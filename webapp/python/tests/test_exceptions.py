import unittest

from isucari import exceptions, app


class ExceptionsTestCase(unittest.TestCase):
    def test_UserNotFound(self):
        e = exceptions.UserNotFound()
        self.assertEqual(404, e.status_code)
        self.assertEqual("user not found", e.message)
        with app.app_context():
            resp = e.get_response()
            self.assertEqual('application/json', resp.content_type)
            self.assertEqual(b'{"error":"user not found"}\n', resp.data)

    def test_PaymentError(self):
        e = exceptions.PaymentError()
        self.assertEqual(500, e.status_code)
        self.assertEqual("想定外のエラー", e.message)
        with app.app_context():
            resp = e.get_response()
            self.assertEqual('application/json', resp.content_type)
            self.assertEqual(b'{"error":"\\u60f3\\u5b9a\\u5916\\u306e\\u30a8\\u30e9\\u30fc"}\n', resp.data)
