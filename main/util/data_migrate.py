"""此脚本用于导入历史工时"""
import os, requests, datetime, logging
import pandas as pd

headers = lambda x: {"Authorization": x}
logging.basicConfig(level=logging.INFO)


def get_contact(excel_path: str):
    """
    params: excel_path:
    return: Dataframe
    """
    try:
        contact = pd.read_excel(excel_path, sheet_name="1联系方式")
        logging.info("联系方式读取成功！！！")
        return contact
    except Exception as e:
        raise RuntimeError("excel读取失败，存在不合规数据，详细原因为：", e)


def get_daily(excel_path: str):
    try:
        dailys = pd.read_excel(excel_path, sheet_name="4日报")
        dailys["日期"] = dailys.日期.apply(lambda x: x.strftime("%Y-%m-%d"))
        logging.info("日报表读取成功！！！")
        return dailys
    except Exception as e:
        raise RuntimeError("excel读取失败，存在不合规数据，详细原因为：", e)


def get_token(host: str, username: str, pwd: str, port: str):
    """
    获取token
    :param host: 请求host
    :param username: 用户名
    :param pwd: 密码
    :return: {'phone':token}
    """
    data = {"username": username, "password": pwd, "port": port}
    resp = requests.post(host + "auth/token", json=data)
    assert resp.status_code == 200
    return resp.json()


def tokens(contact: pd.DataFrame, host: str):
    """
    根据联系方式表，获取工程师和pm的token池
    :param host: 请求host
    :param username: 用户名
    :param pwd: 密码
    :return: {'phone':token}
    """
    try:
        return {
            data[2]: get_token(host, data[2], "nk123456", "m")["token"]
            for data in contact.values
        }
    except Exception as e:
        logging.info("token池获取失败，原因为:", e)


def direct_enter_project(host: str, excel_path: str, basepath: str, company: str, company_pwd: str, pwd: str):
    """
    :param filepath: 入职信息表
    :param om_token: 平台端管理员token
    :param cm_token: 甲方端管理员token
    :return:
    """
    entry_info = pd.read_excel(
        excel_path,
        sheet_name="2入职信息",
        names=[
            "real_name",
            "gender",
            "phone",
            "email",
            "cv_upload_result",
            "entry_files",
            "start_date",
            "work_place",
            "salary_type",
            "project_id",
            "position_id",
            "position_level_id",
            "pm_id",
        ],
    )
    try:
        entry_info["start_date"] = entry_info.start_date.apply(
            lambda x: x.strftime("%Y-%m-%d")
        )
        entry_info.replace(
            {"gender": {"男": 1, "女": 0}, "salary_type": {"按日": 0, "按月": 1}},
            inplace=True,
        )
        logging.info("入职信息表读取成功！！！")
    except Exception as e:
        raise RuntimeError("excel读取失败，存在不合规数据，详细原因为：", e)
    # 清洗数据
    cm_token = get_token(host, company, company_pwd, "cm")["token"]
    om_token = get_token(host, "admin", pwd, "om")["token"]
    pms_info = requests.get(host + "pms", headers=headers(cm_token))
    assert pms_info.status_code == 200
    pms = {int(pm["phone"]): pm["id"] for pm in pms_info.json()["data"]}
    projects_info = requests.get(host + "projects", headers=headers(cm_token))
    assert projects_info.status_code == 200
    projects = {
        project["name"]: project["id"] for project in projects_info.json()["data"]
    }
    positions_info = requests.get(
        host + "positions?schema=PositionWithLevelsSchema", headers=headers(cm_token)
    )
    assert positions_info.status_code == 200
    positions = {
        positions["name"]: positions["id"]
        for positions in positions_info.json()["data"]
    }
    # todo 极有可能存在不同职位，级别名相同的情况
    position_levels = {
        position["name"]: position["id"]
        for positions in positions_info.json()["data"]
        for position in positions["position_levels"]
    }
    entry_info.replace(
        {
            "pm_id": pms,
            "project_id": projects,
            "position_id": positions,
            "position_level_id": position_levels,
        },
        inplace=True,
    )
    print("入项准备结束......")
    # 增员入项
    for entry in entry_info.values:
        cv_path = os.path.join(basepath, entry[4])
        files = {
            "Filename": entry[4],
            "contract": (entry[4], open(cv_path, "rb"), "application/octet-stream"),
        }
        # 上传简历
        respone = requests.post(
            host + "contract", files=files, headers=headers(cm_token)
        )
        if respone.status_code != 200:
            raise RuntimeError(f"简历上传失败{respone.json()}")

        entry[4], entry[2] = respone.text, str(entry[2])
        entry_dict = dict(
            pm_id=entry[12],
            position_level_id=entry[11],
            salary_type=entry[8],
            project_id=entry[9],
            start_date=entry[6],
            work_place=entry[7],
            engineer=dict(zip(entry_info[:6], entry[:6])),
        )
        logging.info(entry[0] + "入项流程开始----------")
        # 增员
        respone = requests.post(
            host + "purchase/direct_enter_project",
            json=entry_dict,
            headers=headers(cm_token),
        )
        if respone.status_code != 200:
            raise RuntimeError(f"增员失败{respone.json()}")
        enter_id = respone.json()["id"]
        logging.info("增员成功")
        # 入项材料提交
        engineer_token = get_token(host, entry[2], pwd, "m")
        path = os.path.join(basepath, entry[5])
        f = {"entry_files": open(path, "rb")}
        m = {
            "Content-Disposition": "form-data",
            "name": "entry_files",
            "filename": entry[5],
            "Content-Type": "application/pdf",
        }
        engineer_respone = requests.post(
            host + "entry_files",
            files=f,
            data=m,
            headers=headers(engineer_token["token"]),
        )
        kwargs = {
            "ef_upload_result": str(engineer_respone.text),
            "engineer_id": engineer_token["uid"],
        }
        resp = requests.put(
            host
            + "enter_project?schema=EnterProjectSubmitSchema&engineer_id=%s"
            % kwargs["engineer_id"],
            headers=headers(engineer_token["token"]),
            json=kwargs,
        )
        if resp.status_code != 200:
            raise RuntimeError("入项材料提交失败", resp.json())
        logging.info("入项材料提交成功")

        # 平台通过入项
        pm_info_rsp = requests.get(
            host + "pm?id=%s" % entry[12], headers=headers(om_token)
        )
        pm_info = pm_info_rsp.json()
        en_resp = requests.put(
            host
            + "enter_project?id=%s&schema=EnterProjectOmFileAuditSchema" % enter_id,
            json={"comment": "", "yes_or_no": 1},
            headers=headers(om_token),
        )
        if en_resp.status_code != 200:
            raise RuntimeError("平台通过失败", en_resp.json())
        logging.info("平台通过成功")

        # 项目经理通过入项
        pm_token = get_token(host, pm_info["phone"], pwd, "m")["token"]
        pm_rsp = requests.put(
            host
            + "enter_project?engineer_id=%s&schema=EnterProjectPmFileAuditSchema"
            % engineer_token["uid"],
            json={"comment": "", "yes_or_no": 1},
            headers=headers(pm_token),
        )
        if pm_rsp.status_code != 200:
            raise RuntimeError("项目经理通过失败", pm_rsp.json())
        logging.info("项目经理通过成功")

        # 甲方端通过入项
        data = {
            "work_content": "111",
            "service_type": "现场",
            "auto_renew": 0,
            "renew_cycle": 12,
            "yes_or_no": 1,
        }  # work_content 内容  auto_renew 自动续签 0 是 1 否 renew_cycle 续签周期
        cm_rsp = requests.put(
            host
            + "enter_project?id=%s&schema=EnterProjectCompanyFileAuditSchema"
            % enter_id,
            json=data,
            headers=headers(cm_token),
        )
        if cm_rsp.status_code != 200:
            raise RuntimeError("甲方通过失败", cm_rsp.json())
        logging.info("甲方通过成功")

        # om审批通过
        data = {"employ_type": 0}  # employ_type 员工模式：0 牛咖 1 员工
        om_rsp = requests.put(
            host + "enter_project?id=%s&schema=EnterProjectOmCheckSchema" % enter_id,
            json=data,
            headers=headers(om_token),
        )
        if om_rsp.status_code != 200:
            raise RuntimeError("OM通过失败", om_rsp.json())
        logging.info("OM通过成功")


