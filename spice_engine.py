"""Adapter between the Flask app and the external ngspice program.

This module is deliberately *not* an analytical model. It builds a netlist for
one fixed CE voltage-divider topology, calls ngspice through ``subprocess.run``
with an argument list (never ``shell=True``), parses the ASCII raw file, and
returns arrays with explicit units. Nothing is hard-coded as a "successful"
result: a missing binary, timeout, empty output or simulator error raises
``SpiceError`` instead.

The read-out conversions (Ohm's law on measured node voltages, VCE region)
live in ``dc_bias.py`` so that all physics stays in one module, as required by
``AGENTS.md``.
"""

from __future__ import annotations

import cmath
import math
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from dc_bias import current_from_voltage_drop, region_from_vce

ANALYSES = ("dc", "ac", "tran")
_MODEL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class SpiceError(Exception):
    """A user-facing failure of the ngspice integration."""


@dataclass
class SimulationParams:
    """Validated SI inputs for the reference CE amplifier.

    Resistances are ohms, capacitances farads, voltages volts, frequencies
    hertz and times seconds. ``ac_points`` is the number of points per decade.
    """

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin: float
    cout: float
    source_amp: float
    source_freq: float
    ac_fmin: float
    ac_fmax: float
    ac_points: float
    tran_stop: float
    tran_step: float
    bjt_model: str
    beta: float = 100.0

    def __post_init__(self) -> None:
        numbers = (
            "vcc",
            "r1",
            "r2",
            "rc",
            "re",
            "rl",
            "cin",
            "cout",
            "source_amp",
            "source_freq",
            "ac_fmin",
            "ac_fmax",
            "ac_points",
            "tran_stop",
            "tran_step",
            "beta",
        )
        for name in numbers:
            value = getattr(self, name)
            if isinstance(value, bool):
                raise SpiceError(f"{name} ต้องเป็นตัวเลข")
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise SpiceError(f"{name} ต้องเป็นตัวเลข (พบ {value!r})") from None
            if not math.isfinite(value):
                raise SpiceError(f"{name} ต้องเป็นตัวเลขที่จำกัด")
            setattr(self, name, value)

        if not isinstance(self.bjt_model, str) or not _MODEL_NAME_RE.match(self.bjt_model):
            raise SpiceError("ชื่อโมเดลทรานซิสเตอร์ไม่ถูกต้อง")

        positive = (
            "vcc",
            "r1",
            "r2",
            "rc",
            "re",
            "rl",
            "cin",
            "cout",
            "source_amp",
            "source_freq",
            "ac_fmin",
            "ac_fmax",
            "ac_points",
            "tran_stop",
            "tran_step",
            "beta",
        )
        for name in positive:
            if getattr(self, name) <= 0:
                raise SpiceError(f"{name} ต้องมากกว่า 0")
        if self.ac_fmax <= self.ac_fmin:
            raise SpiceError("ac_fmax ต้องมากกว่า ac_fmin")
        if self.ac_points < 2:
            raise SpiceError("ac_points ต้องมากกว่าหรือเท่ากับ 2")
        if self.tran_step >= self.tran_stop:
            raise SpiceError("tran_step ต้องน้อยกว่า tran_stop")
        if self.source_amp >= self.vcc:
            raise SpiceError("source_amp ต้องน้อยกว่า VCC")


@dataclass
class SpiceResult:
    """Parsed simulator output. ``values`` maps a variable name to a list."""

    analysis: str
    source: str = "SPICE"
    version: str = ""
    values: dict[str, list] = field(default_factory=dict)
    meta: dict[str, object] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    netlist: str = ""
    log_tail: str = ""


_SUFFIXES = (("meg", 1e6), ("k", 1e3), ("", 1.0), ("m", 1e-3), ("u", 1e-6), ("n", 1e-9), ("p", 1e-12))


