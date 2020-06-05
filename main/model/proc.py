from marshmallow import fields, schema, EXCLUDE

from ._base import db


class Proc(object):
    def __init__(self, proc_name, in_schema=None, out_schema=None):
        self.proc_name = proc_name
        self.in_schema = in_schema
        self.out_schema = out_schema

    def __enter__(self):
        self.conn = db.engine.raw_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.connection.close()

    def exec(self, *args):
        in_args = None
        if self.in_schema:
            schema = self.in_schema(many=False, unknown=EXCLUDE)
            in_args = schema.load(args)


class Proc(object):
    def __init__(self):
        self.conn = db.engine.raw_connection()

    @staticmethod
    def hello(user_id):
        with Proc('hello', user_id) as pc:
            result = pc.exec()



