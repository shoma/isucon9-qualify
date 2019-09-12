# -*- coding: utf-8 -*-

import bcrypt
import datetime
import os
from typing import List

from requests import codes
from werkzeug.datastructures import FileStorage
from sqlalchemy import and_, or_

from .config import Constants
from .models import (User, Item, TransactionEvidences, Shipping, Category, Config, ShippingStatus, ItemStatus,
                     TransactionEvidenceStatus)
from .database import db
from .exceptions import (HttpException, ItemNotFound, UserNotFound, TransactionEvidencesNotFound, ShippingNotFound)
from . import http_service, validator, utils, app

Items = List[Item]


def get_category_by_id(category_id):
    category = Category.query.get(category_id)
    if category is None:
        raise HttpException(codes.not_found, "category not found")
    if category.parent_id != 0:
        parent = get_category_by_id(category.parent_id)
        category.parent_category_name = parent.category_name
    return category


def get_config(name) -> Config:
    return Config.query.get(name)


def get_payment_service_url() -> str:
    config = get_config("payment_service_url")
    return Constants.DEFAULT_PAYMENT_SERVICE_URL if config is None else config.val


def get_shipment_service_url() -> str:
    config = get_config("shipment_service_url")
    return Constants.DEFAULT_SHIPMENT_SERVICE_URL if config is None else config.val


def timeline(item_id: int, created_at: int) -> Items:
    q = Item.query.filter(
        Item.status.in_([ItemStatus.on_sale, ItemStatus.sold_out]),
    )
    if item_id > 0 and created_at > 0:
        # paging
        ts = datetime.datetime.fromtimestamp(created_at)
        q.filter(
            or_(
                Item.created_at < ts,
                and_(Item.created_at <= ts,
                     Item.id < item_id)
            )
        )

    q.order_by(Item.created_at.desc(), Item.id.desc()).limit(Constants.ITEMS_PER_PAGE + 1)

    items = []
    for row in q:
        row.seller = User.query.get(row.seller_id).for_simple_json()
        row.category = get_category_by_id(row.category_id).for_json()
        row.image_url = utils.get_image_url(row.image_name)
        items.append(row)
    return items


def category_items(item_id: int, created_at: int, root_category_id: int) -> Items:
    categories = Category.query.filter(Category.parent_id == root_category_id).with_entities(Category.id)

    q = Item.query.filter(
        Item.status.in_([
            ItemStatus.on_sale,
            ItemStatus.sold_out,
        ]),
        Item.category_id.in_(categories),
    )
    if item_id > 0 and created_at > 0:
        # paging
        ts = datetime.datetime.fromtimestamp(created_at)
        q.filter(or_(
            Item.created_at < ts,
            Item.id < item_id
        ))
    q.order_by(Item.created_at.desc(), Item.id.desc()).limit(Constants.ITEMS_PER_PAGE+1)

    items = []
    for row in q:
        row.seller = User.query.get(row.seller_id).for_simple_json()
        row.category = get_category_by_id(row.category_id).for_json()
        row.image_url = utils.get_image_url(row.image_name)
        items.append(row)
    return items


def transaction_items(user: User, item_id: int, created_at: int) -> Items:
    q = Item.query.filter(
        or_(
            Item.seller_id == user.id,
            Item.buyer_id == user.id
        ),
        Item.status.in_([
            ItemStatus.on_sale,
            ItemStatus.trading,
            ItemStatus.sold_out,
            ItemStatus.cancel,
            ItemStatus.stop
        ])
    )

    if item_id > 0 and created_at > 0:
        # paging
        ts = datetime.datetime.fromtimestamp(created_at)
        q.filter(or_(
            Item.created_at < ts,
            and_(
                Item.created_at <= ts,
                Item.id < item_id
            )
        ))
    q.order_by(Item.created_at.desc(), Item.id.desc()).limit(Constants.ITEMS_PER_PAGE+1)

    items = []
    for row in q:
        row.seller = User.query.get(row.seller_id).for_simple_json()
        row.category = get_category_by_id(row.category_id).for_json()
        row.image_url = utils.get_image_url(row.image_name)

        transaction_evidence = TransactionEvidences.query.filter(
            TransactionEvidences.item_id == row.id).one_or_none()
        if transaction_evidence is not None:
            shipping = Shipping.query.get(transaction_evidence.id)
            if not shipping:
                raise ShippingNotFound()
            ssr = http_service.Shipping.status(get_shipment_service_url(), {"reserve_id": shipping.reserve_id})
            row.transaction_evidence_id = transaction_evidence.id
            row.transaction_evidence_status = transaction_evidence.status
            row.shipping_status = ssr["status"]
        items.append(row)
    return items