def spice_number(value: float) -> str:
    """Format a SI number as a compact SPICE suffix literal (e.g. 100k, 10u)."""
    if not math.isfinite(value):
        raise SpiceError("ค่าไม่ใช่ตัวเลขที่จำกัด")
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    for suffix, scale in _SUFFIXES:
        if magnitude >= scale:
            scaled = magnitude / scale
            break
    else:  # pragma: no cover - covered by the last suffix
        suffix, scaled = "p", magnitude / 1e-12
    text = f"{scaled:.6f}".rstrip("0").rstrip(".")
    return f"{sign}{text}{suffix}"


def build_netlist(analysis: str, params: SimulationParams) -> str:
    """Return a netlist string for ``analysis`` in ``ANALYSES``."""
    if analysis not in ANALYSES:
        raise SpiceError(f"analysis ต้องเป็น {' / '.join(ANALYSES)} (พบ {analysis!r})")

    amp = spice_number(params.source_amp)
    freq = spice_number(params.source_freq)
    lines = [
        f"* CE voltage-divider amplifier - {analysis}",
        f"VCC vcc 0 DC {spice_number(params.vcc)}",
        f"Vi in 0 DC 0 AC {amp} SIN(0 {amp} {freq} 0 0 0)",
        f"R1 vcc b {spice_number(params.r1)}",
        f"R2 b 0 {spice_number(params.r2)}",
        f"RC vcc c {spice_number(params.rc)}",
        f"RE e 0 {spice_number(params.re)}",
        f"Q1 c b e {params.bjt_model}",
        f"Cin in b {spice_number(params.cin)}",
        f"Cout c out {spice_number(params.cout)}",
        f"RL out 0 {spice_number(params.rl)}",
        f".model {params.bjt_model} NPN BF={spice_number(params.beta)}",
    ]

    if analysis == "dc":
        lines.append(".op")
    elif analysis == "ac":
        lines.append(
            f".ac dec {spice_number(params.ac_points)} "
            f"{spice_number(params.ac_fmin)} {spice_number(params.ac_fmax)}"
        )
    else:
        step = spice_number(params.tran_step)
        lines.append(f".tran {step} {spice_number(params.tran_stop)} 0 {step}")
    lines.append(".end")
    return "\n".join(lines) + "\n"


_HEADER_RE = re.compile(r"^(Title|Date|Command|Plotname|Flags|No\. Variables|No\. Points):\s*(.*)$")
# Do not split on ',' here: a complex value is written as "real,imag".
_TOKEN_SPLIT_RE = re.compile(r"[\t ]+")
_INDEX_RE = re.compile(r"^\d+$")


