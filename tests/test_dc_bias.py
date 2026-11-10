"""Unit tests for the DC bias engineering core (no Flask, no HTTP)."""

import unittest

from dc_bias import ValidationError, calculate, to_ohms


class TestReferenceOperatingPoint(unittest.TestCase):
    """Lab reference set: VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, beta=100, VBE=0.70."""

    def test_lab_reference_values(self):
        r = calculate(
            vcc=12.0,
            r1=100_000.0,
            r2=22_000.0,
            rc=2_200.0,
            re=1_000.0,
            beta=100.0,
            vbe=0.70,
        )
        self.assertAlmostEqual(r.vth, 2.163934426, places=6)
        self.assertAlmostEqual(r.rth, 18032.7868852, places=5)
        self.assertAlmostEqual(r.ib, 12.298581462608456e-6, places=12)
        self.assertAlmostEqual(r.ic, 1.2298581462608456e-3, places=12)
        self.assertAlmostEqual(r.ie, 1.242156727723454e-3, places=12)
        self.assertAlmostEqual(r.ve, 1.2421567277, places=6)
        self.assertAlmostEqual(r.vb, 1.9421567277, places=6)
        self.assertAlmostEqual(r.vc, 9.2943120782, places=6)
        self.assertAlmostEqual(r.vce, 8.0521553505, places=6)
        self.assertEqual(r.region, "ACTIVE")


class TestUnitConversion(unittest.TestCase):
    def test_kohm_with_decimal(self):
        self.assertAlmostEqual(to_ohms(2.2, "kohm"), 2200.0)

    def test_ohm_passthrough(self):
        self.assertAlmostEqual(to_ohms(2200.0, "ohm"), 2200.0)


class TestValidation(unittest.TestCase):
    def test_rejects_zero_resistor(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate(12.0, 0.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertIn("r1", ctx.exception.errors)

    def test_rejects_nonpositive_beta(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 0.0, 0.70)
        self.assertIn("beta", ctx.exception.errors)

    def test_rejects_negative_vcc(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate(-1.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertIn("vcc", ctx.exception.errors)

    def test_rejects_vbe_at_or_above_vcc(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 12.0)
        self.assertIn("vbe", ctx.exception.errors)


class TestRegions(unittest.TestCase):
    def test_cutoff_when_vth_below_vbe(self):
        # R2 small -> VTH below VBE
        r = calculate(12.0, 100_000.0, 1_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(r.region, "CUTOFF")
        self.assertEqual(r.ic, 0.0)
        self.assertEqual(r.vc, 12.0)
        self.assertTrue(r.warnings)

    def test_saturation_when_vce_below_threshold(self):
        # RC very large -> VCE goes negative
        r = calculate(12.0, 100_000.0, 22_000.0, 100_000.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(r.region, "SATURATION")
        self.assertLess(r.vce, 0.30)
        self.assertTrue(r.warnings)

    def test_active_has_no_warnings(self):
        r = calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(r.warnings, [])


if __name__ == "__main__":
    unittest.main()
