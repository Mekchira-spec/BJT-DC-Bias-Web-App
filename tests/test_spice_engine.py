"""Tests for the ngspice adapter (TDD: written before spice_engine.py).

No live simulator is required for these unit tests. One opt-in integration
test runs the real binary when NGSPICE / ngspice is available.
"""

import math
import os
import shutil
import unittest

import spice_engine


OP_RAW = """Title: op fixture
Date: Tue Nov 24 00:00:00 2026
Command: ngspice-47
Plotname: Operating Point
Flags: real
No. Variables: 5
No. Points: 1
Variables:
\t0\tv(vcc)\tvoltage
\t1\tv(b)\tvoltage
\t2\tv(c)\tvoltage
\t3\tv(e)\tvoltage
\t4\ti(vcc)\tcurrent
Values:
0\t\t1.200000000000000e+01
\t1.954003507907189e+00
\t9.438841283751714e+00
\t1.175804667053703e+00
\t-1.264623017761059e-03
"""

AC_RAW = """Title: ac fixture
Command: ngspice-47
Plotname: AC Analysis
Flags: complex
No. Variables: 3
No. Points: 3
Variables:
\t0\tfrequency\tfrequency
\t1\tv(in)\tvoltage
\t2\tv(out)\tvoltage
Values:
0\t\t1.000000000000000e+00,0.000000000000000e+00
\t1.000000000000000e-02,0.000000000000000e+00
\t1.000000000000000e-01,0.000000000000000e+00
1\t\t1.000000000000000e+03,0.000000000000000e+00
\t1.000000000000000e-02,0.000000000000000e+00
\t-1.000000000000000e+00,0.000000000000000e+00
2\t\t1.000000000000000e+04,0.000000000000000e+00
\t1.000000000000000e-02,0.000000000000000e+00
\t-5.000000000000000e-01,0.000000000000000e+00
"""

TRAN_RAW = """Title: tran fixture
Command: ngspice-47
Plotname: Transient Analysis
Flags: real
No. Variables: 3
No. Points: 4
Variables:
\t0\ttime\ttime
\t1\tv(in)\tvoltage
\t2\tv(out)\tvoltage
Values:
0\t\t0.000000000000000e+00
\t0.000000000000000e+00
\t0.000000000000000e+00
1\t\t2.500000000000000e-04
\t1.000000000000000e-02
\t-2.000000000000000e-01
2\t\t7.500000000000000e-04
\t-1.000000000000000e-02
\t2.000000000000000e-01
3\t\t1.250000000000000e-03
\t1.000000000000000e-02
\t-2.000000000000000e-01
"""


def params(**overrides):
    base = dict(
        vcc=12.0,
        r1=100_000.0,
        r2=22_000.0,
        rc=2_200.0,
        re=1_000.0,
        rl=10_000.0,
        cin=10e-6,
        cout=10e-6,
        source_amp=0.010,
        source_freq=1_000.0,
        ac_fmin=1.0,
        ac_fmax=10e6,
        ac_points=20,
        tran_stop=3e-3,
        tran_step=2e-6,
        bjt_model="QNPN",
    )
    base.update(overrides)
    return spice_engine.SimulationParams(**base)


class TestNetlist(unittest.TestCase):
    def test_dc_netlist_has_required_elements(self):
        net = spice_engine.build_netlist("dc", params())
        self.assertIn(".op", net)
        self.assertIn("VCC vcc 0 DC 12", net)
        self.assertIn("R1 vcc b 100k", net)
        self.assertIn("RC vcc c 2.2k", net)
        self.assertIn("Q1 c b e QNPN", net)
        self.assertIn("Cin in b 10u", net)
        self.assertIn("Cout c out 10u", net)
        self.assertIn("RL out 0 10k", net)
        self.assertTrue(net.rstrip().endswith(".end"))

    def test_ac_netlist_uses_ac_source_and_decade_sweep(self):
        net = spice_engine.build_netlist("ac", params())
        self.assertIn("AC 10m", net)
        self.assertIn(".ac dec 20 1 10meg", net)
        self.assertNotIn(".tran", net)

    def test_tran_netlist_uses_sin_and_positive_tstep(self):
        net = spice_engine.build_netlist("tran", params())
        self.assertIn("SIN(0 10m 1k", net)
        self.assertIn(".tran 2u 3m 0 2u", net)
        self.assertNotIn(".ac", net)

    def test_changed_values_change_netlist(self):
        net = spice_engine.build_netlist("dc", params(re=4_700.0, rl=1_000.0))
        self.assertIn("RE e 0 4.7k", net)
        self.assertIn("RL out 0 1k", net)

    def test_unknown_analysis_rejected(self):
        with self.assertRaises(spice_engine.SpiceError):
            spice_engine.build_netlist("foo", params())

    def test_injection_string_rejected(self):
        with self.assertRaises(spice_engine.SpiceError):
            params(source_freq="1k\n.end\n* injected")

    def test_nonpositive_rejected(self):
        with self.assertRaises(spice_engine.SpiceError):
            params(rc=0.0)
        with self.assertRaises(spice_engine.SpiceError):
            params(vcc=-12.0)

    def test_nan_and_inf_rejected(self):
        with self.assertRaises(spice_engine.SpiceError):
            params(cin=math.nan)
        with self.assertRaises(spice_engine.SpiceError):
            params(rl=math.inf)

    def test_frequency_range_rejected(self):
        with self.assertRaises(spice_engine.SpiceError):
            params(ac_fmin=10e6, ac_fmax=1.0)