def parse_raw(text: str) -> dict[str, object]:
    """Parse an ASCII ngspice raw file into a dict of arrays.

    Complex analyses are returned as Python ``complex`` values. The analysis
    name is inferred from ``Plotname``.
    """
    if not text or not text.strip():
        raise SpiceError("ngspice ไม่ได้เขียนไฟล์ผล (raw file ว่าง)")

    lines = text.splitlines()
    headers: dict[str, str] = {}
    variables: list[str] = []
    values_at: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "Values:":
            values_at = index + 1
            break
        match = _HEADER_RE.match(stripped)
        if match:
            headers[match.group(1)] = match.group(2).strip()
            continue
        tokens = [token for token in _TOKEN_SPLIT_RE.split(stripped) if token]
        if len(tokens) >= 2 and _INDEX_RE.match(tokens[0]):
            variables.append(tokens[1])

    if values_at is None:
        raise SpiceError("ไฟล์ผล ngspice ไม่มีส่วน Values")
    try:
        nvars = int(headers["No. Variables"])
        npoints = int(headers["No. Points"])
    except (KeyError, ValueError):
        raise SpiceError("ไฟล์ผล ngspice ขาดส่วนบอกจำนวนตัวแปร/จุด") from None
    if nvars <= 0 or npoints <= 0 or len(variables) < nvars:
        raise SpiceError("ไฟล์ผล ngspice มีโครงสร้างไม่ครบ")

    # ngspice writes one value per line, with an optional point index before
    # the first value of each row. Treat the block as a flat token stream.
    tokens: list[str] = []
    for line in lines[values_at:]:
        tokens.extend(token for token in _TOKEN_SPLIT_RE.split(line.strip()) if token)
    if len(tokens) == npoints * (nvars + 1):
        stream: list[str] = []
        for point in range(npoints):
            offset = point * (nvars + 1)
            if not _INDEX_RE.match(tokens[offset]):
                raise SpiceError("เลขลำดับจุดในไฟล์ผล ngspice ไม่ถูกต้อง")
            stream.extend(tokens[offset + 1 : offset + 1 + nvars])
    elif len(tokens) == npoints * nvars:
        stream = tokens
    else:
        raise SpiceError(
            f"ไฟล์ผล ngspice มี {len(tokens)} ค่า ไม่ตรงกับ {npoints} จุด × {nvars} ตัวแปร"
        )

    is_complex = "complex" in headers.get("Flags", "").lower()
    columns: list[list] = [[] for _ in range(nvars)]
    for point in range(npoints):
        row = stream[point * nvars : (point + 1) * nvars]
        for column, token in zip(columns, row):
            if is_complex:
                real, _, imag = token.partition(",")
                if not imag:
                    raise SpiceError("พบค่า complex ที่ขาดส่วนจินภาพ")
                column.append(complex(float(real), float(imag)))
            else:
                column.append(float(token))

    # The frequency axis is complex-typed in an .ac raw file, but its imaginary
    # part is always zero. Keep it as a plain float for charts and sweeps.
    axis_names = variables[:nvars]
    if "frequency" in axis_names:
        axis_index = axis_names.index("frequency")
        columns[axis_index] = [
            float(value.real) if isinstance(value, complex) else float(value)
            for value in columns[axis_index]
        ]

    plotname = headers.get("Plotname", "").lower()
    if "operating point" in plotname:
        analysis = "dc"
    elif "ac analysis" in plotname:
        analysis = "ac"
    elif "transient analysis" in plotname:
        analysis = "tran"
    else:
        analysis = "unknown"

    data: dict[str, object] = {
        "analysis": analysis,
        "plotname": headers.get("Plotname", ""),
        "flags": headers.get("Flags", ""),
        "command": headers.get("Command", ""),
        "variables": variables[:nvars],
        "npoints": npoints,
    }
    for name, column in zip(variables[:nvars], columns):
        data[name] = column
    return data


def op_to_dc(data: dict[str, object], params: SimulationParams) -> dict[str, float]:
    """Convert an ``.op`` result into the same quantities as ``dc_bias``.

    IC is the drop across RC, IE is the drop across RE, and IB = IE - IC.
    These are read-out conversions of measured node voltages, not the
    forward-active teaching equations.
    """
    try:
        vcc = float(data["v(vcc)"][0])  # type: ignore[index]
        vb = float(data["v(b)"][0])  # type: ignore[index]
        vc = float(data["v(c)"][0])  # type: ignore[index]
        ve = float(data["v(e)"][0])  # type: ignore[index]
    except (KeyError, IndexError, TypeError, ValueError):
        raise SpiceError("ผล .op ขาด node voltage ที่จำเป็น (vcc/b/c/e)") from None

    ic = current_from_voltage_drop(vcc, vc, params.rc)
    ie = current_from_voltage_drop(ve, 0.0, params.re)
    ib = ie - ic
    vce = vc - ve
    return {
        "vcc": vcc,
        "vb": vb,
        "vc": vc,
        "ve": ve,
        "vce": vce,
        "ic": ic,
        "ie": ie,
        "ib": ib,
        "region": region_from_vce(vce),
    }


def _normalise_phase(degrees: float) -> float:
    value = degrees
    while value > 180.0:
        value -= 360.0
    while value < -180.0:
        value += 360.0
    if value > 179.999999:  # a CE stage is reported as -180°, not +180°
        return -180.0
    return value


