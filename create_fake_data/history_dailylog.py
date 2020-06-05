# chaos
import xlrd

from create_fake_data import test_app, AuthUser


def import_data(user_name, password='11111111'):
    e = AuthUser(user_name, password=password)
    result = e.get("daily_logs?sort_id=-1&page=1&per_page=1")
    pass


if __name__ == "__main__":
    import_data('e1')
