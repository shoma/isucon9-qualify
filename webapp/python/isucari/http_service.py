import requests

from .config import Constants


class Shipping(object):
    @classmethod
    def create(cls, base_url, params=None):
        if params is None:
            params = {}
        res = requests.post(base_url + "/create",
                            headers=dict(Authorization=Constants.ISUCARI_API_TOKEN),
                            json=dict(
                                to_address=params['to_address'],
                                to_name=params['to_name'],
                                from_address=params['from_address'],
                                from_name=params['from_name'],
                            ))
        res.raise_for_status()
        return res.json()

    @classmethod
    def status(cls, base_url, params=None):
        if params is None:
            params = {}

        res = requests.post(
            base_url + "/status",
            headers=dict(Authorization=Constants.ISUCARI_API_TOKEN),
            json=params,
            )
        res.raise_for_status()
        return res.json()


class Payment(object):
    @classmethod
    def token(cls, base_url, params=None):
        if params is None:
            params = {}
        res = requests.post(base_url + "/token",
                            json=dict(
                                shop_id=Constants.PAYMENT_SERVICE_ISUCARI_SHOP_ID,
                                api_key=Constants.PAYMENT_SERVICE_ISUCARI_API_KEY,
                                token=params['token'],
                                price=params['price'],
                            ))
        res.raise_for_status()
        return res.json()
