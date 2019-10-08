# -*- coding: utf-8 -*-
import os

from .database import get_dsn


base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
static_folder = os.path.abspath(os.path.join(base_dir, '..', 'public'))


class Constants(object):
    DEFAULT_PAYMENT_SERVICE_URL = "http://127.0.0.1:5555"
    DEFAULT_SHIPMENT_SERVICE_URL = "http://127.0.0.1:7000"

    ISUCARI_API_TOKEN = 'Bearer 75ugk2m37a750fwir5xr-22l6h4wmue1bwrubzwd0'

    PAYMENT_SERVICE_ISUCARI_API_KEY = 'a15400e46c83635eb181-946abb51ff26a868317c'
    PAYMENT_SERVICE_ISUCARI_SHOP_ID = '11'

    ITEMS_PER_PAGE = 48
    TRANSACTIONS_PER_PAGE = 10
    BUMP_ALLOW_SECONDS = 3


Config = {
    'SECRET_KEY': 'tagomoris',
    'UPLOAD_FOLDER': os.path.join(static_folder, 'upload'),
    'SQLALCHEMY_DATABASE_URI': get_dsn(),
    'SQLALCHEMY_TRACK_MODIFICATIONS': True,
    'CACHE_TYPE' : 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
}
