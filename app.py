"""Flask routes for the BJT DC bias web app and the Lab 4 SPICE simulator.

This module only parses HTTP forms, dispatches to the engineering module or to
``spice_engine``, and renders a template. All circuit equations stay in
``dc_bias.py`` and ``spice_engine.py``. The original analytical routes are kept
unchanged so Lab 3 behaviour is a regression test, not a rewrite.
"""

import math

from flask import Flask, render_template, request

from charts import make_chart
from dc_bias import (
    ValidationError,
    calculate,
    calculate_emitter_bias,
    calculate_fixed_bias,
    to_ohms,
)
from spice_engine import (
    SimulationParams,
    SpiceError,
    analyze_ac,
    analyze_tran,
    downsample,
    op_to_dc,
    run as run_spice,
)

app = Flask(__name__)

FIELDS = ("VCC", "R1", "R2", "RC", "RE", "RB", "beta", "VBE")
SPICE_FIELDS = ("RL", "Cin", "Cout", "source_amp", "source_freq", "ac_fmin", "ac_fmax", "tran_stop")
ALL_FIELDS = FIELDS + SPICE_FIELDS + ("analysis",)
RESISTOR_FIELDS = ("R1", "R2", "RC", "RE", "RB", "RL")
UNITS = ("kohm", "ohm")
MODES = ("divider", "fixed", "emitter")
ANALYSES = ("analytical", "dc", "ac", "tran")

MODE_NAMES = {
    "divider": "Voltage Divider",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

ANALYSIS_NAMES = {
    "analytical": "Analytical (Python)",
    "dc": "DC .op (ngspice)",
    "ac": "AC .ac (ngspice)",
    "tran": "Transient .tran (ngspice)",
}

# Field names used by the engineering module -> names used by the HTML form.
DOMAIN_TO_FORM = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "rb": "RB",
    "beta": "beta",
    "vbe": "VBE",
}

# Fields required by each mode (in form field names).
MODE_REQUIRED_FIELDS = {
    "divider": ("VCC", "R1", "R2", "RC", "RE", "beta", "VBE"),
    "fixed": ("VCC", "RC", "RB", "beta", "VBE"),
    "emitter": ("VCC", "RC", "RB", "RE", "beta", "VBE"),
}

DEFAULTS = {
    "VCC": "12",
    "R1": "100",
    "R2": "22",
    "RC": "2.2",
    "RE": "1",
    "RB": "1000",
    "beta": "100",
    "VBE": "0.70",
    "mode": "divider",
    "RL": "10",
    "Cin": "10",
    "Cout": "10",
    "source_amp": "10",
    "source_freq": "1",
    "ac_fmin": "1",
    "ac_fmax": "10",
    "tran_stop": "3",
    "analysis": "analytical",
}

NUMERIC_ERROR = "กรุณากรอกตัวเลข"


def _render(
    form,
    unit,
    mode,
    analysis="analytical",
    result=None,
    sim=None,
    errors=None,
    spice_error=None,
):
    """Single rendering path so every route supplies the same context."""
    return render_template(
        "index.html",
        form=form,
        unit=unit,
        mode=mode,
        analysis=analysis,
        mode_names=MODE_NAMES,
        analysis_names=ANALYSIS_NAMES,
        result=result,
        sim=sim,
        errors=errors or {},
        spice_error=spice_error,
    )


def parse_form(form) -> tuple[dict[str, float], dict[str, str], str, str]:
    """Return (values in SI units, field errors, resistance unit, mode).

    Only fields required by the selected mode are validated.  Other fields
    may be empty or invalid without causing an error.
    """
    values: dict[str, float] = {}
    errors: dict[str, str] = {}

    mode = form.get("mode") or "divider"
    if mode not in MODES:
        mode = "divider"

    required = MODE_REQUIRED_FIELDS[mode]

    for field in FIELDS:
        # Skip fields not required by this mode.
        if field not in required:
            continue

        text = (form.get(field) or "").strip()
        if not text:
            errors[field] = NUMERIC_ERROR
            continue
        try:
            value = float(text)
        except ValueError:
            errors[field] = NUMERIC_ERROR
            continue
        if not math.isfinite(value):
            errors[field] = NUMERIC_ERROR
            continue
        values[field] = value

    unit = form.get("unit") or "kohm"
    if unit not in UNITS:
        unit = "kohm"

    for field in RESISTOR_FIELDS:
        if field in values:
            values[field] = to_ohms(values[field], unit)

    return values, errors, unit, mode


