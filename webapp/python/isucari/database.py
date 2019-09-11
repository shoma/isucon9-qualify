import os

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    db.init_app(app)


def get_dsn():
    return "mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8".format(
        host=os.getenv('MYSQL_HOST', '127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'isucari'),
        password=os.getenv('MYSQL_PASS', 'isucari'),
        database=os.getenv('MYSQL_DBNAME', 'isucari'),
    )
