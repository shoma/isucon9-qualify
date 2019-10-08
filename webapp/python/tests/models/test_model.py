from isucari.models.model import *


def test_user():
    sut = User()
    sut.id = 42
    sut.account_name = 'aaaaa'
    sut.address = 'bbbbb'
    sut.num_sell_items = 10
    sut.created_at = datetime.now()
    sut.hashed_password = 'b2:ccccc'

    expected = dict(account_name="aaaaa", address="bbbbb", id=42, num_sell_items=10)
    ret = sut.for_json()
    assert expected == ret
    assert "hashed_password" not in ret

    simple = dict(account_name="aaaaa", id=42, num_sell_items=10)
    ret = sut.for_simple_json()
    assert simple == sut.for_simple_json()
    assert "hashed_password" not in ret
    assert "address" not in ret


def test_item():
    now = datetime.now()
    sut = Item()
    sut.id = 42
    sut.seller_id = 84
    sut.buyer_id = 0
    sut.status = ItemStatus.on_sale
    sut.name = "aaaaa"
    sut.price = 200
    sut.description = "bbbbbbbbbbb"
    sut.image_name = "image.jpg"
    sut.category_id = 36
    sut.created_at = now
    sut.updated_at = now
    sut.transaction_evidence_id = 0

    least = sut.for_json()
    expected = dict(buyer_id=0, category_id=36, description='bbbbbbbbbbb', id=42, name='aaaaa',
                    image_name='image.jpg', price=200, seller_id=84, status='on_sale')
    assert expected == least

    simple = sut.for_simple_json()
    least_simple_expected = {'category': None,
                             'category_id': 36,
                             'created_at': int(now.timestamp()),
                             'id': 42,
                             'image_url': None,
                             'name': 'aaaaa',
                             'price': 200,
                             'seller': None,
                             'seller_id': 84,
                             'status': 'on_sale'}
    assert least_simple_expected == simple

    detail = sut.for_detail_json()
    least_detail_expected = {'category': None,
                             'category_id': 36,
                             'created_at': int(now.timestamp()),
                             'description': 'bbbbbbbbbbb',
                             'id': 42,
                             'image_url': None,
                             'name': 'aaaaa',
                             'price': 200,
                             'seller': None,
                             'seller_id': 84,
                             'status': 'on_sale', }
    assert least_detail_expected == detail


def test_category():
    sut = Category()
    sut.id = 11
    sut.parent_id = 10
    sut.category_name = 'aaaaa'
    sut.parent_category_name = 'bbbbb'
    assert dict(id=11, parent_id=10, category_name='aaaaa', parent_category_name='bbbbb') == sut.for_json()


if __name__ == '__main__':
    import pytest

    pytest.main()
