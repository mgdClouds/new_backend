class NewComException(Exception):
    def __init__(self, description, status_code):
        self.description = description
        self.status_code = status_code


class NewComItemNotExist(NewComException):
    def __init__(self, description=None, status_code=None):
        super().__init__(description or '对象不存在', status_code or 404)
