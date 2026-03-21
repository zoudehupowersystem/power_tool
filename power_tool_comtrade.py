from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import struct
import numpy as np


@dataclass
class ComtradeChannel:
    index: int
    name: str
    phase: str
    unit: str
    a: float
    b: float


@dataclass
class ComtradeRecord:
    station_name: str
    device_id: str
    revision: str
    frequency_hz: float
    sample_rates: list[tuple[float, int]]
    analog_channels: list[ComtradeChannel]
    digital_channel_names: list[str]
    time_s: np.ndarray
    analog_values: np.ndarray
    digital_values: np.ndarray
    file_type: str
    cfg_path: Path
    dat_path: Path

    @property
    def duration_s(self) -> float:
        return float(self.time_s[-1] - self.time_s[0]) if self.time_s.size > 1 else 0.0


@dataclass
class HarmonicComponent:
    order: int
    frequency_hz: float
    amplitude: float
    rms: float
    phase_deg: float


@dataclass
class FourierSummary:
    fundamental_hz: float
    dc: float
    harmonics: list[HarmonicComponent]
    thd_percent: float


@dataclass
class SequenceSummary:
    positive: float
    negative: float
    zero: float
    unbalance_percent: float


@dataclass
class PronySummary:
    dominant_frequency_hz: float
    damping_ratio_percent: float
    decay_time_constant_s: float
    amplitude: float


def _parse_float(text: str, default: float = 0.0) -> float:
    text = text.strip()
    if not text:
        return default
    return float(text)


def parse_cfg(cfg_path: str | Path) -> dict:
    path = Path(cfg_path)
    lines = [line.strip() for line in path.read_text(encoding='utf-8-sig', errors='ignore').splitlines() if line.strip()]
    if len(lines) < 6:
        raise ValueError('CFG 文件内容不足，无法解析。')

    station_parts = [p.strip() for p in lines[0].split(',')]
    station_name = station_parts[0] if station_parts else ''
    device_id = station_parts[1] if len(station_parts) > 1 else ''
    revision = station_parts[2] if len(station_parts) > 2 else '1999'

    counts = [p.strip() for p in lines[1].split(',')]
    total_channels = int(counts[0])
    analog_count = int(counts[1].rstrip('Aa'))
    digital_count = int(counts[2].rstrip('Dd')) if len(counts) > 2 else 0

    pos = 2
    analog_channels: list[ComtradeChannel] = []
    for _ in range(analog_count):
        parts = [p.strip() for p in lines[pos].split(',')]
        analog_channels.append(
            ComtradeChannel(
                index=int(parts[0]),
                name=parts[1],
                phase=parts[2] if len(parts) > 2 else '',
                unit=parts[4] if len(parts) > 4 else '',
                a=_parse_float(parts[5], 1.0) if len(parts) > 5 else 1.0,
                b=_parse_float(parts[6], 0.0) if len(parts) > 6 else 0.0,
            )
        )
        pos += 1

    digital_names: list[str] = []
    for _ in range(digital_count):
        parts = [p.strip() for p in lines[pos].split(',')]
        digital_names.append(parts[1] if len(parts) > 1 else f'D{len(digital_names)+1}')
        pos += 1

    frequency_hz = _parse_float(lines[pos])
    pos += 1
    nrates = int(lines[pos].split(',')[0].strip())
    pos += 1
    sample_rates: list[tuple[float, int]] = []
    for _ in range(nrates):
        rate_parts = [p.strip() for p in lines[pos].split(',')]
        sample_rates.append((_parse_float(rate_parts[0]), int(rate_parts[1])))
        pos += 1

    start_timestamp = lines[pos] if pos < len(lines) else ''
    pos += 1
    trigger_timestamp = lines[pos] if pos < len(lines) else ''
    pos += 1
    file_type = lines[pos].split(',')[0].strip().upper() if pos < len(lines) else 'ASCII'
    pos += 1
    timemult = _parse_float(lines[pos], 1.0) if pos < len(lines) else 1.0

    return {
        'station_name': station_name,
        'device_id': device_id,
        'revision': revision,
        'total_channels': total_channels,
        'analog_count': analog_count,
        'digital_count': digital_count,
        'analog_channels': analog_channels,
        'digital_names': digital_names,
        'frequency_hz': frequency_hz,
        'sample_rates': sample_rates,
        'start_timestamp': start_timestamp,
        'trigger_timestamp': trigger_timestamp,
        'file_type': file_type,
        'timemult': timemult,
    }


