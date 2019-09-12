# -*- coding: utf-8 -*-

import socket
import os
import datetime
import subprocess

import flask
import bcrypt
import requests
from sqlalchemy import and_, or_

from . import (utils,
               database,
               models,
               )

static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../public'))

app = flask.Flask(__name__, static_folder=str(static_folder), static_url_path='', template_folder=static_folder)
app.config['SECRET_KEY'] = 'isucari'
app.config['UPLOAD_FOLDER'] = os.path.join(static_folder, 'upload')
app.config['SQLALCHEMY_DATABASE_URI'] = database.get_dsn()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

database.init_db(app)


class Constants(object):
    DEFAULT_PAYMENT_SERVICE_URL = "http://127.0.0.1:5555"
    DEFAULT_SHIPMENT_SERVICE_URL = "http://127.0.0.1:7000"

    ISUCARI_API_TOKEN = 'Bearer 75ugk2m37a750fwir5xr-22l6h4wmue1bwrubzwd0'

    PAYMENT_SERVICE_ISUCARI_API_KEY = 'a15400e46c83635eb181-946abb51ff26a868317c'
    PAYMENT_SERVICE_ISUCARI_SHOP_ID = '11'

    ITEMS_PER_PAGE = 48
    TRANSACTIONS_PER_PAGE = 10
    BUMP_ALLOW_SECONDS = 3


class HttpException(Exception):
    status_code = 500

    def __init__(self, status_code, message):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code

    def get_response(self):
        response = flask.jsonify({'error': self.message})
        response.status_code = self.status_code
        return response


def http_json_error(code, msg):
    raise HttpException(code, msg)


@app.errorhandler(HttpException)
def handle_http_exception(error):
    return error.get_response()


def get_current_user():
    user_id = flask.session.get("user_id")
    if user_id is None:
        http_json_error(requests.codes['not_found'], "no session")
    return get_user_by_id(user_id)


def get_user_or_none():
    user_id = flask.session.get("user_id")
    if user_id is None:
        return None
    return models.User.query.get(user_id)


