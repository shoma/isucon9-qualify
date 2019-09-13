import unittest

from isucari import utils


class UtilsTestCase(unittest.TestCase):
    def test_random_string(self):
        for i in range(1, 40):
            ret = utils.random_string(i)
            self.assertEqual(len(ret), i)
            self.assertRegex(ret, '[a-z0-9]+')

    def get_image_url(self):
        self.assertEqual(utils.get_image_url('image.png'), '/upload/image.png')
