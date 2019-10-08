# -*- coding: utf-8 -*-

import string
import random


def random_string(length):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))


def get_image_url(image_name):
    return "/upload/{}".format(image_name)