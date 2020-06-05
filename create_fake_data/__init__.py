import json

from main.app import create_app
from main.model import Om

app = create_app('testing')
app_ctx = app.app_context()
app_ctx.push()

test_app = app.test_client()

@app.before_first_request
def other_config():
    _om = Om.query.filter().first()
    app.config.update(
        break_up_fee=_om.break_up_fee,
        tax_free_rate=_om.tax_free_rate,
        ware_fare=_om.ware_fare
    )

class AuthUser(object):
    def __init__(self, user_name, password="11111111"):
        response = test_app.post('/api/v1/auth/token', json={'username': user_name, 'password': password})
        if not response.status_code == 200:
            raise Exception('cant get token' + response.text)
        result = json.loads(response.get_data(as_text=True))
        self.token = result['token']
        self.id = result['uid']

    def get(self, *args, **kwargs):
        res = test_app.get(*args, **kwargs, headers={'Authorization': self.token})
        if not res.status_code == 200:
            raise Exception(res.data.decode())
        return res.get_data(as_text=True)

    def get_json(self, *args, **kwargs):
        return json.loads(self.get(*args, **kwargs))

    def post(self, *args, **kwargs):
        res = test_app.post(*args, **kwargs, headers={'Authorization': self.token})
        if not res.status_code == 200:
            raise Exception(res.data.decode())
        return res.get_data(as_text=True)

    def put(self, *args, **kwargs):
        res = test_app.put(*args, **kwargs, headers={'Authorization': self.token})
        if not res.status_code == 200:
            print(res.data.decode)
            # raise Exception(res.data.decode())
        return res.get_data(as_text=True)

    def delete(self, *args, **kwargs):
        res = test_app.delete(*args, **kwargs, headers={'Authorization': self.token})
        if not res.status_code == 200:
            raise Exception(res.data.decode())
        return res.get_data(as_text=True)


def tearDown():
    app_ctx.pop()