def get_user_by_id(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        raise HttpException(requests.codes.not_found, "user not found")
    return user


def get_category_by_id(category_id):
    category = models.Category.query.get(category_id)
    if category is None:
        raise HttpException(requests.codes.not_found, "category not found")
    if category.parent_id != 0:
        parent = models.Category.query.get(category.parent_id)
        category.parent_category_name = parent.category_name
    return category


def ensure_required_payload(keys=None):
    if keys is None:
        keys = []
    for k in keys:
        if not flask.request.json.get(k):
            http_json_error(requests.codes['bad_request'], 'all parameters are required')


def ensure_valid_csrf_token():
    if flask.request.json['csrf_token'] != flask.session['csrf_token']:
        http_json_error(requests.codes['unprocessable_entity'], "csrf token error")


def get_config(name):
    return models.Config.query.get(name)


def get_payment_service_url():
    config = get_config("payment_service_url")
    return Constants.DEFAULT_PAYMENT_SERVICE_URL if config is None else config.val


def get_shipment_service_url():
    config = get_config("shipment_service_url")
    return Constants.DEFAULT_SHIPMENT_SERVICE_URL if config is None else config.val


def api_shipment_status(shipment_url, params=None):
    if params is None:
        params = {}
    try:
        res = requests.post(
            shipment_url + "/status",
            headers=dict(Authorization=Constants.ISUCARI_API_TOKEN),
            json=params,
        )
        res.raise_for_status()
        return res.json()
    except (socket.gaierror, requests.HTTPError) as err:
        app.logger.exception(err)
        http_json_error(requests.codes.internal_server_error, "")


# API
@app.route("/initialize", methods=["POST"])
def post_initialize():
    subprocess.call(["../sql/init.sh"])

    payment_service_url = flask.request.json.get('payment_service_url', Constants.DEFAULT_PAYMENT_SERVICE_URL)
    shipment_service_url = flask.request.json.get('shipment_service_url', Constants.DEFAULT_SHIPMENT_SERVICE_URL)

    payment_service_url_config = models.Config(name="payment_service_url", val=payment_service_url)
    database.db.session.add(payment_service_url_config)

    shipment_service_url_config = models.Config(name="shipment_service_url", val=shipment_service_url)
    database.db.session.add(payment_service_url_config)
    database.db.session.add(shipment_service_url_config)
    database.db.session.commit()

    return flask.jsonify({
        "campaign": 0,  # キャンペーン実施時には還元率の設定を返す。詳しくはマニュアルを参照のこと。
        "language": "python"  # 実装言語を返す
    })


@app.route("/new_items.json", methods=["GET"])
def get_new_items():
    item_id = 0
    created_at = 0

    item_id_str = flask.request.args.get('item_id')
    if item_id_str:
        if not item_id_str.isdecimal() or int(item_id_str) < 0:
            http_json_error(requests.codes['bad_request'], "item_id param error")
        item_id = int(item_id_str)

    created_at_str = flask.request.args.get('created_at')
    if created_at_str:
        if not created_at_str.isdecimal() or int(created_at_str) < 0:
            http_json_error(requests.codes['bad_request'], "created_at param error")
        created_at = int(created_at_str)
    if item_id > 0 and created_at > 0:
        # paging
        results = models.Item.query.filter(
            models.Item.status.in_([models.ItemStatus.on_sale, models.ItemStatus.sold_out]),
            or_(models.Item.created_at < datetime.datetime.fromtimestamp(created_at),
                and_(models.Item.created_at <= datetime.datetime.fromtimestamp(created_at),
                     models.Item.id < item_id))) \
            .order_by(models.Item.created_at.desc(), models.Item.id.desc()) \
            .limit(Constants.ITEMS_PER_PAGE + 1)
    else:
        results = models.Item.query.filter(
            models.Item.status.in_([models.ItemStatus.on_sale, models.ItemStatus.sold_out])) \
            .order_by(models.Item.created_at.desc(), models.Item.id.desc()) \
            .limit(Constants.ITEMS_PER_PAGE + 1)
    items = []
    for row in results:
        row.seller = get_user_by_id(row.seller_id).for_simple_json()
        row.category = get_category_by_id(row.category_id).for_json()
        row.image_url = utils.get_image_url(row.image_name)
        items.append(row)

    has_next = False
    if len(items) > Constants.ITEMS_PER_PAGE:
        has_next = True
        items = items[:Constants.ITEMS_PER_PAGE]

    return flask.jsonify(dict(
        items=[i.for_simple_json() for i in items],
        has_next=has_next,
    ))


@app.route("/new_items/<root_category_id>.json", methods=["GET"])
def get_new_category_items(root_category_id=None):
    root_category = get_category_by_id(root_category_id)

    item_id = 0
    created_at = 0

    item_id_str = flask.request.args.get('item_id')
    if item_id_str:
        if not item_id_str.isdecimal() or int(item_id_str) < 0:
            http_json_error(requests.codes['bad_request'], "item_id param error")
        item_id = int(item_id_str)

    created_at_str = flask.request.args.get('created_at')
    if created_at_str:
        if not created_at_str.isdecimal() or int(created_at_str) < 0:
            http_json_error(requests.codes['bad_request'], "created_at param error")
        created_at = int(created_at_str)

    categories = models.Category.query.filter(models.Category.parent_id == root_category_id).with_entities(
        models.Category.id)

    if item_id > 0 and created_at > 0:
        results = models.Item.query.filter(
            models.Item.status.in_([models.ItemStatus.on_sale, models.ItemStatus.sold_out]),
            models.Item.category_id.in_(categories),
            or_(models.Item.created_at < datetime.datetime.fromtimestamp(created_at), models.Item.id < item_id)) \
            .order_by(models.Item.created_at.desc()) \
            .order_by(models.Item.id.desc()) \
            .limit(Constants.ITEMS_PER_PAGE + 1)
    else:
        results = models.Item.query.filter(
            models.Item.status.in_([models.ItemStatus.on_sale, models.ItemStatus.sold_out]),
            models.Item.category_id.in_(categories)) \
            .order_by(models.Item.created_at.desc()) \
            .order_by(models.Item.id.desc()) \
            .limit(Constants.ITEMS_PER_PAGE + 1)
    items = []
    for row in results:
        row.seller = get_user_by_id(row.seller_id).for_simple_json()
        row.category = get_category_by_id(row.category_id).for_json()
        row.image_url = utils.get_image_url(row.image_name)
        items.append(row)

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

    item_id = 0
    created_at = 0

    item_id_str = flask.request.args.get('item_id')
    if item_id_str:
        if not item_id_str.isdecimal() or int(item_id_str) < 0:
            http_json_error(requests.codes['bad_request'], "item_id param error")
        item_id = int(item_id_str)

    created_at_str = flask.request.args.get('created_at')
    if created_at_str:
        if not created_at_str.isdecimal() or int(created_at_str) < 0:
            http_json_error(requests.codes['bad_request'], "created_at param error")
        created_at = int(created_at_str)

    if item_id > 0 and created_at > 0:
        # paging
        result = models.Item.query \
            .filter(or_(models.Item.seller_id == user.id, models.Item.buyer_id == user.id), models.Item.status.in_([
                models.ItemStatus.on_sale,
                models.ItemStatus.trading,
                models.ItemStatus.sold_out,
                models.ItemStatus.cancel,
                models.ItemStatus.stop])) \
            .filter(or_(models.Item.created_at < datetime.datetime.fromtimestamp(created_at),
                        and_(models.Item.created_at <= datetime.datetime.fromtimestamp(created_at),
                             models.Item.created_at < item_id))) \
            .order_by(models.Item.created_at.desc()) \
            .order_by(models.Item.id.desc()) \
            .limit(Constants.ITEMS_PER_PAGE + 1)
    else:
        # 1st page
        result = models.Item.query \
            .filter(or_(models.Item.seller_id == user.id, models.Item.buyer_id == user.id), models.Item.status.in_([
                models.ItemStatus.on_sale,
                models.ItemStatus.trading,
                models.ItemStatus.sold_out,
                models.ItemStatus.cancel,
                models.ItemStatus.stop])) \
            .order_by(models.Item.created_at.desc()) \
            .order_by(models.Item.id.desc()) \
            .limit(Constants.ITEMS_PER_PAGE + 1)
    items = []
    for row in result:
        row.seller = get_user_by_id(row.seller_id).for_simple_json()
        row.category = get_category_by_id(row.category_id).for_json()
        row.image_url = utils.get_image_url(row.image_name)

        transaction_evidence = models.TransactionEvidences.query.filter(
            models.TransactionEvidences.item_id == row.id).one()
        if transaction_evidence is not None:
            shipping = models.Shipping.query.get(transaction_evidence.id)
            if not shipping:
                raise HttpException(requests.codes.not_found, "shipping not found")
            ssr = api_shipment_status(get_shipment_service_url(), {"reserve_id": shipping.reserve_id})
            row.transaction_evidence_id = transaction_evidence.id
            row.transaction_evidence_status = transaction_evidence.status
            row.shipping_status = ssr["status"]
        items.append(row)

    has_next = False
    if len(items) > Constants.TRANSACTIONS_PER_PAGE:
        has_next = True
        items = items[:Constants.TRANSACTIONS_PER_PAGE]

    return flask.jsonify(dict(
        items=[i.for_detail_json() for i in items],
        has_next=has_next,
    ))


@app.route("/users/<user_id>.json", methods=["GET"])
def get_user_items(user_id=None):
    user = get_user_by_id(user_id)

    item_id = 0
    created_at = 0

    item_id_str = flask.request.args.get('item_id')
    if item_id_str:
        if not item_id_str.isdecimal() or int(item_id_str) < 0:
            http_json_error(requests.codes['bad_request'], "item_id param error")
        item_id = int(item_id_str)

    created_at_str = flask.request.args.get('created_at', 0)
    if created_at_str:
        if not created_at_str.isdecimal() or int(created_at_str) < 0:
            http_json_error(requests.codes['bad_request'], "created_at param error")
        created_at = int(created_at_str)

    if item_id > 0 and created_at > 0:
        # paging
        result = models.Item.query \
            .filter(models.Item.seller_id == user.id, models.Item.status.in_([
                models.ItemStatus.on_sale,
                models.ItemStatus.trading,
                models.ItemStatus.sold_out])) \
            .filter(
                or_(models.Item.created_at < datetime.datetime.fromtimestamp(created_at),
                    and_(models.Item.created_at <= datetime.datetime.fromtimestamp(created_at),
                         models.Item.created_at < item_id))) \
            .order_by(models.Item.created_at.desc()) \
            .order_by(models.Item.id.desc()) \
            .limit(Constants.ITEMS_PER_PAGE + 1)
    else:
        # 1st page
        # SELECT items.id AS items_id, items.seller_id AS items_seller_id, items.buyer_id AS items_buyer_id, items.status AS items_status, items.name AS items_name, items.price AS items_price, items.description AS items_description, items.image_name AS items_image_name, items.category_id AS items_category_id, items.created_at AS items_created_at, items.updated_at AS items_updated_at
        # FROM items
        # WHERE items.seller_id = %(seller_id_1)s AND items.status IN (%(status_1)s, %(status_2)s, %(status_3)s) ORDER BY items.created_at DESC, items.id DESC
        # LIMIT %(param_1)s
        result = models.Item.query \
            .filter(models.Item.seller_id == user.id, models.Item.status.in_([
                models.ItemStatus.on_sale,
                models.ItemStatus.trading,
                models.ItemStatus.sold_out])) \
            .order_by(models.Item.created_at.desc()) \
            .order_by(models.Item.id.desc()) \
            .limit(Constants.ITEMS_PER_PAGE + 1)
    items = []
    for row in result:
        row.seller = get_user_by_id(row.seller_id).for_simple_json()
        row.category = get_category_by_id(row.category_id)
        row["image_url"] = utils.get_image_url(row.image_name)
        items.append(row)

    has_next = False
    if len(items) > Constants.ITEMS_PER_PAGE:
        has_next = True
        items = items[:Constants.ITEMS_PER_PAGE]

    return flask.jsonify(dict(
        user=user.for_simple_json(),
        items=[i.for_simple_json() for i in items],
        has_next=has_next,
    ))


@app.route("/items/<item_id>.json", methods=["GET"])
def get_item(item_id=None):
    user = get_current_user()

    item = models.Item.query.get(item_id)
    if item is None:
        http_json_error(requests.codes['not_found'], "item not found")

    seller = models.User.query.get(item.seller_id)
    category = get_category_by_id(item.category_id)

    item.category = category.for_json()
    item.seller = seller.for_json()
    item.image_url = utils.get_image_url(item.image_name)

    if (user.id == item.seller_id or user.id == item.buyer_id) and item.buyer_id != 0:
        buyer = get_user_by_id(item.buyer_id)

        item.buyer = buyer.for_simple_json()
        item.buyer_id = buyer.id

        transaction_evidence = models.TransactionEvidences.query.filter(item_id=item.id).one()
        item.transaction_evidence_id = transaction_evidence.id
        item.transaction_evidence_status = transaction_evidence.status

        shipping = models.Shipping.query.filter(transaction_evidence_id=transaction_evidence.id).one()
        if not shipping:
            http_json_error(requests.codes['not_found'], "shipping not found")

        ssr = api_shipment_status(get_shipment_service_url(), {"reserve_id": shipping.reserve_id})
        item.shipping_status = ssr["status"]
    else:
        item.buyer = {}
        item.buyer_id = 0

    return flask.jsonify(item.for_detail_json())


@app.route("/items/edit", methods=["POST"])
def post_item_edit():
    ensure_valid_csrf_token()
    ensure_required_payload(['item_price', 'item_id'])

    price = int(flask.request.json['item_price'])
    item_id = int(flask.request.json['item_id'])
    if not 100 <= price <= 1000000:
        http_json_error(requests.codes['bad_request'], "商品価格は100ｲｽｺｲﾝ以上、1,000,000ｲｽｺｲﾝ以下にしてください")
    user = get_current_user()

    item = models.Item.query.get(item_id).with_for_update()
    if item is None:
        http_json_error(requests.codes['not_found'], "item not found")
    if item.seller_id != user.id:
        http_json_error(requests.codes['forbidden'], "自分の商品以外は編集できません")
    if item.status != models.ItemStatus.on_sale:
        http_json_error(requests.codes['forbidden'], "販売中の商品以外編集できません")
    item.price = flask.request.json["item_price"]
    item.updated_at = datetime.datetime.now()

    database.db.session.update(item)
    database.db.session.commit()

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

    target_item = models.Item.query.get(flask.request.json['item_id']).with_for_update()
    if target_item is None:
        http_json_error(requests.codes['not_found'], "item not found")
    if target_item['status'] != models.ItemStatus.on_sale:
        http_json_error(requests.codes['forbidden'], "item is not for sale")
    if target_item['seller_id'] == buyer['id']:
        http_json_error(requests.codes['forbidden'], "自分の商品は買えません")

    seller = models.User.query.get(target_item['seller_id']).with_for_update()
    if seller is None:
        http_json_error(requests.codes['not_found'], "seller not found")
    category = get_category_by_id(target_item['category_id'])

    transaction_evidence = models.TransactionEvidences(
        seller_id=seller.id,
        buyer_id=buyer.id,
        status=models.TransactionEvidenceStatus.wait_shipping,
        item_id=target_item.id,
        item_name=target_item.name,
        item_price=target_item.price,
        item_description=target_item.description,
        item_category_id=category.id,
        item_root_category_id=category.parent_id,
    )
    database.db.session.add(transaction_evidence)
    target_item.buyer_id = buyer.id
    target_item.status = models.ItemStatus.trading
    target_item.updated_at = datetime.datetime.now()
    database.db.session.update(target_item)

    host = get_shipment_service_url()
    try:
        res = requests.post(host + "/create",
                            headers=dict(Authorization=Constants.ISUCARI_API_TOKEN),
                            json=dict(
                                to_address=buyer['address'],
                                to_name=buyer['account_name'],
                                from_address=seller['address'],
                                from_name=seller['account_name'],
                            ))
        res.raise_for_status()
        shipping_res = res.json()
    except (socket.gaierror, requests.HTTPError) as er:
        app.logger.exception(er)
        http_json_error(requests.codes['internal_server_error'])

    host = get_payment_service_url()
    try:
        res = requests.post(host + "/token",
                            json=dict(
                                shop_id=Constants.PAYMENT_SERVICE_ISUCARI_SHOP_ID,
                                api_key=Constants.PAYMENT_SERVICE_ISUCARI_API_KEY,
                                token=flask.request.json['token'],
                                price=target_item['price'],
                            ))
        res.raise_for_status()
        payment_res = res.json()
        if payment_res['status'] == "invalid":
            http_json_error(requests.codes["bad_request"], "カード情報に誤りがあります")
        if payment_res['status'] == "fail":
            http_json_error(requests.codes["bad_request"], "カードの残高が足りません")
        if payment_res['status'] != "ok":
            http_json_error(requests.codes["bad_request"], "想定外のエラー")
    except (socket.gaierror, requests.HTTPError) as er:
        app.logger.exception(er)
        http_json_error(requests.codes['internal_server_error'])

    shipping = models.Shipping(
        transaction_evidence_id=transaction_evidence.id,
        status=models.ShippingStatus.initial,
        item_name=target_item.name,
        item_id=target_item.id,
        reserve_id=shipping_res["reserve_id"],
        reserve_time=shipping_res["reserve_time"],
        to_address=buyer.address,
        to_name=buyer.name,
        from_address=seller.address,
        from_name=seller.name,
        img_binary=""
    )
    database.db.session.add(shipping)

    database.db.session.commit()

    return flask.jsonify(dict(transaction_evidence_id=transaction_evidence.id))


@app.route("/sell", methods=["POST"])
def post_sell():
    if flask.request.form['csrf_token'] != flask.session['csrf_token']:
        http_json_error(requests.codes['unprocessable_entity'], "csrf token error")
    for k in ["name", "description", "price", "category_id"]:
        if k not in flask.request.form or len(flask.request.form[k]) == 0:
            http_json_error(requests.codes['bad_request'], 'all parameters are required')

    price = int(flask.request.form['price'])
    if not 100 <= price <= 1000000:
        http_json_error(requests.codes['bad_request'], "商品価格は100ｲｽｺｲﾝ以上、1,000,000ｲｽｺｲﾝ以下にしてください")

    category = get_category_by_id(flask.request.form['category_id'])
    if category['parent_id'] == 0:
        http_json_error(requests.codes['bad_request'], 'Incorrect category ID')
    user = get_current_user()

    if "image" not in flask.request.files:
        http_json_error(requests.codes['internal_server_error'], 'image error')

    file = flask.request.files['image']
    ext = os.path.splitext(file.filename)[1]
    if ext not in ('.jpg', 'jpeg', '.png', 'gif'):
        http_json_error(requests.codes['bad_request'], 'unsupported image format error error')
    if ext == ".jpeg":
        ext = ".jpg"
    imagename = "{0}{1}".format(utils.random_string(32), ext)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagename))

    seller = models.User.query.get(user.id).with_for_update()
    if seller is None:
        http_json_error(requests['not_found'], 'user not found')
    item = models.Item(
        seller_id=seller.id,
        status=models.ItemStatus.on_sale,
        name=flask.request.form['name'],
        price=price,
        description=flask.request.form['description'],
        image_name=imagename,
        category_id=flask.request.form['category_id'],
    )
    database.db.session.add(item)
    seller.num_sell_items = seller.num_sell_items + 1
    seller.last_bump = datetime.datetime.now()
    database.db.session.update(seller)
    database.db.session.commit()

    return flask.jsonify({
        'id': item.id,
    })


