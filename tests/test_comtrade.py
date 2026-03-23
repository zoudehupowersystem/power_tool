from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from power_tool_comtrade import (
    estimate_sampling_rate,
    fourier_summary,
    parse_comtrade,
    parse_waveform_file,
    sequence_phasors,
    single_frequency_phasor,
)


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


def _write_yokogawa_pair(base: Path) -> None:
    hdr = base.with_suffix(".HDR")
    wvf = base.with_suffix(".WVF")
    hdr.write_text(
        "$PublicInfo\n"
        "Format WVF\n"
        "Endian Little\n"
        "DataOffset 0\n"
        "$Group1\n"
        "BlockNumber 1\n"
        "TraceName CH1 CH2\n"
        "BlockSize 4 4\n"
        "HOffset 0 0\n"
        "HResolution 0.001 0.001\n"
        "HUnit s s\n"
        "VOffset 0 0\n"
        "VResolution 0.1 1.0\n"
        "VUnit V A\n"
        "VDataType IS2 IS2\n",
        encoding="utf-8",
    )
    with wvf.open("wb") as f:
        f.write(struct.pack("<hhhh", 0, 10, 20, 30))
        f.write(struct.pack("<hhhh", 1, 2, 3, 4))


def test_parse_yokogawa_wvf(tmp_path: Path) -> None:
    base = tmp_path / "capture"
    _write_yokogawa_pair(base)
    record = parse_waveform_file(base.with_suffix(".WVF"))
    assert record.file_type == "WVF"
    assert record.analog_values.shape == (4, 2)
    assert np.allclose(record.time_s, [0.0, 0.001, 0.002, 0.003])
    assert np.allclose(record.analog_values[:, 0], [0.0, 1.0, 2.0, 3.0])
    assert np.allclose(record.analog_values[:, 1], [1.0, 2.0, 3.0, 4.0])


def test_parse_yokogawa_wdf_via_converter(tmp_path: Path, monkeypatch) -> None:
    wdf = tmp_path / "capture.WDF"
    wdf.write_bytes(b"placeholder")
    converter = tmp_path / "fake_wdfcon.py"
    converter.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "base = Path(sys.argv[1]).with_suffix('')\n"
        "base.with_suffix('.HDR').write_text("
        "    '$PublicInfo\\nFormat WVF\\nEndian Little\\nDataOffset 0\\n'"
        "    '$Group1\\nBlockNumber 1\\nTraceName CH1\\nBlockSize 4\\n'"
        "    'HOffset 0\\nHResolution 0.001\\nHUnit s\\nVOffset 0\\n'"
        "    'VResolution 0.5\\nVUnit V\\nVDataType IS2\\n',"
        "    encoding='utf-8'"
        ")\n"
        "base.with_suffix('.WVF').write_bytes((0).to_bytes(2, 'little', signed=True)"
        " + (2).to_bytes(2, 'little', signed=True)"
        " + (4).to_bytes(2, 'little', signed=True)"
        " + (6).to_bytes(2, 'little', signed=True))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("POWER_TOOL_WDF_CONVERTER", sys.executable)
    real_run = subprocess.run
    monkeypatch.setattr(
        "power_tool_comtrade.subprocess.run",
        lambda cmd, check, capture_output, text: real_run(
            [sys.executable, str(converter), cmd[1]],
            check=check,
            capture_output=capture_output,
            text=text,
        ),
    )
    record = parse_waveform_file(wdf)
    assert record.file_type == "WDF"
    assert np.allclose(record.analog_values[:, 0], [0.0, 1.0, 2.0, 3.0])


def test_parse_embedded_wdf_samples() -> None:
    for name in ["不接地系统500Ω单相接地.WDF", "消弧线圈系统1000Ω单相接地.WDF"]:
        record = parse_waveform_file(Path(__file__).with_name(name))
        assert record.file_type == "WDF"
        assert record.analog_values.shape == (250250, 11)
        assert record.analog_channels[0].name == "CH1"
        assert record.analog_channels[-1].name == "CH11"
        assert np.isclose(record.time_s[0], -5.00498)
        assert np.isclose(record.time_s[1] - record.time_s[0], 2e-5)

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