def create_approval(host: str, excel_path: str, tokenPools: dict, month: str):
    """
    :param tokenPools: 所有员工token池
    :param month: 月份 eg：202001
    :return:
    """
    approvals = pd.read_excel(
        excel_path,
        sheet_name="3加班-请假审批",
        names=[
            "month",
            "real_name",
            "phone",
            "pm",
            "pm_phone",
            "start_date",
            "end_date",
            "duration",
            "act",
            "reason",
            "leave_type",
        ],
    )
    try:
        approvals.replace(
            {
                "act": {"请假": "leave", "加班": "extra_work"},
                "leave_type": {"事假": "personal", "病假": "sick", "调休": "shift"},
            },
            inplace=True,
        )
        approvals["start_date"] = approvals.start_date.apply(
            lambda x: x.strftime("%Y-%m-%d %H:%M:%S")
        )
        approvals["end_date"] = approvals.end_date.apply(
            lambda x: x.strftime("%Y-%m-%d %H:%M:%S")
        )
        logging.info("加班-请假审批表读取成功！！！")
    except Exception as e:
        raise RuntimeError("excel读取失败，存在不合规数据，详细原因为：", e)

    logging.info(month + " 审批开始")
    for approval in approvals.values:
        if approval[0] == int(month):
            data1 = dict(
                zip(
                    ["start_date", "end_date", "duration", "reason"],
                    [approval[5], approval[6], approval[7], approval[9]],
                )
            )
            data2 = {"status": "checked"}
            schema = "ExtraWorkCheckPutSchema"
            if approval[8] == "leave":
                schema = "LeaveCheckPutSchema"
                data1["leave_type"] = approval[10]
            eg_resp = requests.post(
                host + approval[8], json=data1, headers=headers(tokenPools[approval[2]])
            )
            if eg_resp.status_code != 200:
                raise RuntimeError("%s %s提交失败" % (approval[1], approval[8]), eg_resp.json())
            logging.info("%s %s审批提交成功" % (approval[1], approval[8]))
            pm_resp = requests.put(
                host + "audit?schema=%s&id=%s" % (schema, eg_resp.json()["id"]),
                json=data2,
                headers=headers(tokenPools[approval[4]]),
            )
            if pm_resp.status_code != 200:
                raise RuntimeError(
                    "%s %s审批通过失败" % (approval[1], approval[8]), pm_resp.json()
                )
            logging.info("%s %s审批通过成功" % (approval[1], approval[8]))