@app.route("/ship", methods=["POST"])
def post_ship():
    ensure_valid_csrf_token()
    user = get_current_user()

    transaction_evidence = models.TransactionEvidences.query.filter(item_id=flask.request.json["item_id"]).one()
    if transaction_evidence is None:
        http_json_error(requests.codes["not_found"], "transaction_evidences not found")
    if transaction_evidence.seller_id != user.id:
        http_json_error(requests.codes['forbidden'], "権限がありません")

    item = models.Item.query.get(flask.request.json["item_id"]).with_for_update()
    if item is None:
        http_json_error(requests.codes["not_found"], "item not found")
    if item.status != models.ItemStatus.trading:
        http_json_error(requests.codes["forbidden"], "商品が取引中ではありません")
    transaction_evidence = models.TransactionEvidences.query.get(transaction_evidence.id).with_for_update()
    if transaction_evidence is None:
        http_json_error(requests.codes["not_found"], "transaction_evidences not found")
    if transaction_evidence.status != models.TransactionEvidenceStatus.wait_shipping:
        http_json_error(requests.codes['forbidden'], "準備ができていません")

    shipping = models.Shipping.query.filter(transaction_evidence_id=transaction_evidence.id).one().with_for_update()
    if shipping is None:
        http_json_error(requests.codes["not_found"], "shipping not found")
    try:
        host = get_shipment_service_url()
        res = requests.post(host + "/request",
                            headers=dict(Authorization=Constants.ISUCARI_API_TOKEN),
                            json=dict(reserve_id=shipping["reserve_id"]))
        res.raise_for_status()
    except (socket.gaierror, requests.HTTPError) as err:
        app.logger.exception(err)
        http_json_error(requests.codes["internal_server_error"], "failed to request to shipment service")
    shipping.status = models.ShippingStatus.wait_pickup
    shipping.img_binary = res.content
    shipping.updated_at = datetime.datetime.now()

    database.db.session.update(shipping)
    database.db.session.commit()

    return flask.jsonify(dict(
        path="/transactions/{}.png".format(transaction_evidence.id),
        reserve_id=shipping.reserve_id,
    ))


