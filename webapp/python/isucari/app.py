# -*- coding: utf-8 -*-

import os
import subprocess

import flask
from flask_caching import Cache
import requests
from sqlalchemy.exc import SQLAlchemyError

from . import (utils,
               database,
               models,
               isucari,
               )
from .config import Constants, Config
from .exceptions import HttpException

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
static_folder = os.path.abspath(os.path.join(base_dir, '..', 'public'))

app = flask.Flask(__name__, static_folder=static_folder, static_url_path='', template_folder=static_folder)
app.config.from_mapping(Config)

cache = Cache(app)
database.init_db(app)


@app.errorhandler(HttpException)
def handle_http_exception(error):
    return error.get_response()


@app.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    response = flask.jsonify({'error': "db error"})
    response.status_code = requests.codes.server_error
    app.logger.exception(error)
    return response


def get_current_user():
    user_id = flask.session.get("user_id")
    if user_id is None:
        raise HttpException(requests.codes.not_found, "no session")
    return models.User.query.get(user_id)


def get_user_or_none():
    user_id = flask.session.get("user_id")
    if user_id is None:
        return None
    return models.User.query.get(user_id)


def ensure_required_payload(keys=None):
    if keys is None:
        keys = []
    data = {}
    for k in keys:
        if not flask.request.json.get(k):
            raise HttpException(requests.codes.bad_request, 'all parameters are required')
        data[k] = flask.request.json.get(k)
    return data


def ensure_valid_csrf_token():
    if flask.request.json['csrf_token'] != flask.session['csrf_token']:
        raise HttpException(requests.codes.unprocessable_entity, "csrf token error")


# API
@app.route("/initialize", methods=["POST"])
def post_initialize():
    d = os.path.abspath(os.path.join(base_dir, '..', 'sql'))
    subprocess.call([d + "/init.sh"])

    payment_service_url = flask.request.json.get('payment_service_url', Constants.DEFAULT_PAYMENT_SERVICE_URL)
    isucari.save_config('payment_service_url', payment_service_url)
    shipment_service_url = flask.request.json.get('shipment_service_url', Constants.DEFAULT_SHIPMENT_SERVICE_URL)
    isucari.save_config('shipment_service_url', shipment_service_url)

    return flask.jsonify({
        "campaign": 0,  # キャンペーン実施時には還元率の設定を返す。詳しくはマニュアルを参照のこと。
        "language": "python"  # 実装言語を返す
    })


@app.route("/new_items.json", methods=["GET"])
def get_new_items():
    item_id = flask.request.args.get('item_id', default=0, type=int)
    if item_id < 0:
        raise HttpException(requests.codes.bad_request, "item_id param error")

    created_at = flask.request.args.get('created_at', default=0, type=int)
    if created_at < 0:
        raise HttpException(requests.codes.bad_request, "created_at param error")

    items = isucari.timeline(item_id, created_at)
    has_next = False
    if len(items) > Constants.ITEMS_PER_PAGE:
        has_next = True
        items = items[:Constants.ITEMS_PER_PAGE]

    return flask.jsonify(dict(
        items=[i.for_simple_json() for i in items],
        has_next=has_next,
    ))


@app.route("/new_items/<int:root_category_id>.json", methods=["GET"])
def get_new_category_items(root_category_id=None):
    item_id = flask.request.args.get('item_id', default=0, type=int)
    if item_id < 0:
        raise HttpException(requests.codes.bad_request, "item_id param error")

    created_at = flask.request.args.get('created_at', default=0, type=int)
    if created_at < 0:
        raise HttpException(requests.codes.bad_request, "created_at param error")

    root_category, items = isucari.category_items(item_id, created_at, root_category_id)

    has_next = False
    if len(items) > Constants.ITEMS_PER_PAGE:
        has_next = True
        items = items[:Constants.ITEMS_PER_PAGE]

    return flask.jsonify(dict(
        root_category_id=root_category.id,
        root_category_name=root_category.category_name,
        items=[i.for_simple_json() for i in items],
        has_next=has_next,
    ))


@app.route("/users/transactions.json", methods=["GET"])
def get_transactions():
    user = get_current_user()

    item_id = flask.request.args.get('item_id', default=0, type=int)
    if item_id < 0:
        raise HttpException(requests.codes.bad_request, "item_id param error")

    created_at = flask.request.args.get('created_at', default=0, type=int)
    if created_at < 0:
        raise HttpException(requests.codes.bad_request, "created_at param error")

    items = isucari.transaction_items(user, item_id, created_at)

    has_next = False
    if len(items) > Constants.TRANSACTIONS_PER_PAGE:
        has_next = True
        items = items[:Constants.TRANSACTIONS_PER_PAGE]

    return flask.jsonify(dict(
        items=[i.for_detail_json() for i in items],
        has_next=has_next,
    ))


@app.route("/users/<int:user_id>.json", methods=["GET"])
def get_user_items(user_id=None):
    user = models.User.query.get(user_id)

    item_id = flask.request.args.get('item_id', default=0, type=int)
    if item_id < 0:
        raise HttpException(requests.codes.bad_request, "item_id param error")

    created_at = flask.request.args.get('created_at', default=0, type=int)
    if created_at < 0:
        raise HttpException(requests.codes.bad_request, "created_at param error")

    items = isucari.user_time_line(user, item_id, created_at)
    has_next = False
    if len(items) > Constants.ITEMS_PER_PAGE:
        has_next = True
        items = items[:Constants.ITEMS_PER_PAGE]

    return flask.jsonify(dict(
        user=user.for_simple_json(),
        items=[i.for_simple_json() for i in items],
        has_next=has_next,
    ))


@app.route("/items/<int:item_id>.json", methods=["GET"])
def get_item(item_id=None):
    user = get_current_user()
    item = isucari.get_item(user, item_id)

    return flask.jsonify(item.for_detail_json())


