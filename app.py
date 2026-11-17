"""Flask routes for the BJT DC bias web app.

This module only parses the HTTP form, calls the engineering module and
renders a template. All circuit equations live in ``dc_bias.py``.
"""

import math

from flask import Flask, render_template, request

from dc_bias import (
    ValidationError,
    calculate,
    calculate_emitter_bias,
    calculate_fixed_bias,
    to_ohms,
)

app = Flask(__name__)

FIELDS = ("VCC", "R1", "R2", "RC", "RE", "RB", "beta", "VBE")
RESISTOR_FIELDS = ("R1", "R2", "RC", "RE", "RB")
UNITS = ("kohm", "ohm")
MODES = ("divider", "fixed", "emitter")

MODE_NAMES = {
    "divider": "Voltage Divider",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
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
}

NUMERIC_ERROR = "กรุณากรอกตัวเลข"


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


def submitted_form(form) -> dict[str, str]:
    """Keep what the user typed so the form can be re-rendered with errors."""
    return {field: (form.get(field) or "") for field in FIELDS}


@app.route("/")
def index():
    return render_template(
        "index.html",
        form=DEFAULTS,
        unit="kohm",
        mode="divider",
        mode_names=MODE_NAMES,
        result=None,
        errors={},
    )


@app.route("/calculate", methods=["POST"])
def calculate_route():
    values, errors, unit, mode = parse_form(request.form)
    form = submitted_form(request.form)

    if errors:
        return render_template(
            "index.html",
            form=form,
            unit=unit,
            mode=mode,
            mode_names=MODE_NAMES,
            result=None,
            errors=errors,
        )

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
        return render_template(
            "index.html",
            form=form,
            unit=unit,
            mode=mode,
            mode_names=MODE_NAMES,
            result=None,
            errors=field_errors,
        )

    return render_template(
        "index.html", form=form, unit=unit, mode=mode, mode_names=MODE_NAMES, result=result, errors={}
    )


if __name__ == "__main__":
    app.run(debug=True)
