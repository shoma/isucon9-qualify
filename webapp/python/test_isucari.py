import unittest

from . import isucari


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
        e = isucari.UserNotFound()
        self.assertEqual(404, e.status_code)
        self.assertEqual("user not found", e.message)
        with isucari.app.app_context():
            resp = e.get_response()
            self.assertEqual('application/json', resp.content_type)
            self.assertEqual(b'{"error":"user not found"}\n', resp.data)

    def test_PaymentError(self):
        e = isucari.PaymentError()
        self.assertEqual(500, e.status_code)
        self.assertEqual("想定外のエラー", e.message)
        with isucari.app.app_context():
            resp = e.get_response()
            self.assertEqual('application/json', resp.content_type)
            self.assertEqual(b'{"error":"\\u60f3\\u5b9a\\u5916\\u306e\\u30a8\\u30e9\\u30fc"}\n', resp.data)


class ValidatorTestCase(unittest.TestCase):
    def test_validate_price(self):
        with self.assertRaises(isucari.HttpException):
            isucari.validator.validate_price(99)

        with self.assertRaises(isucari.HttpException):
            isucari.validator.validate_price(1000001)

        try:
            isucari.validator.validate_price(100)
        except isucari.HttpException:
            self.fail('unexpected Exception')
        try:
            isucari.validator.validate_price(1000000)
        except isucari.HttpException:
            self.fail('unexpected Exception')


if __name__ == '__main__':
    unittest.main()