def _log_interpolate(f1: float, g1: float, f2: float, g2: float, target: float) -> float:
    if math.isclose(g1, g2):
        return f1
    fraction = (target - g1) / (g2 - g1)
    fraction = min(1.0, max(0.0, fraction))
    return 10 ** (math.log10(f1) + fraction * (math.log10(f2) - math.log10(f1)))


def analyze_ac(freqs: list[float], vin: list[complex], vout: list[complex]) -> dict[str, object]:
    """Return gain, phase and -3 dB edges from an AC sweep."""
    if len(freqs) < 2 or len(vin) != len(freqs) or len(vout) != len(freqs):
        raise SpiceError("ข้อมูล .ac ไม่ครบ")
    if any(f <= 0 for f in freqs):
        raise SpiceError("ความถี่ในผล .ac ต้องมากกว่า 0")

    gain: list[float] = []
    gain_db: list[float] = []
    phase_deg: list[float] = []
    for source, load in zip(vin, vout):
        magnitude = abs(source)
        if magnitude == 0:
            raise SpiceError("ฉันท์ Vin ในผล .ac เป็นศูนย์ ไม่สามารถหา gain ได้")
        ratio = abs(load) / magnitude
        gain.append(ratio)
        gain_db.append(20.0 * math.log10(ratio) if ratio > 0 else -300.0)
        phase_deg.append(_normalise_phase(math.degrees(cmath.phase(load) - cmath.phase(source))))

    peak_gain = max(gain)
    peak_gain_db = 20.0 * math.log10(peak_gain) if peak_gain > 0 else -300.0
    threshold = peak_gain / math.sqrt(2.0)
    above = [index for index, value in enumerate(gain) if value >= threshold]

    f_low: float | None = None
    f_high: float | None = None
    if above:
        first, last = above[0], above[-1]
        if first > 0:
            f_low = _log_interpolate(freqs[first - 1], gain[first - 1], freqs[first], gain[first], threshold)
        else:
            f_low = freqs[first]
        if last < len(freqs) - 1:
            f_high = _log_interpolate(freqs[last], gain[last], freqs[last + 1], gain[last + 1], threshold)
        else:
            f_high = freqs[last]

    determined = (
        above
        and first > 0
        and last < len(freqs) - 1
        and f_low is not None
        and f_high is not None
    )
    if not determined:
        f_low, f_high = None, None
    if determined:
        note = f"fL ≈ {spice_number(f_low)}Hz, fH ≈ {spice_number(f_high)}Hz (เทียบ -3 dB จาก gain สูงสุด)"
    else:
        note = "not determined in sweep range — ไม่พบจุดตัด -3 dB ภายในช่วงที่ sweep"

    return {
        "frequency": list(freqs),
        "gain": gain,
        "gain_db": gain_db,
        "phase_deg": phase_deg,
        "peak_gain": peak_gain,
        "peak_gain_db": peak_gain_db,
        "f_low": f_low,
        "f_high": f_high,
        "bandwidth_note": note,
    }


def analyze_tran(times: list[float], vin: list[float], vout: list[float]) -> dict[str, object]:
    """Return peak-to-peak amplitudes and inversion from a transient trace."""
    if len(times) < 2 or len(vin) != len(times) or len(vout) != len(times):
        raise SpiceError("ข้อมูล .tran ไม่ครบ")
    vpp_in = max(vin) - min(vin)
    vpp_out = max(vout) - min(vout)
    mean_in = sum(vin) / len(vin)
    mean_out = sum(vout) / len(vout)
    covariance = sum((a - mean_in) * (b - mean_out) for a, b in zip(vin, vout))
    variance = sum((a - mean_in) ** 2 for a in vin)
    inverted = variance > 0 and covariance < 0
    return {
        "time": list(times),
        "vin": list(vin),
        "vout": list(vout),
        "vpp_in": vpp_in,
        "vpp_out": vpp_out,
        "inverted": inverted,
        "phase_deg_est": -180.0 if inverted else 0.0,
    }