def parse_sim_form(form) -> tuple[SimulationParams | None, dict[str, str]]:
    """Read the SPICE form into validated SI ``SimulationParams``.

    Form units: resistors follow the selected kΩ/Ω selector, capacitors µF,
    source amplitude mV, source frequency kHz, AC sweep 1 Hz–MHz, and
    transient stop time ms.
    """
    errors: dict[str, str] = {}
    unit = form.get("unit") or "kohm"
    if unit not in UNITS:
        unit = "kohm"

    def read(field: str, scale: float = 1.0) -> float | None:
        text = (form.get(field) or "").strip()
        if not text:
            errors[field] = NUMERIC_ERROR
            return None
        try:
            value = float(text)
        except ValueError:
            errors[field] = NUMERIC_ERROR
            return None
        if not math.isfinite(value):
            errors[field] = NUMERIC_ERROR
            return None
        return value * scale

    resistance_scale = 1000.0 if unit == "kohm" else 1.0
    vcc = read("VCC")
    r1 = read("R1", resistance_scale)
    r2 = read("R2", resistance_scale)
    rc = read("RC", resistance_scale)
    re = read("RE", resistance_scale)
    rl = read("RL", resistance_scale)
    beta = read("beta")
    cin = read("Cin", 1e-6)
    cout = read("Cout", 1e-6)
    source_amp = read("source_amp", 1e-3)
    source_freq = read("source_freq", 1e3)
    ac_fmin = read("ac_fmin")
    ac_fmax = read("ac_fmax", 1e6)
    tran_stop_ms = read("tran_stop")
    if errors:
        return None, errors

    tran_stop = tran_stop_ms * 1e-3
    try:
        params = SimulationParams(
            vcc=vcc,
            r1=r1,
            r2=r2,
            rc=rc,
            re=re,
            rl=rl,
            cin=cin,
            cout=cout,
            source_amp=source_amp,
            source_freq=source_freq,
            ac_fmin=ac_fmin,
            ac_fmax=ac_fmax,
            ac_points=20,
            tran_stop=tran_stop,
            tran_step=tran_stop / 1500.0,
            bjt_model="QNPN",
            beta=beta,
        )
    except SpiceError as exc:
        errors["analysis"] = str(exc)
        return None, errors
    return params, {}


def submitted_form(form) -> dict[str, str]:
    """Keep what the user typed so the form can be re-rendered with errors."""
    return {field: (form.get(field) or "") for field in ALL_FIELDS}


def _eng(value: float, unit: str) -> str:
    """Compact engineering notation, e.g. 1.2 MHz or 2 ms."""
    if value == 0:
        return f"0 {unit}"
    for suffix, scale in (("M", 1e6), ("k", 1e3), ("", 1.0), ("m", 1e-3), ("u", 1e-6)):
        if abs(value) >= scale:
            return f"{value / scale:.3g} {suffix}{unit}"
    return f"{value:.3g} {unit}"


def _sampled_indices(length: int, limit: int) -> list[int]:
    return downsample(list(range(length)), limit)


def _build_sim(analysis: str, result, params: SimulationParams) -> dict:
    """Turn parsed simulator arrays into template-ready stats and charts."""
    values = result.values
    sim: dict = {
        "kind": analysis,
        "label": ANALYSIS_NAMES[analysis],
        "source": result.source,
        "version": result.version,
        "points": result.meta["npoints"],
        "netlist": result.netlist,
        "log_tail": result.log_tail,
        "stats": [],
        "charts": [],
        "note": "",
        "warnings": list(result.warnings),
    }

    if analysis == "dc":
        dc = op_to_dc(values, params)
        sim["badge"] = dc["region"]
        sim["stats"] = [
            ("VB", f"{dc['vb']:.3f} V"),
            ("VE", f"{dc['ve']:.3f} V"),
            ("VC", f"{dc['vc']:.3f} V"),
            ("VCE", f"{dc['vce']:.3f} V"),
            ("IC", f"{dc['ic'] * 1e3:.3f} mA"),
            ("IE", f"{dc['ie'] * 1e3:.3f} mA"),
            ("IB", f"{dc['ib'] * 1e6:.2f} µA"),
        ]
        sim["note"] = "ค่าอ่านจาก ngspice .op — IC มาจากแรงดันตกบน RC, IE จาก RE"

    elif analysis == "ac":
        ac = analyze_ac(values["frequency"], values["v(in)"], values["v(out)"])
        indices = _sampled_indices(len(ac["frequency"]), 240)
        sample = lambda array: [array[index] for index in indices]  # noqa: E731
        freqs = sample(ac["frequency"])
        sim["badge"] = "AC SWEEP"
        sim["stats"] = [
            ("Gain สูงสุด", f"{ac['peak_gain']:.2f} V/V ({ac['peak_gain_db']:.1f} dB)"),
            ("fL (-3 dB)", _eng(ac["f_low"], "Hz") if ac["f_low"] else "not determined"),
            ("fH (-3 dB)", _eng(ac["f_high"], "Hz") if ac["f_high"] else "not determined"),
            ("จุด sweep", f"{ac['frequency'][0]:.3g}–{ac['frequency'][-1]:.3g} Hz"),
        ]
        sim["note"] = ac["bandwidth_note"]
        sim["charts"] = [
            make_chart(
                "Bode magnitude — |Vout/Vin|",
                "Frequency (Hz)",
                "Gain (dB)",
                [{"name": "|Vout/Vin|", "color": "#2563eb", "x": freqs, "y": sample(ac["gain_db"])}],
                logx=True,
            ),
            make_chart(
                "Bode phase — Vout เทียบ Vin",
                "Frequency (Hz)",
                "Phase (deg)",
                [{"name": "phase", "color": "#dc2626", "x": freqs, "y": sample(ac["phase_deg"])}],
                logx=True,
            ),
        ]

    else:  # tran
        tr = analyze_tran(values["time"], values["v(in)"], values["v(out)"])
        indices = _sampled_indices(len(tr["time"]), 240)
        sample = lambda array: [array[index] for index in indices]  # noqa: E731
        times = [value * 1e3 for value in sample(tr["time"])]
        sim["badge"] = "TRANSIENT"
        sim["stats"] = [
            ("Vin (Vpp)", f"{tr['vpp_in'] * 1e3:.1f} mV"),
            ("Vout (Vpp)", f"{tr['vpp_out']:.3f} V"),
            ("Gain Vpp", f"{tr['vpp_out'] / tr['vpp_in']:.2f} V/V" if tr["vpp_in"] else "n/a"),
            ("เฟสโดยประมาณ", f"{tr['phase_deg_est']:.0f}°"),
        ]
        sim["note"] = (
            "สัญญาณขาออกกลับเฟสตามวงจร Common-Emitter"
            if tr["inverted"]
            else "ไม่พบการกลับเฟส — ตรวจจุดวัด Vin/Vout"
        )
        sim["charts"] = [
            make_chart(
                "Transient — Vin / Vout ตามเวลา",
                "Time (ms)",
                "Voltage (V)",
                [
                    {"name": "Vin", "color": "#2563eb", "x": times, "y": sample(tr["vin"])},
                    {"name": "Vout", "color": "#dc2626", "x": times, "y": sample(tr["vout"])},
                ],
            ),
        ]
    return sim