def flush_log(tokenPools: dict, pm_phones: set):
    """
    刷新日报，生成新日报
    :param tokenPools: token池
    :return:
    """

    result = dict()
    for phone, token in tokenPools.items():
        if phone not in pm_phones:
            resp = requests.get(
                host + "daily_logs?sort_id=-1&latest=True", headers=headers(token)
            )
            if resp.status_code != 200:
                raise RuntimeError(f"{phone} 日报刷新失败 {resp.json()}")
            logging.info("%s 日报刷新成功" % phone)
            result[phone] = resp.json()["data"]
    return result


def insert_dailylog(
        flush_datas: dict, tokenPools: dict, dailys: pd.DataFrame, month: str
):
    """
    日报写入
    :param flush_datas: 刷新结果
    :param tokenPools: token池
    :return:
    """
    for daily in dailys.values:
        if "".join(daily[1].split("-")[:2]) == month:
            for flush_data in flush_datas[daily[0]]:
                if daily[1] == flush_data["date"] and flush_data["is_workday"]:
                    data = {"content": daily[2], "duration": daily[3]}
                    eg_resp = requests.put(
                        host
                        + "daily_log?schema=DailyLogPutSchema&id=%s" % flush_data["id"],
                        json=data,
                        headers=headers(tokenPools[daily[0]]),
                    )
                    if eg_resp.status_code != 200:
                        raise RuntimeError(
                            "%s %s 日报写入失败" % (daily[0], flush_data[1]), eg_resp.json()
                        )
                    logging.info("%s %s 日报写入成功！" % (daily[0], daily[1]))


def submit_report(month: str, tokenPools: dict, contact: pd.DataFrame, pm_phones: set):
    """
    提交日报
    :param month:
    :param tokenPools:
    :return:
    """
    for person in contact.values:
        if person[2] not in pm_phones:
            resp = requests.post(
                host + "work_report",
                json={"year_month": int(month)},
                headers=headers(tokenPools[person[2]]),
            )
            if resp.status_code != 200:
                raise RuntimeError("%s %s 日报提交失败" % (person[2], month), resp.json())
            logging.info("%s %s 日报提交成功！" % (person[2], month))


def checked_report(tokenPools: dict, pm_phones: set):
    """
    审核日报
    :param tokenPools:
    :return:
    """
    jsondata = {"ability_score": 4, "attitude_score": 4, "status": "checked"}
    for phone in pm_phones:
        respdatas = requests.get(
            host + "audits?sort_id=-1&in_status=[%22submit%22]",
            headers=headers(tokenPools[phone]),
        )
        if respdatas.status_code != 200:
            raise RuntimeError(f"刷新失败 {respdatas.json()}")
        datas = respdatas.json()["data"]
        for data in datas:
            resp = requests.put(
                host + "audit?schema=WorkReportCheckPutSchema&id=%s" % data["id"],
                json=jsondata,
                headers=headers(tokenPools[phone]),
            )
            if resp.status_code != 200:
                raise RuntimeError(resp.json())
            logging.info("%s 日报审核成功！" % data["engineer"]["pre_username"])


def main(host: str, excel_path: str):
    contact, dailys = get_contact(excel_path), get_daily(excel_path)
    pm_phones = {info[2] for info in contact.values if info[1] == "项目经理"}
    tokenPools = tokens(contact, host)
    months = sorted(
        set(["".join(date.split("-")[:2]) for date in dailys.日期.values]),
        key=lambda x: int(x),
    )
    last_moth_last_day = datetime.datetime.today().replace(day=1) - datetime.timedelta(
        days=1
    )
    last_moth = last_moth_last_day.year * 100 + last_moth_last_day.month
    for month in months:
        flush_logs = flush_log(tokenPools, pm_phones)
        create_approval(host, excel_path, tokenPools, month)
        insert_dailylog(flush_logs, tokenPools, dailys, month)
        if int(month) <= last_moth:
            submit_report(month, tokenPools, contact, pm_phones)
            checked_report(tokenPools, pm_phones)
    logging.info("导入工时成功")


if __name__ == "__main__":
    host = "https://api.newcom.ren/api/v1/"
    default_pwd = "nk123456"
    basepath = r"C:\Users\W\Desktop\1231提测-导入入项材料"
    excel_name = "导入历史工时0111.xlsx"
    excel_path = os.path.join(basepath, excel_name)
    # 自主增员
    direct_enter_project(host,excel_path, basepath,"test1211", "nk123456", default_pwd)
    # 导入历史工时
    main(host,excel_path)