def user_time_line(user: User, item_id: int, created_at: int) -> Items:
    q = Item.query.filter(
        Item.seller_id == user.id,
        Item.status.in_([
            ItemStatus.on_sale,
            ItemStatus.trading,
            ItemStatus.sold_out,
        ]))
    if item_id > 0 and created_at > 0:
        # paging
        ts = datetime.datetime.fromtimestamp(created_at)
        q.filter(or_(Item.created_at < ts,
                     and_(Item.created_at <= ts,
                          Item.id < item_id)))
    q.order_by(Item.created_at.desc(), Item.id.desc()).limit(Constants.ITEMS_PER_PAGE + 1)
    items = []
    for row in q:
        row.seller = User.query.get(row.seller_id).for_simple_json()
        row.category = get_category_by_id(row.category_id)
        row.image_url = utils.get_image_url(row.image_name)
        items.append(row)
    return items


def get_item(user: User, item_id: int) -> Item:
    item = Item.query.get(item_id)
    if item is None:
        raise ItemNotFound()

    seller = User.query.get(item.seller_id)
    category = get_category_by_id(item.category_id)

    item.category = category.for_json()
    item.seller = seller.for_json()
    item.image_url = utils.get_image_url(item.image_name)

    if (user.id == item.seller_id or user.id == item.buyer_id) and item.buyer_id != 0:
        buyer = User.query.get(item.buyer_id)

        item.buyer = buyer.for_simple_json()
        item.buyer_id = buyer.id

        transaction_evidence = TransactionEvidences.query.filter(item_id=item.id).one_or_none()
        item.transaction_evidence_id = transaction_evidence.id
        item.transaction_evidence_status = transaction_evidence.status

        shipping = Shipping.query.filter(transaction_evidence_id=transaction_evidence.id).one_or_none()
        if not shipping:
            raise ShippingNotFound()

        ssr = http_service.Shipping.status(get_shipment_service_url(), {"reserve_id": shipping.reserve_id})
        item.shipping_status = ssr["status"]
    return item


def sell(user: User, name: str, description: str, price: int, category_id: int, image: FileStorage) -> Item:
    validator.validate_price(price)

    category = get_category_by_id(category_id)
    if category.parent_id == 0:
        raise HttpException(codes.bad_request, 'Incorrect category ID')

    ext = os.path.splitext(image.filename)[1]
    if ext not in ('.jpg', 'jpeg', '.png', 'gif'):
        raise HttpException(codes.bad_request, 'unsupported image format error error')
    if ext == ".jpeg":
        ext = ".jpg"
    imagename = "{0}{1}".format(utils.random_string(32), ext)
    image.save(os.path.join(app.config['UPLOAD_FOLDER'], imagename))

    seller = User.query.get(user.id).with_for_update()
    if seller is None:
        raise UserNotFound()
    item = Item(
        seller_id=seller.id,
        status=ItemStatus.on_sale,
        name=name,
        price=price,
        description=description,
        image_name=imagename,
        category_id=category_id,
    )
    db.session.add(item)

    seller.num_sell_items = seller.num_sell_items + 1
    seller.last_bump = datetime.datetime.now()
    db.session.update(seller)

    db.session.commit()
    return item


def edit(seller: User, item_id: int, price: int) -> Item:
    validator.validate_price(price)
    item = Item.query.get(item_id).with_for_update()
    if item is None:
        raise ItemNotFound()
    if item.seller_id != seller.id:
        raise HttpException(codes.forbidden, "自分の商品以外は編集できません")
    if item.status != ItemStatus.on_sale:
        raise HttpException(codes.forbidden, "販売中の商品以外編集できません")
    item.price = price
    item.updated_at = datetime.datetime.now()

    db.session.update(item)
    db.session.commit()
    return item


