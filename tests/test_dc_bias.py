"""Unit tests for the DC bias engineering core (no Flask, no HTTP)."""

import unittest

from dc_bias import ValidationError, calculate, to_ohms, calculate_fixed_bias, calculate_emitter_bias


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


class TestFixedBias(unittest.TestCase):
    """Fixed Bias: VCC=12, RC=2.2k, RB=1M, beta=100, VBE=0.70.

    IB = (VCC - VBE) / RB = 11.3 / 1e6 = 11.3 µA
    IC = β·IB = 1.13 mA
    VE = 0, VB = VBE = 0.70 V
    VC = VCC - IC·RC = 12 - 1.13m·2200 = 9.514 V
    VCE = VC - VE = 9.514 V
    """

    def test_fixed_basic_values(self):
        r = calculate_fixed_bias(
            vcc=12.0,
            rc=2_200.0,
            beta=100.0,
            vbe=0.70,
            rb=1_000_000.0,
        )
        self.assertAlmostEqual(r.ib, 11.3e-6, places=10)
        self.assertAlmostEqual(r.ic, 1.13e-3, places=10)
        self.assertAlmostEqual(r.ie, 1.1413e-3, places=10)
        self.assertAlmostEqual(r.ve, 0.0, places=10)
        self.assertAlmostEqual(r.vb, 0.70, places=10)
        self.assertAlmostEqual(r.vc, 9.514, places=6)
        self.assertAlmostEqual(r.vce, 9.514, places=6)
        self.assertEqual(r.mode, "fixed")
        self.assertEqual(r.region, "ACTIVE")

    def test_fixed_rb_zero_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_fixed_bias(12.0, 2_200.0, 100.0, 0.70, 0.0)
        self.assertIn("rb", ctx.exception.errors)


class TestEmitterBias(unittest.TestCase):
    """Emitter Bias: VCC=12, RC=2.2k, RB=1M, RE=1k, beta=100, VBE=0.70.

    IB = (VCC - VBE) / (RB + (β+1)·RE) = 11.3 / 1,101,000 ≈ 10.2634 µA
    IC = β·IB ≈ 1.02634 mA
    IE = (β+1)·IB ≈ 1.03660 mA
    VE = IE·RE ≈ 1.03660 V
    VB = VE + VBE ≈ 1.73660 V
    VC = VCC - IC·RC ≈ 9.74205 V
    VCE = VC - VE ≈ 8.70545 V
    """

    def test_emitter_basic_values(self):
        r = calculate_emitter_bias(
            vcc=12.0,
            rc=2_200.0,
            beta=100.0,
            vbe=0.70,
            rb=1_000_000.0,
            re=1_000.0,
        )
        self.assertAlmostEqual(r.ib, 11.3 / 1_101_000, places=10)
        self.assertAlmostEqual(r.ic, 100.0 * 11.3 / 1_101_000, places=10)
        self.assertAlmostEqual(r.ve, 101.0 * 11.3 / 1_101_000 * 1_000, places=6)
        self.assertAlmostEqual(r.vb, r.ve + 0.70, places=6)
        self.assertAlmostEqual(r.vc, 12.0 - 100.0 * 11.3 / 1_101_000 * 2_200, places=6)
        self.assertAlmostEqual(r.vce, r.vc - r.ve, places=6)
        self.assertEqual(r.mode, "emitter")
        self.assertEqual(r.region, "ACTIVE")

    def test_emitter_rb_zero_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_emitter_bias(12.0, 2_200.0, 100.0, 0.70, 0.0, 1_000.0)
        self.assertIn("rb", ctx.exception.errors)

    def test_emitter_re_zero_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_emitter_bias(12.0, 2_200.0, 100.0, 0.70, 1_000_000.0, 0.0)
        self.assertIn("re", ctx.exception.errors)


if __name__ == "__main__":
    unittest.main()
