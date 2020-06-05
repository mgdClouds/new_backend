class FileType(object):
    cv = 'cv'
    contract = 'contract'
    head_img = 'head_img'

    @classmethod
    def good_file_type(cls, file_type):
        return file_type in [cls.cv, cls.contract, cls.head_img]


def save(file_type, data):
    if not FileType.good_file_type(file_type):
        pass


def get():
    pass


def clear_tem():
    pass
