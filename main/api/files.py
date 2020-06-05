import os
import shutil
import tempfile

import jwt
import requests
from flask import request, make_response, jsonify
from flask_login import current_user
import oss2
from pdf2image import convert_from_path

from ..model import Roles
from ..util.try_catch import api_response
from ..exception import NewComException
from config import load_config
from .upload import upload_file, simple_upload
from ..model import Engineer, Company, EnterProject

from werkzeug.utils import secure_filename

Config = load_config()

import sys
import base64
import requests
import json

class AliOss(object):
    def __init__(self):
        ak = Config.OSS_KEY
        sk = Config.OSS_SEC
        self.auth = oss2.Auth(ak, sk)
        self.bucket = oss2.Bucket(
            self.auth, "oss-cn-beijing.aliyuncs.com", Config.AliOss_Bucket
        )

    def _upload(self, name, file_path):
        self.bucket.put_object_from_file(name, file_path)

    def _sign_url(self, name):
        return self.bucket.sign_url("GET", name, 120)

    def _download(self, name, file_path):
        self.bucket.get_object_to_file(name, file_path)


class EntryFileTemplate(AliOss):
    def __init__(self, app):
        super().__init__()
        self.app = app

    @classmethod
    def _object_name(cls, company_id=None, file_name=None):
        # entry-template 是在阿里云oss中设置的目录名
        return "entry-template/{}/{}".format(company_id, file_name)

    @classmethod
    def set_default_for_company(cls, company_id):
        ali_oss = AliOss()
        entry_file_template = Config.DEFAULT_ENTRY_FILE_TEMPLATE.split("/")[-1]
        ali_oss._upload(
            cls._object_name(company_id, entry_file_template),
            Config.DEFAULT_ENTRY_FILE_TEMPLATE,
        )
        c = Company.query.get(company_id)
        c.update(entry_file_template=entry_file_template)

    def init_blueprint(self, url_prefix, endpoint_prefix):
        self.app.add_url_rule(
            url_prefix + "/" + "entry_file_template",
            endpoint=endpoint_prefix + ".upload_entry_file_template",
            view_func=self.upload,
            methods=["POST"],
        )
        self.app.add_url_rule(
            url_prefix + "/" + "entry_file_template",
            endpoint=endpoint_prefix + ".entry_file_template_url",
            view_func=self.url,
            methods=["GET"],
        )

    @api_response
    def upload(self):
      if current_user.role not in (Roles.company_om, Roles.purchase):
          raise NewComException("无权进行此操作", 500)
      tem_filename, path = simple_upload("entry_file_template")
      entry_file_template = ".".join(tem_filename.split(".")[1:])
      self._upload(
        self._object_name(current_user.company_id, entry_file_template), path
      )

      mode = request.headers['MODE']
      offerID = request.headers['OFFERID']

      if mode != 'resume':
        c = Company.query.get(current_user.company_id)
        c.update(entry_file_template=entry_file_template)
      else:
        result = self.getAnalysisVia3Party(path, offerID)

      return jsonify({ 'result': result})


    def getAnalysisVia3Party(self, filename, offerID):
      url = 'http://www.resumesdk.com/api/parse'
      uid = 2005091   # 替换为你的用户名（int格式）
      pwd = 'NknGoM'  # 替换为你的密码（str格式）

      # 读取文件内容，构造请求
      cont = open(filename, 'rb').read()
      base_cont = base64.b64encode(cont)
      base_cont = base_cont.decode('utf-8') if sys.version.startswith('3') else base_cont     #兼容python2与python3
      data = {'uid': uid,
              'pwd': str(pwd),
              'file_name': filename,
              'file_cont': base_cont,
              }
      
      # 发送请求
      res = requests.post(url, data=json.dumps(data))
      
      # 解析结果
      res_js = json.loads(res.text)
      print('result:\n%s\n'%(json.dumps(res_js, indent=2, ensure_ascii=False)))
      
      if 'result' in res_js:
          print('name: %s'%(res_js['result'].get('name', 'None')))

      # putting analysis result to db
      engineer = res_js['result']
      engineer['offerID'] = offerID
      offer_result = Engineer.post_from_cv(**dict(engineer))
      return offer_result


    @api_response
    def url(self):
        if current_user.role == "company_om":
            company_id = current_user.company_id
        if current_user.role == "engineer":
            company_id = (
                EnterProject.query.filter_by(engineer_id=current_user.id)
                .first()
                .company_id
            )
        c = Company.query.get(company_id)
        entry_file_template = c.entry_file_template
        url = self._sign_url(self._object_name(company_id, entry_file_template))
        return jsonify(
            {
                "url": url.replace("http:", "https:"),
                "entry_file_template": entry_file_template,
            }
        )


