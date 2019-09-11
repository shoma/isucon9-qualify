from datetime import datetime

from ..database import db
from .status import *


class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.BigInteger, primary_key=True)
    account_name = db.Column(db.String, unique=True, nullable=False)
    hashed_password = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    num_sell_items = db.Column(db.Integer, nullable=False, default=0)
    last_bump = db.Column(db.DateTime, nullable=False, default=datetime.now)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def for_json(self):
        return {
            "id": self.id,
            "account_name": self.account_name,
            "address": self.address,
            "num_sell_items": self.num_sell_items,
        }

    def for_simple_json(self):
        return {
            "id": self.id,
            "account_name": self.account_name,
            "num_sell_items": self.num_sell_items,
        }


class Item(db.Model):
    __tablename__ = 'items'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.BigInteger, primary_key=True)
    seller_id = db.Column(db.BigInteger, nullable=False)
    buyer_id = db.Column(db.BigInteger, nullable=False)
    status = db.Column(db.Enum(ItemStatus), nullable=False, default=ItemStatus.on_sale)
    name = db.Column(db.String(length=191), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.UnicodeText, nullable=False)
    image_name = db.Column(db.String(length=191), nullable=False)
    category_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    category = None
    image_url = None
    seller = None
    buyer = None
    transaction_evidence_id = None
    transaction_evidence_status = None
    shipping_status = None

    def for_json(self):
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "buyer_id": self.buyer_id,
            "status": self.status.value,
            "name": self.name,
            "price": self.price,
            "description": self.description,
            "image_name": self.image_name,
            "category_id": self.category_id,
        }

    def for_simple_json(self):
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "seller": self.seller,
            "status": self.status.value,
            "name": self.name,
            "price": self.price,
            "image_url": self.image_url,
            "category_id": self.category_id,
            "category": self.category,
            "created_at": int(self.created_at.timestamp()),
        }

    def for_detail_json(self):
        rtn = {
            "id": self.id,
            "seller_id": self.seller_id,
            "seller": self.seller,
            "status": self.status.value,
            "name": self.name,
            "price": self.price,
            "description": self.description,
            "image_name": self.image_name,
            "category_id": self.category_id,
            "category": self.category,
            "created_at": int(self.created_at.timestamp()),
        }
        extra = {
            "buyer_id": self.buyer_id,
            "buyer": self.buyer,
            "transaction_evidence_id": self.transaction_evidence_id,
        }
        rtn.update({k: v for k, v in extra.items() if v is not None})
        if self.transaction_evidence_status is not None:
            rtn["transaction_evidence_status"] = self.transaction_evidence_status.value
        if self.shipping_status is not None:
            rtn["shipping_status"] = self.shipping_status.value
        return rtn


class Category(db.Model):
    __tablename__ = 'categories'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, nullable=False)
    category_name = db.Column(db.String(length=191), nullable=False)
    parent_category_name = None

    def for_json(self):
        rtn = dict(
            id=self.id,
            parent_id=self.parent_id,
            category_name=self.category_name,
        )
        if self.parent_category_name is not None:
            rtn['parent_category_name'] = self.parent_category_name
        return rtn


class Config(db.Model):
    __tablename__ = 'configs'
    __table_args__ = {'extend_existing': True}

    name = db.Column(db.String(length=191), primary_key=True)
    val = db.Column(db.String(length=255), nullable=False)


class Shipping(db.Model):
    __tablename__ = 'shippings'
    __table_args__ = {'extend_existing': True}

    transaction_evidence_id = db.Column(db.BigInteger, primary_key=True)
    status = db.Column(db.Enum(ShippingStatus), nullable=False, default=ShippingStatus.initial)
    item_name = db.Column(db.String(length=191), nullable=False)
    item_id = db.Column(db.BigInteger, nullable=False)
    reserve_id = db.Column(db.String(length=191), primary_key=True)
    reserve_time = db.Column(db.BigInteger, nullable=False)
    to_address = db.Column(db.String(length=191), nullable=False)
    to_name = db.Column(db.String(length=191), nullable=False)
    from_address = db.Column(db.String(length=191), nullable=False)
    from_name = db.Column(db.String(length=191), nullable=False)
    img_binary = db.Column(db.BLOB, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


class TransactionEvidences(db.Model):
    __tablename__ = 'transaction_evidences'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.BigInteger, primary_key=True)
    seller_id = db.Column(db.BigInteger, nullable=False)
    buyer_id = db.Column(db.BigInteger, nullable=False)
    status = db.Column(db.Enum(TransactionEvidenceStatus), nullable=False,
                       default=TransactionEvidenceStatus.wait_shipping)
    item_id = db.Column(db.BigInteger, nullable=False, unique=True)
    item_name = db.Column(db.String(length=191), nullable=False)
    item_price = db.Column(db.Integer, nullable=False)
    item_description = db.Column(db.UnicodeText, nullable=False)
    item_category_id = db.Column(db.Integer, nullable=False)
    item_root_category_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def for_json(self):
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "buyer_id": self.buyer_id,
            "status": self.status.value,
            "item_id": self.item_id,
            "item_name": self.item_name,
            "item_price": self.item_price,
            "item_description": self.item_description,
            "item_category_id": self.item_category_id,
            "item_root_category_id": self.item_root_category_id,
        }