@app.route("/ship_done", methods=["POST"])
def post_ship_done():
    ensure_valid_csrf_token()
    user = get_current_user()

    transaction_evidence = models.TransactionEvidenceStatus.query.filter(item_id=flask.request.json["item_id"]).one()
    if transaction_evidence is None:
        http_json_error(requests.codes["not_found"], "transaction_evidences not found")
    if transaction_evidence.seller_id != user.id:
        http_json_error(requests.codes['forbidden'], "権限がありません")

    item = models.Item.query.get(flask.request.json["item_id"]).with_for_update()
    if item is None:
        http_json_error(requests.codes["not_found"], "item not found")
    if item.status != models.ItemStatus.trading:
        http_json_error(requests.codes["forbidden"], "商品が取引中ではありません")

    transaction_evidence = models.TransactionEvidences.query.get(transaction_evidence.id).with_for_update()
    if transaction_evidence is None:
        http_json_error(requests.codes["not_found"], "transaction_evidences not found")
    if transaction_evidence.status != models.TransactionEvidenceStatus.wait_shipping:
        http_json_error(requests.codes['forbidden'], "準備ができていません")

    shipping = models.Shipping.query.filter(transaction_evidence_id=transaction_evidence.id).one().with_for_update()
    if shipping is None:
        http_json_error(requests.codes["not_found"], "shipping not found")

    ssr = api_shipment_status(get_shipment_service_url(), {"reserve_id": shipping["reserve_id"]})

    if ssr["status"] not in [str(s) for s in (models.ShippingStatus.done, models.ShippingStatus.shipping)]:
        http_json_error(requests.codes["forbidden"], "shipment service側で配送中か配送完了になっていません")
    shipping.status = models.Shipping[ssr["status"]]
    shipping.updated_at = datetime.datetime.now()
    database.db.session.update(shipping)

    transaction_evidence.status = models.TransactionEvidenceStatus.wait_done
    transaction_evidence.updated_at = datetime.datetime.now()
    database.db.session.update(transaction_evidence)

    database.db.session.commit()

    return flask.jsonify(dict(transaction_evidence_id=transaction_evidence.id))