class EntryFile(EntryFileTemplate):
    def __init__(self, app):
        super().__init__(app)

    def _object_name(self, engineer):
        # entry-files 是在阿里云oss中设置的目录名
        return "entry-files/{}".format(engineer.id)

    def init_blueprint(self, url_prefix, endpoint_prefix):
        self.app.add_url_rule(
            url_prefix + "/" + "entry_files",
            endpoint=endpoint_prefix + ".upload_entry_files",
            view_func=self.upload,
            methods=["POST"],
        )
        self.app.add_url_rule(
            url_prefix + "/" + "entry_files",
            endpoint=endpoint_prefix + ".entry_files_url",
            view_func=self.url,
            methods=["GET"],
        )
        self.app.add_url_rule(
            url_prefix + "/" + "entry_files",
            endpoint=endpoint_prefix + ".update",
            view_func=self.update,
            methods=["PUT"],
        )
        self.app.add_url_rule(
            url_prefix + "/" + "ef_<engineer_id>_<page>.png",
            endpoint="engineer.ef",
            view_func=self.get_image,
            methods=["GET"],
        )

    # linux环境下pdf转换image
    @classmethod
    def turn_pdf2img(cls, model, pdfPath):
        with tempfile.TemporaryDirectory() as path:
            images = convert_from_path(pdfPath)
            ef_root_path = os.path.join(
                os.path.join(Config.ROOT_DIR, Config.FILE_ENTER_PATH), str(model.id)
            )
            if os.path.exists(ef_root_path):
                shutil.rmtree(ef_root_path)
            os.mkdir(ef_root_path)
            for index, image in enumerate(images):
                image.save("%s/page_%s.jpg" % (ef_root_path, index + 1), quality=65)
        return len(images)

    @api_response
    def upload(self):
        if not current_user.role == Roles.engineer:
            raise NewComException("无权进行此操作", 500)
        tem_filename, path = upload_file("entry_files")

        

        e = Engineer.query.get(current_user.id)
        image_count = self.turn_pdf2img(e, path)
        self._upload(self._object_name(e), path)
        e.update(
            ef_name=".".join(tem_filename.split(".")[1:]), ef_img_amount=image_count
        )
        return tem_filename

    @api_response
    def update(self):
        if not current_user.role == Roles.engineer:
            raise NewComException("无权进行此操作", 500)
        e = Engineer.query.get(current_user.id)
        audit = EnterProject.query.filter_by(
            career_id=e.now_career_id, engineer_id=e.id
        ).first()
        if not audit.status <= 0:
            raise NewComException("当前不可更改", 500)
        tem_filename, path = upload_file("entry_files")
        e = Engineer.query.get(current_user.id)
        image_count = self.turn_pdf2img(e, path)
        self._upload(self._object_name(e), path)
        e.update(
            ef_name=".".join(tem_filename.split(".")[1:]), ef_img_amount=image_count
        )
        return tem_filename

    @api_response
    def url(self):
        engineer_id = request.args.get("engineer_id")
        e = Engineer.query.get(engineer_id)
        url = self._sign_url(self._object_name(e))
        code = requests.get(url).status_code
        if code == 200:
            return url.replace("http:", "https:")
        return ""

    @api_response
    def get_image(self, engineer_id, page):
        """
        下载也要有权限控制，所以，不能放静态文件夹，要通过本函数获取
        :return:
        """
        et_path = os.path.join(
            os.path.join(Config.ROOT_DIR, Config.FILE_ENTER_PATH), str(engineer_id)
        )
        img_path = os.path.join(et_path, "page_{}.jpg".format(page))
        with open(img_path, "rb") as f:
            response = make_response(f.read())
        mime_type = "image/png"
        response.headers["Content-Type"] = mime_type
        # response.headers['Content-Length'] = ''
        et_name = "ef_{}_{}.jpg".format(engineer_id, page)  # .encode('utf-8'))
        response.headers[
            "Content-Disposition"
        ] = "attachment; filename*=utf-8''{}".format(et_name)
        return response

def init_api(app, url_prefix):
    EntryFileTemplate(app).init_blueprint(url_prefix, "files")
    EntryFile(app).init_blueprint(url_prefix, "files")