class TestRawParsing(unittest.TestCase):
    def test_parse_op(self):
        data = spice_engine.parse_raw(OP_RAW)
        self.assertEqual(data["analysis"], "dc")
        self.assertAlmostEqual(data["v(b)"][0], 1.9540035, places=5)
        self.assertAlmostEqual(data["v(c)"][0], 9.4388412, places=5)
        self.assertEqual(len(data["v(b)"]), 1)

    def test_parse_ac_complex_pairs(self):
        data = spice_engine.parse_raw(AC_RAW)
        self.assertEqual(data["analysis"], "ac")
        self.assertEqual(data["frequency"], [1.0, 1000.0, 10000.0])
        self.assertAlmostEqual(data["v(out)"][1], -1.0)
        self.assertTrue(all(isinstance(x, complex) for x in data["v(out)"]))

    def test_parse_tran(self):
        data = spice_engine.parse_raw(TRAN_RAW)
        self.assertEqual(data["analysis"], "tran")
        self.assertEqual(data["time"][-1], 1.25e-3)
        self.assertAlmostEqual(data["v(out)"][1], -0.2)

    def test_parse_empty_raises(self):
        with self.assertRaises(spice_engine.SpiceError):
            spice_engine.parse_raw("")

    def test_parse_missing_values_raises(self):
        with self.assertRaises(spice_engine.SpiceError):
            spice_engine.parse_raw("Title: broken\nFlags: real\n")

    def test_op_to_dc_result_uses_voltage_drops(self):
        data = spice_engine.parse_raw(OP_RAW)
        dc = spice_engine.op_to_dc(data, params())
        self.assertAlmostEqual(dc["vce"], 9.4388412 - 1.1758046, places=4)
        self.assertAlmostEqual(dc["ic"] * 1000, 1.1642, places=3)
        self.assertAlmostEqual(dc["ie"] * 1000, 1.1758, places=3)
        self.assertAlmostEqual(dc["ib"] * 1e6, 11.6, places=0)
        self.assertEqual(dc["region"], "ACTIVE")


class TestAnalysisHelpers(unittest.TestCase):
    def test_ac_gain_phase_and_bandwidth(self):
        import cmath

        freqs = [1.0, 10.0, 100.0, 1000.0, 10000.0, 100000.0]
        vin = [0.01 * cmath.exp(0j) for _ in freqs]
        # gain 10x mid-band, roll off at both ends.
        gains = [1.0, 7.0, 10.0, 10.0, 7.0, 1.0]
        vout = [0.01 * g * cmath.exp(math.pi * 1j) for g in gains]
        result = spice_engine.analyze_ac(freqs, vin, vout)
        self.assertAlmostEqual(result["peak_gain"], 10.0, places=5)
        self.assertAlmostEqual(result["peak_gain_db"], 20.0, places=4)
        self.assertTrue(math.isclose(result["phase_deg"][0], -180.0, abs_tol=1e-6))
        self.assertGreater(result["f_low"], 10.0)
        self.assertLess(result["f_high"], 100000.0)

    def test_ac_bandwidth_not_determined_message(self):
        import cmath

        freqs = [1.0, 10.0]
        vin = [0.01 + 0j, 0.01 + 0j]
        vout = [0.01 + 0j, 0.01 + 0j]
        result = spice_engine.analyze_ac(freqs, vin, vout)
        self.assertEqual(result["f_low"], None)
        self.assertEqual(result["f_high"], None)
        self.assertIn("not determined in sweep range", result["bandwidth_note"])

    def test_tran_inversion_and_vpp(self):
        t = [0.0, 0.25e-3, 0.75e-3, 1.25e-3]
        vin = [0.0, 0.01, -0.01, 0.01]
        vout = [0.0, -0.2, 0.2, -0.2]
        result = spice_engine.analyze_tran(t, vin, vout)
        self.assertAlmostEqual(result["vpp_in"], 0.02, places=6)
        self.assertAlmostEqual(result["vpp_out"], 0.4, places=6)
        self.assertTrue(result["inverted"])

    def test_downsample_keeps_first_and_last(self):
        pts = list(range(1000))
        sampled = spice_engine.downsample(pts, 10)
        self.assertEqual(sampled[0], 0)
        self.assertEqual(sampled[-1], 999)
        self.assertLessEqual(len(sampled), 10)


class TestDiscoveryAndErrors(unittest.TestCase):
    def test_find_ngspice_from_env(self):
        old = os.environ.get("NGSPICE")
        os.environ["NGSPICE"] = r"C:\fake\ngspice.exe"
        try:
            self.assertEqual(spice_engine.find_ngspice(), r"C:\fake\ngspice.exe")
        finally:
            if old is None:
                os.environ.pop("NGSPICE", None)
            else:
                os.environ["NGSPICE"] = old

    def test_missing_binary_raises_spice_error(self):
        with self.assertRaises(spice_engine.SpiceError) as ctx:
            spice_engine.run("dc", params(), ngspice_path=r"C:\no\such\ngspice.exe")
        self.assertIn("ไม่พบ", str(ctx.exception))

    @unittest.skipUnless(
        bool(os.environ.get("NGSPICE") or shutil.which("ngspice")),
        "ngspice binary not available",
    )
    def test_real_ngspice_dc_op(self):
        result = spice_engine.run("dc", params())
        self.assertEqual(result.source, "SPICE")
        self.assertGreater(result.values["v(c)"][0], 0.0)
        self.assertIn("ngspice", result.version.lower())


if __name__ == "__main__":
    unittest.main()
