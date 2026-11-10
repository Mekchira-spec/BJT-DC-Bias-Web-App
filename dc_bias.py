"""Pure engineering calculations for a BJT common-emitter voltage-divider bias.

This module knows nothing about Flask, HTTP, HTML or forms. It works in SI
units only: volts, amperes and ohms. Presentation (mA, uA, kohm) belongs to
the template layer.

Model: forward-active approximation with constant beta and constant VBE.
Results outside that assumption are reported with an explicit warning; they
are never silently presented as trustworthy.
"""

import math
from dataclasses import dataclass, field

# Collector-emitter voltage below which the transistor is considered to be in
# saturation for this teaching model.
VCE_SAT = 0.30

REGION_ACTIVE = "ACTIVE"
REGION_CUTOFF = "CUTOFF"
REGION_SATURATION = "SATURATION"


class ValidationError(ValueError):
    """Raised when the device values cannot describe a valid circuit.

    ``errors`` maps a form field name to a human readable Thai message.
    """

    def __init__(self, errors: dict[str, str]):
        self.errors = dict(errors)
        super().__init__("; ".join(f"{name}: {msg}" for name, msg in self.errors.items()))


@dataclass(frozen=True)
class BiasResult:
    """DC operating point plus the intermediate values used to obtain it."""

    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: list[str] = field(default_factory=list)


def to_ohms(value: float, unit: str) -> float:
    """Convert a resistance to ohms.

    ``unit`` is ``"kohm"`` or ``"ohm"``.
    """
    if unit == "kohm":
        return value * 1_000.0
    if unit == "ohm":
        return value
    raise ValueError(f"unknown resistance unit: {unit!r}")


def _validate(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> None:
    errors: dict[str, str] = {}

    for name, value in (
        ("vcc", vcc),
        ("r1", r1),
        ("r2", r2),
        ("rc", rc),
        ("re", re),
        ("beta", beta),
        ("vbe", vbe),
    ):
        if not math.isfinite(value):
            errors[name] = "ค่าต้องเป็นตัวเลขที่จำกัด"

    positive = {
        "vcc": (vcc, "VCC"),
        "r1": (r1, "R1"),
        "r2": (r2, "R2"),
        "rc": (rc, "RC"),
        "re": (re, "RE"),
        "beta": (beta, "β"),
    }
    for name, (value, label) in positive.items():
        if name not in errors and value <= 0:
            errors[name] = f"{label} ต้องมากกว่า 0"

    if "vbe" not in errors and (vbe < 0 or vbe >= vcc):
        errors["vbe"] = "VBE ต้องอยู่ระหว่าง 0 ถึง VCC"

    if errors:
        raise ValidationError(errors)


def calculate(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    """Return the DC operating point for a voltage-divider biased NPN BJT.

    All arguments are in SI units (V, ohm). ``vbe`` is the base-emitter
    forward voltage drop, assumed constant.
    """
    _validate(vcc, r1, r2, rc, re, beta, vbe)

    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)

    # If the divider cannot turn the transistor on, the forward-active
    # equations would produce a negative base current, which is meaningless.
    # Report the cutoff state instead of a nonsense operating point.
    if vth <= vbe:
        return BiasResult(
            vth=vth,
            rth=rth,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vb=vth,
            ve=0.0,
            vc=vcc,
            vce=vcc,
            region=REGION_CUTOFF,
            warnings=[
                "Forward-Active ใช้ไม่ได้: VTH ≤ VBE แสดงสถานะ Cutoff "
                "(IB = IC = IE = 0, VC = VCC)"
            ],
        )

    ib = (vth - vbe) / (rth + (beta + 1.0) * re)
    ic = beta * ib
    ie = (beta + 1.0) * ib

    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    warnings: list[str] = []
    if vce < VCE_SAT:
        region = REGION_SATURATION
        warnings.append(
            f"ค่าเหล่านี้มาจากสมการ Forward-Active แต่ VCE = {vce:.3f} V "
            f"ต่ำกว่า VCE(sat) = {VCE_SAT:.2f} V จึงไม่ใช้ได้ใน Saturation "
            "— ใช้เพื่อการเรียนเท่านั้น"
        )
    else:
        region = REGION_ACTIVE

    return BiasResult(
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )
