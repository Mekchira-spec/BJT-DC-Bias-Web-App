"""HTTP-level tests for the Flask routes (test client, no live server)."""

import unittest

from app import app

VALID_FORM = {
    "VCC": "12",
    "R1": "100",
    "R2": "22",
    "RC": "2.2",
    "RE": "1",
    "beta": "100",
    "VBE": "0.70",
    "unit": "kohm",
}


class TestWeb(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_index_shows_form(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'name="VCC"', res.data)

    def test_post_calculate_returns_results(self):
        res = self.client.post("/calculate", data=VALID_FORM)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"8.052", res.data)
        self.assertIn(b"ACTIVE", res.data)

    def test_post_invalid_shows_error_not_crash(self):
        data = dict(VALID_FORM, R1="0")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)

    def test_post_missing_field_shows_error(self):
        res = self.client.post("/calculate", data={"VCC": "12", "unit": "kohm"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)

    def test_post_thousands_separator_shows_error(self):
        data = dict(VALID_FORM, R1="1,000")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)

    def test_post_overflow_value_shows_error(self):
        data = dict(VALID_FORM, R1="1e999")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)


if __name__ == "__main__":
    unittest.main()
