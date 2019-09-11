import unittest

from . import isucari


class UtilsTestCase(unittest.TestCase):
    def test_random_string(self):
        for i in range(1, 40):
            ret = isucari.utils.random_string(i)
            self.assertEqual(len(ret), i)
            self.assertRegex(ret, '[a-z0-9]+')

    def get_image_url(self):
        self.assertEqual(isucari.utils.get_image_url('image.png'), '/upload/image.png')


if __name__ == '__main__':
    unittest.main()
