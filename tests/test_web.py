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

    def test_viewport_allows_zoom(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"user-scalable=yes", res.data)

    def test_circuit_diagram_image_present(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"bjt-voltage-divider.svg", res.data)

    def test_form_has_styled_inputs(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'class="form-input"', res.data)

    def test_results_section_has_result_cards(self):
        res = self.client.post("/calculate", data=VALID_FORM)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'result-card', res.data)

    def test_form_has_mode_selector(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'name="mode"', res.data)
        self.assertIn(b"Voltage Divider", res.data)
        self.assertIn(b"Fixed Bias", res.data)
        self.assertIn(b"Emitter Bias", res.data)

    def test_form_has_rb_field(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'name="RB"', res.data)

    def test_post_fixed_bias_returns_results(self):
        data = dict(VALID_FORM, mode="fixed", RB="1000")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"9.514", res.data)  # VCE ≈ 9.514 V
        self.assertIn(b"ACTIVE", res.data)

    def test_post_emitter_bias_returns_results(self):
        data = dict(VALID_FORM, mode="emitter", RB="1000")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"8.705", res.data)  # VCE ≈ 8.705 V
        self.assertIn(b"ACTIVE", res.data)

    def test_post_fixed_bias_missing_rb_shows_error(self):
        data = dict(VALID_FORM, mode="fixed", RB="")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)


if __name__ == "__main__":
    unittest.main()
