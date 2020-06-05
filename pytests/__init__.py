import json

from main.app import create_app


app = create_app('testing')
app_ctx = app.app_context()
app_ctx.push()

test_app = app.test_client()


class AuthUser(object):
    def __init__(self, user_name):
        response = test_app.post('/api/v1/auth/token', json={'username': user_name, 'password': '111111'})
        if not response.status_code == 200:
            raise Exception('cant get token')
        self.token = response.get_data(as_text=True)

    def get(self, *args, **kwargs):
        res = test_app.get(*args, **kwargs, headers={'Authorization': self.token})
        if not res.status_code == 200:
            raise Exception('bad request')
        return res.get_data(as_text=True)

    def get_json(self, *args, **kwargs):
        return json.loads(self.get(*args, **kwargs))

    def post(self, *args, **kwargs):
        res = test_app.get(*args, **kwargs, headers={'Authorization': self.token})
        if not res.status_code == 200:
            raise Exception('bad request')
        return res.get_data(as_text=True)

    def put(self, *args, **kwargs):
        res = test_app.put(*args, **kwargs, headers={'Authorization': self.token})
        if not res.status_code == 200:
            raise Exception('bad request')
        return res.get_data(as_text=True)

    def delete(self, *args, **kwargs):
        res = test_app.delete(*args, **kwargs, headers={'Authorization': self.token})
        if not res.status_code == 200:
            raise Exception('bad request')
        return res.get_data(as_text=True)


def tearDown():
    app_ctx.pop()