def parse_comtrade(cfg_path: str | Path, dat_path: str | Path | None = None) -> ComtradeRecord:
    cfg_path = Path(cfg_path)
    cfg = parse_cfg(cfg_path)
    dat_path = Path(dat_path) if dat_path is not None else cfg_path.with_suffix('.dat')
    file_type = cfg['file_type']
    if file_type == 'ASCII':
        time_s, analog, digital = _read_ascii_dat(dat_path, cfg)
    elif file_type == 'BINARY':
        time_s, analog, digital = _read_binary_dat(dat_path, cfg)
    else:
        raise ValueError(f'暂不支持的 COMTRADE DAT 类型：{file_type}')

    return ComtradeRecord(
        station_name=cfg['station_name'],
        device_id=cfg['device_id'],
        revision=cfg['revision'],
        frequency_hz=cfg['frequency_hz'],
        sample_rates=cfg['sample_rates'],
        analog_channels=cfg['analog_channels'],
        digital_channel_names=cfg['digital_names'],
        time_s=time_s,
        analog_values=analog,
        digital_values=digital,
        file_type=file_type,
        cfg_path=cfg_path,
        dat_path=dat_path,
    )


def _read_ascii_dat(dat_path: Path, cfg: dict):
    analog_count = cfg['analog_count']
    digital_count = cfg['digital_count']
    timemult = cfg['timemult']
    rows = []
    for raw in dat_path.read_text(encoding='utf-8-sig', errors='ignore').splitlines():
        line = raw.strip()
        if not line:
            continue
        rows.append([p.strip() for p in line.split(',')])
    n = len(rows)
    time_s = np.zeros(n, dtype=float)
    analog = np.zeros((n, analog_count), dtype=float)
    digital = np.zeros((n, digital_count), dtype=int) if digital_count else np.zeros((n, 0), dtype=int)
    for i, row in enumerate(rows):
        time_s[i] = _parse_float(row[1]) * 1e-6 * timemult
        for j, ch in enumerate(cfg['analog_channels']):
            raw_val = _parse_float(row[2 + j])
            analog[i, j] = ch.a * raw_val + ch.b
        digital_start = 2 + analog_count
        for j in range(digital_count):
            if digital_start + j < len(row):
                digital[i, j] = int(float(row[digital_start + j]))
    return time_s, analog, digital


def _read_binary_dat(dat_path: Path, cfg: dict):
    analog_count = cfg['analog_count']
    digital_count = cfg['digital_count']
    timemult = cfg['timemult']
    digital_words = math.ceil(digital_count / 16)
    record_fmt = '<ii' + ('h' * analog_count) + ('H' * digital_words)
    record_size = struct.calcsize(record_fmt)
    data = dat_path.read_bytes()
    if len(data) % record_size != 0:
        raise ValueError('BINARY DAT 长度与 CFG 通道配置不匹配。')
    n = len(data) // record_size
    time_s = np.zeros(n, dtype=float)
    analog = np.zeros((n, analog_count), dtype=float)
    digital = np.zeros((n, digital_count), dtype=int) if digital_count else np.zeros((n, 0), dtype=int)
    offset = 0
    for i in range(n):
        record = struct.unpack_from(record_fmt, data, offset)
        offset += record_size
        time_s[i] = float(record[1]) * 1e-6 * timemult
        for j, ch in enumerate(cfg['analog_channels']):
            analog[i, j] = ch.a * float(record[2 + j]) + ch.b
        words = record[2 + analog_count:]
        bit_idx = 0
        for word in words:
            for k in range(16):
                if bit_idx < digital_count:
                    digital[i, bit_idx] = (word >> k) & 1
                    bit_idx += 1
    return time_s, analog, digital


