from isucari.models import status


def test_item_status():
    assert str(status.ItemStatus.on_sale) == "on_sale"


if __name__ == '__main__':
    import pytest
    pytest.main()