@app.route("/complete", methods=["POST"])
def post_complete():
    ensure_valid_csrf_token()
    user = get_current_user()
    item_id = flask.request.json["item_id"]

    transaction_evidence = models.TransactionEvidences.query.filter(item_id=item_id).one()
    if transaction_evidence is None:
        http_json_error(requests.codes["not_found"], "transaction_evidences not found")
    if transaction_evidence.buyer_id != user.id:
        http_json_error(requests.codes['forbidden'], "権限がありません")

    item = models.Item.query.get(item_id).with_for_update()
    if item is None:
        http_json_error(requests.codes["not_found"], "item not found")
    if item.status != models.ItemStatus.trading:
        http_json_error(requests.codes["forbidden"], "商品が取引中ではありません")

    transaction_evidence = models.TransactionEvidences.query.filter(item_id=item_id).one().with_for_update()
    if transaction_evidence is None:
        http_json_error(requests.codes["not_found"], "transaction_evidences not found")
    if transaction_evidence.status != models.TransactionEvidenceStatus.wait_done:
        http_json_error(requests.codes['forbidden'], "準備ができていません")

    shipping = models.Shipping.query.filter(transaction_evidence_id=transaction_evidence.id).one().with_for_update()
    if transaction_evidence["buyer_id"] != user.id:
        http_json_error(requests.codes['forbidden'], "権限がありません")
    ssr = api_shipment_status(get_shipment_service_url(), {"reserve_id": shipping.reserve_id})

    if ssr["status"] != str(models.ShippingStatus.done):
        http_json_error(requests.codes["bad_request"], "shipment service側で配送完了になっていません")
    shipping.status = models.ShippingStatus.done
    shipping.updated_at = datetime.datetime.now()
    database.db.session.update(shipping)

    transaction_evidence.status = models.TransactionEvidenceStatus.done
    transaction_evidence.updated_at = datetime.datetime.now()
    database.db.session.update(transaction_evidence)

    item.status = models.ItemStatus.sold_out
    item.updated_at = datetime.datetime.now()
    database.db.session.update(item)

    database.db.session.commit()

    return flask.jsonify(dict(transaction_evidence_id=transaction_evidence.id))