def buy(buyer: User, item_id: int, token: str) -> int:
    target_item = Item.query.get(item_id).with_for_update()
    if target_item is None:
        raise ItemNotFound()
    if target_item.status != ItemStatus.on_sale:
        raise HttpException(codes.forbidden, "item is not for sale")
    if target_item.seller_id == buyer.id:
        raise HttpException(codes.forbidden, "自分の商品は買えません")

    seller = User.query.get(target_item['seller_id']).with_for_update()
    if seller is None:
        raise HttpException(codes.not_found, "seller not found")
    category = get_category_by_id(target_item['category_id'])

    transaction_evidence = TransactionEvidences(
        seller_id=seller.id,
        buyer_id=buyer.id,
        status=TransactionEvidenceStatus.wait_shipping,
        item_id=target_item.id,
        item_name=target_item.name,
        item_price=target_item.price,
        item_description=target_item.description,
        item_category_id=category.id,
        item_root_category_id=category.parent_id,
    )
    db.session.add(transaction_evidence)

    target_item.buyer_id = buyer.id
    target_item.status = ItemStatus.trading
    target_item.updated_at = datetime.datetime.now()
    db.session.update(target_item)

    shipping_res = http_service.Shipping.create(get_shipment_service_url(), dict(
        to_address=buyer['address'],
        to_name=buyer['account_name'],
        from_address=seller['address'],
        from_name=seller['account_name'],
    ))

    http_service.Payment.token(get_payment_service_url(),
                               dict(token=token, price=target_item.price))

    shipping = Shipping(
        transaction_evidence_id=transaction_evidence.id,
        status=ShippingStatus.initial,
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
    db.session.add(shipping)

    db.session.commit()
    return transaction_evidence.id


def ship(user: User, item_id: int) -> (int, str):
    transaction_evidence = TransactionEvidences.query.filter(item_id=item_id).one_or_none()
    if transaction_evidence is None:
        raise TransactionEvidencesNotFound()
    if transaction_evidence.seller_id != user.id:
        raise HttpException(codes.forbidden, "権限がありません")

    item = Item.query.get(item_id).with_for_update()
    if item is None:
        raise ItemNotFound()
    if item.status != ItemStatus.trading:
        raise HttpException(codes.forbidden, "商品が取引中ではありません")
    transaction_evidence = TransactionEvidences.query.get(transaction_evidence.id).with_for_update()
    if transaction_evidence is None:
        raise TransactionEvidencesNotFound()
    if transaction_evidence.status != TransactionEvidenceStatus.wait_shipping:
        raise HttpException(codes.forbidden, "準備ができていません")

    shipping = Shipping.query.filter(transaction_evidence_id=transaction_evidence.id).one_or_none().with_for_update()
    if shipping is None:
        raise ShippingNotFound()

    res = http_service.Shipping.request(get_shipment_service_url(), shipping.reserve_id)

    shipping.status = ShippingStatus.wait_pickup
    shipping.img_binary = res.content
    shipping.updated_at = datetime.datetime.now()

    db.session.update(shipping)
    db.session.commit()
    return transaction_evidence.id, shipping.reserve_id


def ship_done(user: User, item_id: int) -> TransactionEvidences:
    transaction_evidence = TransactionEvidences.query.filter(item_id).one_or_none().with_for_update()
    if transaction_evidence is None:
        raise TransactionEvidencesNotFound()
    if transaction_evidence.seller_id != user.id:
        raise HttpException(codes.forbidden, "権限がありません")

    item = Item.query.get(item_id)
    if item is None:
        raise ItemNotFound()
    if item.status != ItemStatus.trading:
        raise HttpException(codes.forbidden, "商品が取引中ではありません")

    if transaction_evidence.status != TransactionEvidenceStatus.wait_shipping:
        raise HttpException(codes.forbidden, "準備ができていません")

    shipping = Shipping.query.filter(transaction_evidence_id=transaction_evidence.id).one_or_none().with_for_update()
    if shipping is None:
        raise ShippingNotFound()

    ssr = http_service.Shipping.status(get_shipment_service_url(), {"reserve_id": shipping["reserve_id"]})
    if ssr["status"] not in [str(s) for s in (ShippingStatus.done, ShippingStatus.shipping)]:
        raise HttpException(codes.forbidden, "shipment service側で配送中か配送完了になっていません")

    now = datetime.datetime.now()
    shipping.status = ShippingStatus[Shipping[ssr["status"]]]
    shipping.updated_at = now
    db.session.update(shipping)

    transaction_evidence.status = TransactionEvidenceStatus.wait_done
    transaction_evidence.updated_at = now
    db.session.update(transaction_evidence)

    db.session.commit()
    return transaction_evidence


def complete(user: User, item_id: int) -> TransactionEvidences:
    transaction_evidence = TransactionEvidences.query.filter(item_id=item_id).one_or_none().with_for_update()
    if transaction_evidence is None:
        raise TransactionEvidencesNotFound()
    if transaction_evidence.buyer_id != user.id:
        raise HttpException(codes.forbidden, "権限がありません")

    item = Item.query.get(item_id).with_for_update()
    if item is None:
        raise ItemNotFound()
    if item.status != ItemStatus.trading:
        raise HttpException(codes.forbidden, "商品が取引中ではありません")

    if transaction_evidence.status != TransactionEvidenceStatus.wait_done:
        raise HttpException(codes.forbidden, "準備ができていません")

    shipping = Shipping.query.filter(transaction_evidence_id=transaction_evidence.id).one_or_none().with_for_update()
    if transaction_evidence.buyer_id != user.id:
        raise HttpException(codes.forbidden, "権限がありません")

    ssr = http_service.Shipping.status(get_shipment_service_url(), {"reserve_id": shipping.reserve_id})
    if ssr["status"] != str(ShippingStatus.done):
        raise HttpException(codes.bad_request, "shipment service側で配送完了になっていません")

    shipping.status = ShippingStatus.done
    shipping.updated_at = datetime.datetime.now()
    db.session.update(shipping)

    transaction_evidence.status = TransactionEvidenceStatus.done
    transaction_evidence.updated_at = datetime.datetime.now()
    db.session.update(transaction_evidence)

    item.status = ItemStatus.sold_out
    item.updated_at = datetime.datetime.now()
    db.session.update(item)

    db.session.commit()
    return transaction_evidence


def get_qr_code(seller: User, transaction_evidence_id: int) -> Shipping:
    transaction_evidence = TransactionEvidences.query.get(transaction_evidence_id)
    if transaction_evidence is None:
        raise TransactionEvidencesNotFound()
    if transaction_evidence.seller_id != seller.id:
        raise HttpException(codes.forbidden, "権限がありません")
    shipping = Shipping.query.get(transaction_evidence.id)
    if shipping is None:
        raise ShippingNotFound()
    if shipping.status not in (ShippingStatus.wait_pickup, ShippingStatus.shipping):
        raise HttpException(codes.forbidden, "qrcode not available")
    if len(shipping.img_binary) == 0:
        raise HttpException(codes.internal_server_error, "empty qrcode image")
    return shipping


def bump(user: User, payload) -> Item:
    item = Item.query.get(payload['item_id']).with_for_update()
    if item is None:
        raise ItemNotFound()
    if item.seller_id != user.id:
        raise HttpException(codes.forbidden, "自分の商品以外は編集できません")
    seller = User.query.get(user.id).with_for_update()
    if seller is None:
        raise UserNotFound()

    now = datetime.datetime.now()
    if seller.last_bump + datetime.timedelta(seconds=Constants.BUMP_ALLOW_SECONDS) > now:
        raise HttpException(codes.forbidden, "Bump not allowed")

    item.created_at = now
    item.updated_at = now
    db.session.update(item)

    seller.last_bump = now
    db.session.update(seller)

    db.session.commit()
    return item


def login(payload) -> User:
    user = User.query.filter_by(account_name=payload['account_name']).one_or_none()
    if user is None or \
            not bcrypt.checkpw(payload['password'].encode('utf-8'), user.hashed_password):
        raise HttpException(codes.unauthorized, 'アカウント名かパスワードが間違えています')
    return user


def register(payload) -> User:
    hashed = bcrypt.hashpw(payload['password'].encode('utf-8'), bcrypt.gensalt(10))

    user = User(account_name=payload['account_name'], hashed_password=hashed, address=payload['address'])
    db.session.add(user)
    db.session.commit()
    return user