@app.route("/items/edit", methods=["POST"])
def post_item_edit():
    ensure_valid_csrf_token()
    data = ensure_required_payload(['item_price', 'item_id'])

    price = int(data['item_price'])
    item_id = int(data['item_id'])
    user = get_current_user()

    item = isucari.edit(user, item_id, price)

    return flask.jsonify(dict(
        item_id=item.id,
        item_price=item.price,
        item_created_at=int(item.created_at.timestamp()),
        item_updated_at=int(item.updated_at.timestamp()),
    ))


@app.route("/buy", methods=["POST"])
def post_buy():
    ensure_valid_csrf_token()
    buyer = get_current_user()

    item_id = int(flask.request.json['item_id'])
    token = flask.request.json['token']

    transaction_evidence_id = isucari.buy(buyer, item_id, token)

    return flask.jsonify(dict(transaction_evidence_id=transaction_evidence_id))


@app.route("/sell", methods=["POST"])
def post_sell():
    # form request
    if flask.request.form['csrf_token'] != flask.session['csrf_token']:
        raise HttpException(requests.codes.unprocessable_entity, "csrf token error")
    for k in ["name", "description", "price", "category_id"]:
        if k not in flask.request.form or len(flask.request.form[k]) == 0:
            raise HttpException(requests.codes.bad_request, 'all parameters are required')

    if "image" not in flask.request.files:
        raise HttpException(requests.codes.internal_server_error, 'image error')

    item = isucari.sell(get_current_user(),
                        flask.request.form['name'],
                        flask.request.form['description'],
                        int(flask.request.form['price']),
                        flask.request.form['category_id'],
                        flask.request.files['image']
                        )

    return flask.jsonify({
        'id': item.id,
    })


@app.route("/ship", methods=["POST"])
def post_ship():
    ensure_valid_csrf_token()
    user = get_current_user()
    item_id = flask.request.json["item_id"]

    transaction_id, reserve_id = isucari.ship(user, item_id)
    return flask.jsonify(dict(
        path="/transactions/{}.png".format(transaction_id),
        reserve_id=reserve_id,
    ))


@app.route("/ship_done", methods=["POST"])
def post_ship_done():
    ensure_valid_csrf_token()
    user = get_current_user()
    item_id = flask.request.json["item_id"]

    transaction_evidence = isucari.ship_done(user, int(item_id))

    return flask.jsonify(dict(transaction_evidence_id=transaction_evidence.id))


@app.route("/complete", methods=["POST"])
def post_complete():
    ensure_valid_csrf_token()
    user = get_current_user()
    item_id = flask.request.json["item_id"]

    transaction_evidence = isucari.complete(user, item_id)

    return flask.jsonify(dict(transaction_evidence_id=transaction_evidence.id))


@app.route("/transactions/<int:transaction_evidence_id>.png", methods=["GET"])
def get_qrcode(transaction_evidence_id):
    if int(transaction_evidence_id) <= 0:
        raise HttpException(requests.codes.bad_request, "incorrect transaction_evidence id")

    seller = get_current_user()
    shipping = isucari.get_qr_code(seller, transaction_evidence_id)

    res = flask.make_response(shipping.img_binary)
    res.headers.set('Content-Type', 'image/png')

    return res


@app.route("/bump", methods=["POST"])
def post_bump():
    ensure_valid_csrf_token()
    data = ensure_required_payload(['item_id'])
    user = get_current_user()

    item = isucari.bump(user, data)

    return flask.jsonify({
        'item_id': item.id,
        'item_price': item.price,
        'item_created_at': int(item.created_at.timestamp()),
        'item_updated_at': int(item.updated_at.timestamp()),
    })


@app.route("/settings", methods=["GET"])
def get_settings():
    outputs = dict()
    user = get_user_or_none()
    if user is not None:
        outputs['user'] = user.for_json()
    outputs['csrf_token'] = flask.session.get('csrf_token', '')
    categories = models.Category.query.all()
    outputs['categories'] = [c.for_json() for c in categories]
    outputs['payment_service_url'] = isucari.get_payment_service_url()

    return flask.jsonify(outputs)


@app.route("/login", methods=["POST"])
def post_login():
    data = ensure_required_payload(['account_name', 'password'])
    user = isucari.login(data)

    flask.session['user_id'] = user.id
    flask.session['csrf_token'] = utils.random_string(10)
    return flask.jsonify(
        user.for_json()
    )


@app.route("/register", methods=["POST"])
def post_register():
    data = ensure_required_payload(['account_name', 'password', 'address'])
    user = isucari.register(data)

    flask.session['user_id'] = user.id
    flask.session['csrf_token'] = utils.random_string(10)
    return flask.jsonify({
        'id': user.id,
        'account_name': user.account_name,
        'address': user.address,
    })


@app.route("/reports.json", methods=["GET"])
def get_reports():
    transaction_evidences = models.TransactionEvidences.query.filter(models.TransactionEvidences.id > 15007)
    return flask.jsonify([t.for_json() for t in transaction_evidences])


# Frontend
@app.route("/")
@app.route("/login")
@app.route("/register")
@app.route("/timeline")
@app.route("/categories/<category_id>/items")
@app.route("/sell")
@app.route("/items/<item_id>")
@app.route("/items/<item_id>/edit")
@app.route("/items/<item_id>/buy")
@app.route("/buy/compelete")
@app.route("/transactions/<transaction_id>")
@app.route("/users/<user_id>")
@app.route("/users/setting")
def get_index(*args, **kwargs):
    # if "user_id" in flask.session:
    #    return flask.redirect('/', 303)
    return flask.render_template('index.html')

# Assets
# @app.route("/*")
