# coding=utf-8
import os
import random
import traceback

import requests
from faker import Faker
from urllib3 import encode_multipart_formdata

root_path = 'G:/PycharmProjects/newcom'
f = Faker(locals='zh_CN')
default_password = 'nk123456'

om_login_url = 'http://127.0.0.1:5000/api/v1/auth/token'
om_name = 'admin'
header = {'Content-Type': 'application/json'}


def login():
    resp = requests.post(om_login_url, json={'username': om_name, 'password': default_password}, headers=header)
    token = resp.json().get('token')
    return token


file_path = 'C:/Users/W/Desktop/libai.pdf'


def contrcat(token, data):
    contract_url = 'http://127.0.0.1:5000/api/v1/contract'
    header = {'Authorization': 'Bearer ' + token}
    data['contract'] = ('libai.pdf', open(file_path, 'rb').read())
    encode_data = encode_multipart_formdata(data)
    data = encode_data[0]
    header['Content-Type'] = encode_data[1]
    r = requests.post(contract_url, headers=header, data=data)
    cv_upload_result = r.content.decode()
    return cv_upload_result


def create_engineer(token, cv_upload_result):
    header = {'Authorization': 'Bearer ' + token}
    url = 'http://127.0.0.1:5000/api/v1/engineer'
    engineer_data = {
        "email": f.email(),
        "real_name": f.name()[1:8],
        "phone": str(random.randrange(15518000000,15518999999,1)),
        "gender": str(random.randint(0, 1)),
        "job_wanted_status": "positive",
        "education": [],
        "ability": [],
        "cv_upload_result": cv_upload_result
    }
    try:
        resp = requests.post(url, json=engineer_data, headers=header)
        print(resp.status_code)
    except Exception as e:
        print(e)
        print(traceback.format_exc)


if __name__ == '__main__':
    token = login()
    for i in range(20):
        cv_upload_result = contrcat(token, {"data": "value"})
        create_engineer(token, cv_upload_result)