def estimate_sampling_rate(record: ComtradeRecord) -> float:
    if record.sample_rates and record.sample_rates[0][0] > 0:
        return float(record.sample_rates[0][0])
    if record.time_s.size > 1:
        dt = float(np.median(np.diff(record.time_s)))
        if dt > 0:
            return 1.0 / dt
    return 0.0


def fourier_summary(signal: np.ndarray, sample_rate_hz: float, fundamental_hz: float = 50.0, max_order: int = 10) -> FourierSummary:
    x = np.asarray(signal, dtype=float)
    n = x.size
    if n < 4:
        raise ValueError('采样点不足，无法做傅里叶分析。')
    t = np.arange(n, dtype=float) / sample_rate_hz
    dc = float(np.mean(x))
    x0 = x - dc
    harmonics: list[HarmonicComponent] = []
    fund_rms = 0.0
    for order in range(1, max_order + 1):
        freq = order * fundamental_hz
        basis = np.exp(-1j * 2.0 * np.pi * freq * t)
        coef = 2.0 / n * np.dot(x0, basis)
        amp = float(abs(coef))
        rms = amp / math.sqrt(2.0)
        phase = math.degrees(math.atan2(coef.imag, coef.real))
        harmonics.append(HarmonicComponent(order, freq, amp, rms, phase))
        if order == 1:
            fund_rms = rms
    other_sq = sum(h.rms ** 2 for h in harmonics[1:])
    thd = math.sqrt(other_sq) / fund_rms * 100.0 if fund_rms > 1e-12 else 0.0
    return FourierSummary(fundamental_hz=fundamental_hz, dc=dc, harmonics=harmonics, thd_percent=thd)


def sequence_components(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> SequenceSummary:
    va = float(np.sqrt(np.mean(np.asarray(a, dtype=float) ** 2)))
    vb = float(np.sqrt(np.mean(np.asarray(b, dtype=float) ** 2)))
    vc = float(np.sqrt(np.mean(np.asarray(c, dtype=float) ** 2)))
    alpha = complex(-0.5, math.sqrt(3.0) / 2.0)
    v0 = (va + vb + vc) / 3.0
    v1 = abs((va + alpha * vb + (alpha ** 2) * vc) / 3.0)
    v2 = abs((va + (alpha ** 2) * vb + alpha * vc) / 3.0)
    unbalance = (v2 / v1 * 100.0) if v1 > 1e-12 else 0.0
    return SequenceSummary(positive=v1, negative=v2, zero=abs(v0), unbalance_percent=unbalance)


def prony_like_summary(signal: np.ndarray, sample_rate_hz: float) -> PronySummary:
    x = np.asarray(signal, dtype=float)
    n = x.size
    if n < 32:
        raise ValueError('采样点不足，无法做振荡信息估计。')
    x = x - np.mean(x)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate_hz)
    spec = np.abs(np.fft.rfft(x))
    if spec.size < 3:
        raise ValueError('频谱分辨率不足。')
    idx = int(np.argmax(spec[1:]) + 1)
    dom_freq = float(freqs[idx])
    analytic_amp = np.abs(x)
    analytic_amp = np.maximum(analytic_amp, np.max(analytic_amp) * 1e-6)
    t = np.arange(n, dtype=float) / sample_rate_hz
    coeffs = np.polyfit(t, np.log(analytic_amp), 1)
    sigma = float(coeffs[0])
    wn = 2.0 * math.pi * max(dom_freq, 1e-9)
    zeta = max(0.0, min(0.999, -sigma / math.sqrt(sigma * sigma + wn * wn)))
    tau = float('inf') if abs(sigma) < 1e-12 else -1.0 / sigma
    return PronySummary(dom_freq, zeta * 100.0, tau, float(np.max(np.abs(x))))
