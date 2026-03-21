from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from power_tool_comtrade import estimate_sampling_rate, fourier_summary, parse_comtrade, sequence_phasors, single_frequency_phasor


def _write_cfg(path: Path, dat_type: str) -> None:
    path.write_text(
        "TEST,REC,1999\n"
        "4,3A,1D\n"
        "1,IA,A,,A,1,0,0,-32768,32767,1,1,P\n"
        "2,IB,B,,A,1,0,0,-32768,32767,1,1,P\n"
        "3,IC,C,,A,1,0,0,-32768,32767,1,1,P\n"
        "1,Trip,0\n"
        "50\n"
        "1\n"
        "1000,4\n"
        "01/01/2025,00:00:00.000000\n"
        "01/01/2025,00:00:00.000000\n"
        f"{dat_type}\n"
        "1\n",
        encoding="utf-8",
    )


def test_parse_ascii_comtrade(tmp_path: Path) -> None:
    cfg = tmp_path / "sample.cfg"
    dat = tmp_path / "sample.dat"
    _write_cfg(cfg, "ASCII")
    dat.write_text(
        "1,0,0,100,-100,0\n"
        "2,1000,309,0,-309,1\n"
        "3,2000,588,-588,0,0\n"
        "4,3000,809,-809,0,1\n",
        encoding="utf-8",
    )
    record = parse_comtrade(cfg)
    assert record.file_type == "ASCII"
    assert record.analog_values.shape == (4, 3)
    assert record.digital_values.shape == (4, 1)
    assert np.isclose(record.time_s[-1], 0.003)
    assert estimate_sampling_rate(record) == 1000


def test_parse_binary_comtrade(tmp_path: Path) -> None:
    cfg = tmp_path / "bin.cfg"
    dat = tmp_path / "bin.dat"
    _write_cfg(cfg, "BINARY")
    rows = [
        (1, 0, 0, 100, -100, 0b0001),
        (2, 1000, 309, 0, -309, 0b0000),
        (3, 2000, 588, -588, 0, 0b0001),
        (4, 3000, 809, -809, 0, 0b0000),
    ]
    with dat.open("wb") as f:
        for sample, ts, ia, ib, ic, dig in rows:
            f.write(struct.pack("<iihhhH", sample, ts, ia, ib, ic, dig))
    record = parse_comtrade(cfg)
    assert record.file_type == "BINARY"
    assert record.analog_values[1, 0] == 309
    assert record.digital_values[:, 0].tolist() == [1, 0, 1, 0]


def test_fourier_summary_extracts_fundamental() -> None:
    fs = 2000.0
    t = np.arange(0.0, 0.2, 1 / fs)
    signal = 10 * np.sin(2 * np.pi * 50 * t) + 1 * np.sin(2 * np.pi * 150 * t)
    summary = fourier_summary(signal, fs, fundamental_hz=50.0, max_order=5)
    assert abs(summary.harmonics[0].amplitude - 10) < 0.2
    assert summary.thd_percent > 5.0


def test_sequence_phasors_detects_positive_sequence() -> None:
    fs = 2000.0
    t = np.arange(0.0, 0.2, 1 / fs)
    va = 10 * np.sin(2 * np.pi * 50 * t)
    vb = 10 * np.sin(2 * np.pi * 50 * t - 2 * np.pi / 3)
    vc = 10 * np.sin(2 * np.pi * 50 * t + 2 * np.pi / 3)
    center = len(t) // 2
    pha = single_frequency_phasor(va, fs, 50.0, center)
    phb = single_frequency_phasor(vb, fs, 50.0, center)
    phc = single_frequency_phasor(vc, fs, 50.0, center)
    seq = sequence_phasors(pha, phb, phc)
    assert abs(seq.positive) > 1.0
    assert abs(seq.negative) < 1e-6
    assert abs(seq.zero) < 1e-6
