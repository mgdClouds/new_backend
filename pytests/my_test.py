# coding=gbk
import json
import unittest, requests
from pytests.test_token import test_token


class TestUser(unittest.TestCase):
    url = 'http://localhost:5000/'

    def setUp(self) -> None:
        print('begin...')

    @classmethod
    def setUpClass(cls) -> None:    # 设置全局变量
        cls.url = 'http://localhost:5000/'

    def test_omlogin(self):  # om登录
        url = self.url + 'api/v1/auth/token'
        data = {"username": "admin", "password": "nk123456"}
        resp = requests.post(url, json=data)
        result = json.loads(resp.text)
        test_token['token'] = result["token"]
        self.assertEqual(resp.status_code, 200)

    def test_createcompany(self):   # 新建公司
        url = self.url + 'api/v1/company'
        data = {
            "name": "HUAWEI",
            "om_name": "huawei123",
            "email": "hav41x@y13.com",
            "phone": "18212542679",
            "contact":"你猜,不猜",
            "address":"西安!",
            "billing_cycle": 1,
            "service_fee_rate": 0.1,
            "tax_rate": 0.05,
            "hr_fee_rate": 0.03,
            "finance_rate": 0.01
        }
        resp = requests.post(url, json=data,headers={'Authorization':test_token['token']})
        code = resp.status_code
        self.assertEqual(code, 200)

    def tearDown(self) -> None:
        print('over...')


tests = [TestUser('test_omlogin'), TestUser('test_createcompany')]
suite = unittest.TestSuite(tests)
unittest.TextTestRunner(verbosity=1).run(suite)


if __name__ == '__main__':
    unittest.main()