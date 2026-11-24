"""HTTP-level tests for the Flask routes (test client, no live server)."""

import unittest

import spice_engine
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


SPICE_FORM = dict(
    VALID_FORM,
    RL="10",
    Cin="10",
    Cout="10",
    source_amp="10",
    source_freq="1",
    ac_fmin="1",
    ac_fmax="10",
    tran_stop="3",
)


@unittest.skipUnless(spice_engine.find_ngspice(), "ngspice binary not available")
class TestWebSpice(unittest.TestCase):
    """Browser-facing routes; every assertion comes from a real batch run."""

    def setUp(self):
        self.client = app.test_client()

    def test_index_has_analysis_selector(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'name="analysis"', res.data)
        self.assertIn(b"Transient", res.data)

    def test_index_has_spice_source_fields(self):
        res = self.client.get("/")
        for field in (b'name="RL"', b'name="Cin"', b'name="source_amp"', b'name="source_freq"'):
            self.assertIn(field, res.data)

    def test_spice_dc_returns_real_operating_point(self):
        res = self.client.post("/calculate", data=dict(SPICE_FORM, analysis="dc"))
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"SPICE", res.data)
        self.assertIn(b"8.2", res.data)  # VCE from ngspice, not the analytical 8.052 V
        self.assertNotIn(b"8.052", res.data)

    def test_spice_dc_changes_when_re_changes(self):
        baseline = self.client.post("/calculate", data=dict(SPICE_FORM, analysis="dc")).data
        changed = self.client.post("/calculate", data=dict(SPICE_FORM, analysis="dc", RE="2")).data
        self.assertNotEqual(baseline, changed)
        self.assertIn(b"SPICE", changed)

    def test_spice_ac_returns_bode_graph(self):
        res = self.client.post("/calculate", data=dict(SPICE_FORM, analysis="ac"))
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Bode", res.data)
        self.assertIn(b"<svg", res.data)
        self.assertIn(b"gain", res.data.lower())

    def test_spice_tran_returns_waveform_graph(self):
        res = self.client.post("/calculate", data=dict(SPICE_FORM, analysis="tran"))
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Transient", res.data)
        self.assertIn(b"<svg", res.data)
        self.assertIn(b"Vin", res.data)
        self.assertIn(b"Vout", res.data)

    def test_spice_invalid_input_shows_error_without_success_badge(self):
        res = self.client.post(
            "/calculate", data=dict(SPICE_FORM, analysis="dc", source_freq="abc")
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)
        self.assertNotIn(b"badge-success", res.data)

    def test_spice_bad_analysis_shows_error(self):
        res = self.client.post("/calculate", data=dict(SPICE_FORM, analysis="foo"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("analysis".encode(), res.data)


if __name__ == "__main__":
    unittest.main()
