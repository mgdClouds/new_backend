from datetime import datetime, timedelta

import numpy
import pandas as pd
from sqlalchemy import create_engine

from config import load_config

config = load_config()
engine = create_engine(config.SQLALCHEMY_DATABASE_URI)


def sql_str(df: pd.DataFrame, name: str):
    names = str(df[name].values.tolist())
    names = names.replace("[", "(")
    names = names.replace("]", ")")
    return names


def insert_offer(excel_path: str):
    """读取offer，插入offer表，只支持写入单条数据"""
    df = pd.read_excel(excel_path, sheet_name=0, usecols="A:K",
                       names=["company_id", "position_id", "position_levels", "position_name", "position_type",
                              "service_type", "work_place", "experience", "education", "description", "need_resume"])
    df["need_resume"].replace("是", True, inplace=True)
    df["need_resume"].replace("否", False, inplace=True)
    names = sql_str(df, "company_id")
    sql = f"select id from company where name in {names}"
    ids = pd.read_sql_query(sql, engine).values
    df["company_id"] = ids
    positions = sql_str(df, "position_id")
    sql = f"select id from position where name in {positions}"
    position_id = pd.read_sql_query(sql, engine).values
    df["position_id"] = position_id
    position_levels_df = df.pop("position_levels")
    df["created"] = [datetime.utcnow() for _ in range(len(df))]
    df["status"] = [1 for _ in range(len(df))]
    df.to_sql("offer", engine, index=False, if_exists="append")
    offer = engine.execute(
        f"SELECT id FROM offer where company_id={ids[0][0]} and position_id={position_id[0][0]} and position_name ='{df['position_name'][0]}'").fetchone()
    position_level_name = str(position_levels_df[0].replace("\n", "").split("，"))
    position_level_name = position_level_name.replace("[", "(")
    position_level_name = position_level_name.replace("]", ")")
    sql = f"select id  as position_level_id from position_level where company_id={ids[0][0]} and position_id={position_id[0][0]} and name in {position_level_name}"
    position_level_ids = pd.read_sql_query(sql, engine)
    position_level_ids["offer_id"] = [offer._row for _ in range(len(position_level_ids))]
    position_level_ids.to_sql("offer_position_levels", engine, index=False, if_exists="append")
    return


def insert_offer_data(excel_path):
    df = pd.read_excel(excel_path, sheet_name=0, usecols="A:B,D:K",
                       names=["offer_id", "engineer_id", "written_score", "Interview_score",
                              "nk_result", "nk_evaluate", "finally_result", "customer_evaluate", "salary",
                              "entry_time"])
    df.replace("\t", numpy.nan, inplace=True)
    df.replace(" ", numpy.nan, inplace=True)
    names = sql_str(df, "engineer_id")
    sql = f"select id from engineer where id in (select id from user where role='engineer' and real_name in {names}) and status=0"
    ids = pd.read_sql_query(sql, engine).values
    df["engineer_id"] = ids
    offers = []
    for offer in df["offer_id"]:
        sql = f"select id from offer where position_name = '{offer}'"
        offer = engine.execute(sql).fetchone()
        offers.append(offer[0])
    df["offer_id"] = offers
    df["created"] = [datetime.utcnow() for _ in range(len(df))]
    df.to_sql("offer_data", engine, index=False, if_exists="append")
    return df


def insert_hiring_schedule(excel_path, offer_name: str):
    """插入招聘进度表"""
    df = pd.read_excel(excel_path, sheet_name=0, usecols="A:D",
                       names=["engineer_id", "created", "plan_status", "note"])
    df["created"] = df["created"].apply(lambda x: x - timedelta(hours=8))
    ids = []
    for name in df["engineer_id"]:
        sql = f"select id from engineer where id in (select id from user where role='engineer' and real_name = '{name}') and status=0"
        id = engine.execute(sql).fetchone()[0]
        ids.append(id)
    df["engineer_id"] = ids
    sql = f"select id from offer where position_name='{offer_name}'"
    offer_id = engine.execute(sql).fetchone()[0]
    df["offer_id"] = [offer_id for _ in range(len(df))]
    df.to_sql("hiring_schedule", engine, index=False, if_exists="append")
    return


def insert_offer_schedule_data(excel_path, offer_name: str):
    """插入需求进度数据"""
    df = pd.read_excel(excel_path, sheet_name=0, usecols="A:D",
                       names=["engineer_id", "created", "plan_status", "note"])
    df["created"] = df["created"].apply(lambda x: x.date())
    df = df.set_index("created")
    grouped = df.groupby(df.index)

    insert_dict = {"date": [], "resume_collection_num": [], "written_pass_num": [], "interview_pass_num": [],
                   "offer_pass_num": []}
    for dt in grouped.groups.keys():
        insert_dict["date"].append(dt)
        dt_df = grouped.get_group(dt)
        insert_dict["resume_collection_num"].append(dt_df.query("plan_status=='收集简历'").shape[0])
        temp = pd.to_numeric(dt_df.query("plan_status=='笔试结束'")["note"], errors="ignore")
        insert_dict["written_pass_num"].append(temp[temp >= 60].shape[0])
        insert_dict["interview_pass_num"].append(dt_df.query("plan_status=='面试结束'").shape[0])
        insert_dict["offer_pass_num"].append(dt_df.query("plan_status=='评定结果' & note=='需求满足'").shape[0])
    insert_df = pd.DataFrame(insert_dict)

    sql = f"select id from offer where position_name='{offer_name}'"
    offer_id = engine.execute(sql).fetchone()[0]
    insert_df["offer_id"] = [offer_id for _ in range(len(insert_df))]
    insert_df.to_sql("offer_schedule_data",engine,index=False,if_exists="append")
    return


if __name__ == '__main__':
    offer = input("请输入offer表路径")
    person = input("请输入人员汇总表路径")
    schedule = input("请输入过程数据表路径")
    offer_name = input("请输入需求名称")
    insert_offer(offer)
    insert_offer_data(person)
    insert_hiring_schedule(schedule, offer_name)
    insert_offer_schedule_data(schedule, offer_name)
