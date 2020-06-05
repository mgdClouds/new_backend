import datetime
import requests


def daily1():
    res = requests.get('http://127.0.0.1:5000/api/v1/system/scheduler')
    print(res.status_code)


if __name__ == '__main__':
    daily1()