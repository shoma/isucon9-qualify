import pytest
import datetime
from unittest import mock
from sqlalchemy.exc import IntegrityError
from werkzeug.test import FileStorage

from isucari import core, exceptions
from isucari.database import db
from isucari.models import User, Item, TransactionEvidences, Shipping, TransactionEvidenceStatus, ShippingStatus


# bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt(10))
_hashed_password=b'$2b$10$kqhzGMuv7TF4L8c5WKEvKe0fvS1VAT.7gzmPKisxUptWNqfZg82Ci'
now = datetime.datetime(2019, 9, 8, 18, 10, 00)


def test_timeline(app):
    pass


def test_category_items(app):
    pass


def test_transaction_items(app):
    pass


def test_user_time_line(app):
    pass


def test_get_item(app):
    pass


def test_sell(app):
    pass
    with app.app_context():
        # Preconditions
        User.query.delete()
        Item.query.delete()

        seller = User(account_name="seller", address="address", hashed_password=_hashed_password)
        db.session.add(seller)
        uploadfile = FileStorage()
        uploadfile.save = mock.MagicMock(return_value=None)
        uploadfile.save('/path/to/file/')
        image = FileStorage()
        res = core.sell(seller, "name", "desc", 1000, 13, image)


def test_edit(app):
    pass


def test_buy(app):
    pass


def test_ship(app):
    pass


def test_ship_done(app):
    pass


def test_complete(app):
    pass


def test_get_qr_code(app):
    with app.app_context():
        # precondition
        User.query.delete()
        TransactionEvidences.query.delete()
        Shipping.query.delete()

        seller = User(account_name="seller", address="address", hashed_password=_hashed_password)
        db.session.add(seller)

        te = TransactionEvidences(
            seller_id=seller.id,
            buyer_id=0,
            status=TransactionEvidenceStatus.wait_done,
            item_id=42,
            item_name="name",
            item_price=1001,
            item_description="description",
            item_category_id=20,
            item_root_category_id=2,
            created_at=now,
            updated_at=now
        )
        db.session.add(te)

        shipping = Shipping(
            transaction_evidence_id=te.id,
            status=ShippingStatus.wait_pickup,
            reserve_id="reserve_id",
            reserve_time="1234567",
            to_address="",
            to_name="",
            from_address="",
            from_name="",
            img_binary=None,
            created_at=now,
            updated_at=now
        )
        db.session.add(shipping)

        db.session.commit()

        res = core.get_qr_code(seller.id, te.id)
        assert res is not None

        with pytest.raises(exceptions.HttpException) as e:
            seller.id = 100
            core.get_qr_code(seller, te.id)
            assert "権限がありません" == e.value.message


def test_bump(app):
    with app.app_context():
        # precondition
        User.query.delete()
        Item.query.delete()

        user = User(account_name="name",
                    address="bbbbb",
                    hashed_password=_hashed_password,
                    last_bump=now,
                    )
        db.session.add(user)
        db.session.commit()
        another = User(account_name="another",
                       address="bbbbb",
                       hashed_password=_hashed_password,
                       last_bump=now,
                       )
        db.session.add(another)
        db.session.commit()
        item = Item(
            seller_id=user.id,
            name="name of item",
            price=201,
            description="description of item",
            image_name="item_image.jpg",
            category_id=42,
            created_at=now,
        )
        db.session.add(item)
        db.session.commit()

        # within 3 seconds
        with mock.patch('isucari.core.current_time', return_value=datetime.datetime(2019, 9, 8, 18, 10, 1)):
            with pytest.raises(exceptions.HttpException) as e:
                core.bump(user, item.id)
                assert "Bump not allowed" == e.value.message

        with mock.patch('isucari.core.current_time', return_value=datetime.datetime(2019, 9, 8, 18, 11, 00)):
            created_at = item.created_at
            last_bump_at = user.last_bump

            core.bump(user, item.id)

            bumped = Item.query.get(item.id)
            assert bumped.created_at > created_at
            assert user.last_bump > last_bump_at

        db.session.add(user)
        db.session.commit()
        with mock.patch('isucari.core.current_time', return_value=datetime.datetime(2019, 9, 8, 18, 12, 00)):
            with pytest.raises(exceptions.HttpException) as e:
                core.bump(another, item.id)
                assert "自分の商品以外は編集できません" == e.value.message


def test_login(app):
    account_name = "name"
    password = "passw0rd"
    with app.app_context():
        # precondition
        User.query.delete()

        # arrange
        user = User(
            account_name=account_name,
            hashed_password=_hashed_password,
            address="dummy"
        )
        db.session.add(user)
        db.session.commit()

        with pytest.raises(exceptions.HttpException) as e:
            # invalid password
            core.login("name", "password")
            assert str(e.value) == "アカウント名かパスワードが間違えています"
        with pytest.raises(exceptions.HttpException) as e:
            # invalid username
            core.login("account", "password")
            assert str(e.value) == "アカウント名かパスワードが間違えています"

        rtn = core.login(account_name, password)
        assert rtn.account_name == account_name
        assert rtn.address == "dummy"


def test_register(app):
    account_name = "name"
    password = "passw0rd"
    address = "address"
    with app.app_context():
        # precondition
        User.query.delete()

        result = core.register(account_name, password, address)

        assert result is not None
        assert account_name == result.account_name
        assert address == result.address
        assert 0 == result.num_sell_items

        # Duplicate
        with pytest.raises(IntegrityError) as e:
            core.register(account_name, password, address)
        msg = str(e.value)
        assert """(1062, "Duplicate entry 'name' for key 'account_name'")""" in msg


if __name__ == '__main__':
    pytest.main()
