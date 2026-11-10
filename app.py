"""Flask routes for the BJT DC bias web app.

This module only parses the HTTP form, calls the engineering module and
renders a template. All circuit equations live in ``dc_bias.py``.
"""

import math

from flask import Flask, render_template, request

from dc_bias import ValidationError, calculate, to_ohms

app = Flask(__name__)

FIELDS = ("VCC", "R1", "R2", "RC", "RE", "beta", "VBE")
RESISTOR_FIELDS = ("R1", "R2", "RC", "RE")
UNITS = ("kohm", "ohm")

# Field names used by the engineering module -> names used by the HTML form.
DOMAIN_TO_FORM = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "beta": "beta",
    "vbe": "VBE",
}

DEFAULTS = {
    "VCC": "12",
    "R1": "100",
    "R2": "22",
    "RC": "2.2",
    "RE": "1",
    "beta": "100",
    "VBE": "0.70",
}

NUMERIC_ERROR = "กรุณากรอกตัวเลข"


def parse_form(form) -> tuple[dict[str, float], dict[str, str], str]:
    """Return (values in SI units, field errors, resistance unit)."""
    values: dict[str, float] = {}
    errors: dict[str, str] = {}

    for field in FIELDS:
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

    return values, errors, unit


def submitted_form(form) -> dict[str, str]:
    """Keep what the user typed so the form can be re-rendered with errors."""
    return {field: (form.get(field) or "") for field in FIELDS}


@app.route("/")
def index():
    return render_template(
        "index.html",
        form=DEFAULTS,
        unit="kohm",
        result=None,
        errors={},
    )


@app.route("/calculate", methods=["POST"])
def calculate_route():
    values, errors, unit = parse_form(request.form)
    form = submitted_form(request.form)

    if errors:
        return render_template(
            "index.html", form=form, unit=unit, result=None, errors=errors
        )

    try:
        result = calculate(**{name.lower(): value for name, value in values.items()})
    except ValidationError as exc:
        field_errors = {
            DOMAIN_TO_FORM.get(name, name): message
            for name, message in exc.errors.items()
        }
        return render_template(
            "index.html", form=form, unit=unit, result=None, errors=field_errors
        )

    return render_template(
        "index.html", form=form, unit=unit, result=result, errors={}
    )


if __name__ == "__main__":
    app.run(debug=True)
