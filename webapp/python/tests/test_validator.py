import unittest

from isucari import exceptions, validator


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
