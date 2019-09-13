import unittest

from . import isucari
from .isucari import exceptions, utils, validator


class UtilsTestCase(unittest.TestCase):
    def test_random_string(self):
        for i in range(1, 40):
            ret = isucari.utils.random_string(i)
            self.assertEqual(len(ret), i)
            self.assertRegex(ret, '[a-z0-9]+')

    def get_image_url(self):
        self.assertEqual(isucari.utils.get_image_url('image.png'), '/upload/image.png')


class ExceptionsTestCase(unittest.TestCase):
    def test_UserNotFound(self):
        e = exceptions.UserNotFound()
        self.assertEqual(404, e.status_code)
        self.assertEqual("user not found", e.message)
        with isucari.app.app_context():
            resp = e.get_response()
            self.assertEqual('application/json', resp.content_type)
            self.assertEqual(b'{"error":"user not found"}\n', resp.data)

    def test_PaymentError(self):
        e = exceptions.PaymentError()
        self.assertEqual(500, e.status_code)
        self.assertEqual("想定外のエラー", e.message)
        with isucari.app.app_context():
            resp = e.get_response()
            self.assertEqual('application/json', resp.content_type)
            self.assertEqual(b'{"error":"\\u60f3\\u5b9a\\u5916\\u306e\\u30a8\\u30e9\\u30fc"}\n', resp.data)


class ValidatorTestCase(unittest.TestCase):
    def test_validate_price(self):
        with self.assertRaises(exceptions.HttpException):
            validator.validate_price(99)

        with self.assertRaises(exceptions.HttpException):
            validator.validate_price(1000001)

        try:
            validator.validate_price(100)
        except exceptions.HttpException:
            self.fail('unexpected Exception')
        try:
            validator.validate_price(1000000)
        except exceptions.HttpException:
            self.fail('unexpected Exception')


if __name__ == '__main__':
    unittest.main()
