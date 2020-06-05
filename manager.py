#!/usr/bin/env python
# coding=utf-8

# import Flask Script object
from werkzeug.security import generate_password_hash

from flask_script import Manager, Server
from flask_migrate import Migrate, MigrateCommand
from main.app import db, create_app
from main.model import User
from main.api.files import EntryFileTemplate

# Init manager object via app object
app = create_app()

manager = Manager(app)

# Create a new commands: server
# This command will be run the Flask development_env server
manager.add_command("run_server", Server(host="0.0.0.0", port=5000))

migrate = Migrate(app, db)
manager.add_command("db", MigrateCommand)


@manager.shell
def make_shell_context():
    """Create a python CLI.

    return: Default import object
    type: `Dict`
    """
    # 确保有导入 Flask app object，否则启动的 CLI 上下文中仍然没有 app 对象
    return dict(app=app, db=db, User=User)


def command_list_routes(name):
    from colorama import init, Fore
    from tabulate import tabulate
    init()
    table = []
    print(Fore.LIGHTRED_EX + name)
    for rule in app.url_map.iter_rules():
        table.append([
            Fore.BLUE + rule.endpoint,
            Fore.GREEN + ','.join(rule.methods),
            Fore.YELLOW + rule.rule])

    print(tabulate(sorted(table),
                   headers=(
                       Fore.BLUE + 'End Point(method name)',
                       Fore.GREEN + 'Allowed Methods',
                       Fore.YELLOW + 'Routes'
                   ), showindex="always", tablefmt="grid"))


@manager.command
def routes():
    command_list_routes('API Routes')


@manager.command
def init_site(user='admin', password='nk123456'):
    password = generate_password_hash(password)
    User.create(username=user, password=password, role='om')


@manager.command
def init_entry_file_template():
    EntryFileTemplate.set_default_for_company(0)


# 临时功能
@manager.command
def engineer_search_index():
    from main.model import Engineer
    es = Engineer.query.all()
    for e in es:
        e.search_index()


if __name__ == '__main__':
    manager.run()
