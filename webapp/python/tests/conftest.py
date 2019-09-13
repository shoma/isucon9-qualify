import pytest
from flask import Flask

from isucari.config import Config,static_folder
from isucari.cache import cache
from isucari import database


@pytest.fixture(scope="session")
def app():
    app = Flask(__name__, static_folder=static_folder, static_url_path='', template_folder=static_folder)
    Config['TESTING'] = True
    app.config.from_mapping(Config)

    with app.app_context():
        cache.init_app(app)
        database.init_db(app)
    return app
