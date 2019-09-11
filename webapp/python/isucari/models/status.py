import enum


@enum.unique
class ItemStatus(enum.Enum):
    on_sale = "on_sale"
    trading = 'trading'
    sold_out = 'sold_out'
    stop = 'stop'
    cancel = 'cancel'

    def __str__(self):
        return self.value


@enum.unique
class TransactionEvidenceStatus(enum.Enum):
    wait_shipping = 'wait_shipping'
    wait_done = 'wait_done'
    done = 'done'

    def __str__(self):
        return self.value


@enum.unique
class ShippingStatus(enum.Enum):
    initial = 'initial'
    wait_pickup = 'wait_pickup'
    shipping = 'shipping'
    done = 'done'

    def __str__(self):
        return self.value