@app.route("/transactions/<transaction_evidence_id>.png", methods=["GET"])
def get_qrcode(transaction_evidence_id):
    if transaction_evidence_id:
        if not transaction_evidence_id.isdecimal() or int(transaction_evidence_id) <= 0:
            http_json_error(requests.codes['bad_request'], "incorrect transaction_evidence id")

    seller = get_current_user()
    transaction_evidence = models.TransactionEvidences.query.get(transaction_evidence_id)
    if transaction_evidence is None:
        http_json_error(requests.codes['not_found'], "transaction_evidences not found")
    if transaction_evidence.seller_id != seller.id:
        http_json_error(requests.codes['forbidden'], "権限がありません")
    shipping = models.Shipping.query.filter(transaction_evidence_id=transaction_evidence.id).one()
    if shipping is None:
        http_json_error(requests.codes['not_found'], "shippings not found")
    if shipping.status != str(models.ShippingStatus.wait_pickup) and \
            shipping.status != str(models.ShippingStatus.shipping):
        http_json_error(requests.codes['forbidden'], "qrcode not available")
    if len(shipping.img_binary) == 0:
        http_json_error(requests.codes['internal_server_error'], "empty qrcode image")

    res = flask.make_response(shipping.img_binary)
    res.headers.set('Content-Type', 'image/png')

    return res


