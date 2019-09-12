from flask import jsonify
from requests import codes


class HttpException(Exception):
    status_code = codes.internal_server_error

    def __init__(self, status_code, message=None):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code

    def get_response(self):
        response = jsonify({'error': self.message})
        response.status_code = self.status_code
        return response


class NotFound(HttpException):
    status_code = codes.not_found

    def __init__(self):
        Exception.__init__(self)


class UserNotFound(NotFound):
    message = "user not found"


class ItemNotFound(NotFound):
    message = "item not found"


class ShippingNotFound(NotFound):
    message = "shipping not found"


class TransactionEvidencesNotFound(NotFound):
    message = "transaction_evidences not found"


class PaymentInvalid(HttpException):
    status_code = codes.bad_request
    message = "カード情報に誤りがあります"

    def __init__(self):
        Exception.__init__(self)


class PaymentFail(HttpException):
    status_code = codes.bad_request
    message = "カードの残高が足りません"

    def __init__(self):
        Exception.__init__(self)


class PaymentError(HttpException):
    status_code = codes.internal_server_error
    message = "想定外のエラー"

    def __init__(self):
        Exception.__init__(self)
