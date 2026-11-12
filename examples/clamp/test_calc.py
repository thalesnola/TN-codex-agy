import unittest
from calc import clamp


class ClampTests(unittest.TestCase):
    def test_below_lower(self):
        self.assertEqual(clamp(-3, 0, 10), 0)

    def test_inside_interval(self):
        self.assertEqual(clamp(4, 0, 10), 4)

    def test_above_upper(self):
        self.assertEqual(clamp(30, 0, 10), 10)

    def test_boundaries(self):
        self.assertEqual(clamp(0, 0, 10), 0)
        self.assertEqual(clamp(10, 0, 10), 10)

    def test_negative_interval(self):
        self.assertEqual(clamp(-5, -10, -2), -5)

    def test_float(self):
        self.assertEqual(clamp(0.5, 0.0, 1.0), 0.5)

    def test_zero_width(self):
        self.assertEqual(clamp(100, 3, 3), 3)

    def test_invalid_interval(self):
        with self.assertRaises(ValueError):
            clamp(5, 10, 0)


if __name__ == '__main__':
    unittest.main()