@app.route("/")
def index():
    return _render(form=DEFAULTS, unit="kohm", mode="divider", analysis="analytical")


def _simulate_route(analysis: str):
    params, errors = parse_sim_form(request.form)
    form = submitted_form(request.form)
    if errors:
        return _render(form=form, unit=request.form.get("unit") or "kohm", mode="divider",
                       analysis=analysis, errors=errors)

    try:
        result = run_spice(analysis, params)
    except SpiceError as exc:
        return _render(
            form=form,
            unit=request.form.get("unit") or "kohm",
            mode="divider",
            analysis=analysis,
            spice_error=str(exc),
        )

    return _render(
        form=form,
        unit=request.form.get("unit") or "kohm",
        mode="divider",
        analysis=analysis,
        sim=_build_sim(analysis, result, params),
    )


@app.route("/calculate", methods=["POST"])
def calculate_route():
    analysis = request.form.get("analysis") or "analytical"
    if analysis not in ANALYSES:
        form = submitted_form(request.form)
        return _render(
            form=form,
            unit=request.form.get("unit") or "kohm",
            mode="divider",
            analysis="analytical",
            errors={"analysis": "โหมด analysis ไม่ถูกต้อง"},
        )
    if analysis != "analytical":
        return _simulate_route(analysis)

    values, errors, unit, mode = parse_form(request.form)
    form = submitted_form(request.form)

    if errors:
        return _render(form=form, unit=unit, mode=mode, analysis=analysis, errors=errors)

    try:
        if mode == "divider":
            result = calculate(
                vcc=values["VCC"],
                r1=values["R1"],
                r2=values["R2"],
                rc=values["RC"],
                re=values["RE"],
                beta=values["beta"],
                vbe=values["VBE"],
            )
        elif mode == "fixed":
            result = calculate_fixed_bias(
                vcc=values["VCC"],
                rc=values["RC"],
                beta=values["beta"],
                vbe=values["VBE"],
                rb=values["RB"],
            )
        elif mode == "emitter":
            result = calculate_emitter_bias(
                vcc=values["VCC"],
                rc=values["RC"],
                beta=values["beta"],
                vbe=values["VBE"],
                rb=values["RB"],
                re=values["RE"],
            )
        else:  # pragma: no cover
            raise ValidationError({"mode": "โหมดวงจรไม่ถูกต้อง"})
    except ValidationError as exc:
        field_errors = {
            DOMAIN_TO_FORM.get(name, name): message
            for name, message in exc.errors.items()
        }
        return _render(
            form=form, unit=unit, mode=mode, analysis=analysis, errors=field_errors
        )

    return _render(
        form=form, unit=unit, mode=mode, analysis=analysis, result=result
    )


if __name__ == "__main__":
    app.run(debug=True)
