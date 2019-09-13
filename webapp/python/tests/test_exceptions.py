from isucari import exceptions, app


def test_user_not_found():
    e = exceptions.UserNotFound()
    assert 404 == e.status_code
    assert "user not found" == e.message
    with app.app_context():
        resp = e.get_response()
        assert 'application/json' == resp.content_type
        assert b'{"error":"user not found"}\n' == resp.data


def test_payment_error():
    e = exceptions.PaymentError()
    assert 500 == e.status_code
    assert "想定外のエラー" == e.message
    with app.app_context():
        resp = e.get_response()
        assert 'application/json' == resp.content_type
        assert b'{"error":"\\u60f3\\u5b9a\\u5916\\u306e\\u30a8\\u30e9\\u30fc"}\n' == resp.data
