import pytest
from isucari import exceptions, validator


def test_validate_price():
    with pytest.raises(exceptions.HttpException):
        validator.validate_price(99)

    with pytest.raises(exceptions.HttpException):
        validator.validate_price(1000001)

    try:
        validator.validate_price(100)
    except exceptions.HttpException:
        pytest.fail('unexpected Exception')

    try:
        validator.validate_price(1000000)
    except exceptions.HttpException:
        pytest.fail('unexpected Exception')
