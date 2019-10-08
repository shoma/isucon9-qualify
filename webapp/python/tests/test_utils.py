import re

from isucari import utils


def test_random_string():
    for i in range(1, 40):
        ret = utils.random_string(i)
        assert len(ret) == i
        assert re.match('[a-z0-9]+', ret)


def get_image_url():
    assert '/upload/image.png' == utils.get_image_url('image.png')