@app.route("/bump", methods=["POST"])
def post_bump():
    ensure_valid_csrf_token()
    ensure_required_payload(['item_id'])
    user = get_current_user()

    item = models.Item.query.get(flask.request.json['item_id']).with_for_update()
    if item is None:
        raise HttpException(requests.codes.not_found, "item not found")
    if item.seller_id != user.id:
        raise HttpException(requests.codes.forbidden, "自分の商品以外は編集できません")
    seller = models.User.query.get(user.id).with_for_update()
    if seller is None:
        raise HttpException(requests.codes.not_found, "user not found")

    now = datetime.datetime.now()
    if seller.last_bump + datetime.timedelta(seconds=Constants.BUMP_ALLOW_SECONDS) > now:
        raise HttpException(requests.codes.forbidden, "Bump not allowed")

    item.created_at = now
    item.updated_at = now
    database.db.session.update(item)

    seller.last_bump = now
    database.db.session.update(seller)

    target_item = models.Item.query.get(item['id'])
    database.db.session.commit()

    return flask.jsonify({
        'item_id': target_item.id,
        'item_price': target_item.price,
        'item_created_at': int(target_item.created_at.timestamp()),
        'item_updated_at': int(target_item.updated_at.timestamp()),
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
    outputs['payment_service_url'] = get_payment_service_url()

    return flask.jsonify(outputs)


@app.route("/login", methods=["POST"])
def post_login():
    ensure_required_payload(['account_name', 'password'])
    user = models.User.query.filter_by(account_name=flask.request.json['account_name']).first()
    if user is None or \
            not bcrypt.checkpw(flask.request.json['password'].encode('utf-8'), user.hashed_password):
        http_json_error(requests.codes['unauthorized'], 'アカウント名かパスワードが間違えています')
    flask.session['user_id'] = user.id
    flask.session['csrf_token'] = utils.random_string(10)
    return flask.jsonify(
        user.for_json()
    )


@app.route("/register", methods=["POST"])
def post_register():
    ensure_required_payload(['account_name', 'password', 'address'])
    hashedpw = bcrypt.hashpw(flask.request.json['password'].encode('utf-8'), bcrypt.gensalt(10))

    try:
        user = models.User(account_name=flask.request.json['account_name'], hashed_password=hashedpw,
                           address=flask.request.json['address'])
        database.db.session.add(user)
        database.db.session.commit()
        flask.session['user_id'] = user.id
        flask.session['csrf_token'] = utils.random_string(10)
        return flask.jsonify({
            'id': user.id,
            'account_name': flask.request.json['account_name'],
            'address': flask.request.json['address'],
        })
    except Exception as err:
        app.logger.exception(err)
        http_json_error(requests.codes['internal_server_error'], 'db error')


@app.route("/reports.json", methods=["GET"])
def get_reports():
    transaction_evidences = models.TransactionEvidences.query.filter(models.TransactionEvidences.id > 15007).all()
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