def downsample(points: list, limit: int) -> list:
    """Keep at most ``limit`` points, always retaining the first and last."""
    if limit < 2:
        raise SpiceError("limit ต้องมากกว่าหรือเท่ากับ 2")
    count = len(points)
    if count <= limit:
        return list(points)
    last = count - 1
    indices = sorted({round(index * last / (limit - 1)) for index in range(limit)})
    return [points[index] for index in indices]


def find_ngspice() -> str | None:
    """Resolve the simulator path without modifying the machine PATH."""
    from_env = os.environ.get("NGSPICE")
    if from_env:
        return from_env
    from_path = shutil_which("ngspice")
    if from_path:
        return from_path
    candidates = [
        Path(__file__).resolve().parent / "tools" / "ngspice" / "bin" / "ngspice.exe",
        Path.home() / "ngspice-47" / "Spice64" / "bin" / "ngspice.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def shutil_which(name: str) -> str | None:
    """Thin wrapper kept separate so tests can patch discovery easily."""
    import shutil

    return shutil.which(name)


def run(
    analysis: str,
    params: SimulationParams,
    ngspice_path: str | None = None,
    timeout: float = 30.0,
) -> SpiceResult:
    """Run a real ngspice batch job and return parsed values with units.

    Each call gets its own temporary working directory. Errors are surfaced as
    ``SpiceError`` so the web layer can never show an old graph with a success
    badge.
    """
    if analysis not in ANALYSES:
        raise SpiceError(f"analysis ต้องเป็น {' / '.join(ANALYSES)} (พบ {analysis!r})")
    executable = ngspice_path or find_ngspice()
    if not executable:
        raise SpiceError("ไม่พบ ngspice — กรุณาติดตั้งแล้วใส่ใน PATH หรือตั้งค่า NGSPICE")
    if not Path(executable).is_file():
        raise SpiceError(f"ไม่พบ ngspice ที่ตำแหน่ง {executable} กรุณาตรวจค่า NGSPICE")

    netlist = build_netlist(analysis, params)
    with tempfile.TemporaryDirectory(prefix="bjt-spice-") as workdir:
        directory = Path(workdir)
        (directory / "circuit.cir").write_text(netlist, encoding="ascii")
        command = [
            str(executable),
            "-b",
            "-o",
            "run.log",
            "-r",
            "run.raw",
            "circuit.cir",
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=directory,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise SpiceError(f"ngspice ใช้เวลาเกิน {timeout:g} วินาที กรุณาลดช่วง sweep") from None
        except (OSError, ValueError) as exc:
            raise SpiceError(f"เรียก ngspice ไม่ได้: {exc}") from None

        log_path = directory / "run.log"
        raw_path = directory / "run.raw"
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        log_tail = "\n".join(log_text.splitlines()[-12:])
        if not raw_path.is_file():
            raise SpiceError(f"ngspice ไม่สร้างไฟล์ผล (exit={completed.returncode}) {log_tail}")
        raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
        data = parse_raw(raw_text)
        if data["analysis"] != analysis:  # type: ignore[comparison-overlap]
            raise SpiceError(
                f"ngspice คืนผล {data['analysis']!r} แต่ต้องการ {analysis!r} {log_tail}"
            )

    command_line = str(data.get("command", ""))  # type: ignore[arg-type]
    version_match = re.search(r"ngspice[- ]?\d+[^\r\n]*", command_line)
    version = version_match.group(0) if version_match else command_line

    result = SpiceResult(
        analysis=analysis,
        version=version,
        values={key: value for key, value in data.items() if isinstance(value, list)},
        meta={
            "plotname": data["plotname"],
            "flags": data["flags"],
            "npoints": data["npoints"],
            "variables": data["variables"],
        },
        netlist=netlist,
        log_tail=log_tail,
    )
    if completed.returncode != 0:
        result.warnings.append(f"ngspice exit code = {completed.returncode}: {log_tail}")
    return result
