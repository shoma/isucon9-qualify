from requests import codes

from .exceptions import HttpException


def validate_price(price):
    if not 100 <= price <= 1000000:
        raise HttpException(codes.bad_request, "商品価格は100ｲｽｺｲﾝ以上、1,000,000ｲｽｺｲﾝ以下にしてください")