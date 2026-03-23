from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import os
import re
import subprocess
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


@dataclass
class SequencePhasorSet:
    zero: complex
    positive: complex
    negative: complex


def single_frequency_phasor(signal: np.ndarray, sample_rate_hz: float, fundamental_hz: float, center_index: int, cycles: float = 1.0) -> complex:
    x = np.asarray(signal, dtype=float)
    if x.size < 4:
        raise ValueError('采样点不足，无法提取工频相量。')
    window_samples = max(8, int(round(sample_rate_hz / max(fundamental_hz, 1e-9) * cycles)))
    half = window_samples // 2
    start = max(0, center_index - half)
    end = min(x.size, start + window_samples)
    start = max(0, end - window_samples)
    seg = x[start:end]
    if seg.size < 4:
        raise ValueError('相量窗长度不足。')
    t = np.arange(seg.size, dtype=float) / sample_rate_hz
    basis = np.exp(-1j * 2.0 * np.pi * fundamental_hz * t)
    coef = 2.0 / seg.size * np.dot(seg, basis)
    return coef / math.sqrt(2.0)


def sequence_phasors(a: complex, b: complex, c: complex) -> SequencePhasorSet:
    alpha = complex(-0.5, math.sqrt(3.0) / 2.0)
    zero = (a + b + c) / 3.0
    positive = (a + alpha * b + (alpha ** 2) * c) / 3.0
    negative = (a + (alpha ** 2) * b + alpha * c) / 3.0
    return SequencePhasorSet(zero=zero, positive=positive, negative=negative)


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


def parse_waveform_file(path: str | Path) -> ComtradeRecord:
    source_path = Path(path)
    suffix = source_path.suffix.lower()
    if suffix == '.cfg':
        return parse_comtrade(source_path)
    if suffix in {'.hdr', '.wvf', '.wdf'}:
        return parse_yokogawa_waveform(source_path)
    raise ValueError(f'暂不支持的录波文件类型：{source_path.suffix or "(无扩展名)"}')


def parse_yokogawa_waveform(path: str | Path) -> ComtradeRecord:
    source_path = Path(path)
    suffix = source_path.suffix.lower()
    if suffix == '.wdf':
        return _parse_wdf_waveform(source_path)
    if suffix == '.wvf':
        wvf_path = source_path
        hdr_path = _resolve_companion_file(source_path, '.HDR')
    elif suffix == '.hdr':
        hdr_path = source_path
        wvf_path = _resolve_companion_file(source_path, '.WVF')
    else:
        raise ValueError(f'无法解析的横河录波文件类型：{source_path.suffix}')
    if not hdr_path.exists():
        raise ValueError(f'缺少配套 HDR 头文件：{hdr_path.name}')
    if not wvf_path.exists():
        raise ValueError(f'缺少配套 WVF 波形文件：{wvf_path.name}')

    header = _parse_yokogawa_hdr(hdr_path)
    analog_values, time_s = _read_yokogawa_wvf(wvf_path, header)
    channels = [
        ComtradeChannel(
            index=idx + 1,
            name=str(trace['name']),
            phase='',
            unit=str(trace['y_unit']),
            a=1.0,
            b=0.0,
        )
        for idx, trace in enumerate(header['traces'])
    ]
    frequency_hz = _infer_nominal_frequency(time_s)
    return ComtradeRecord(
        station_name=source_path.stem,
        device_id='Yokogawa',
        revision='WVF',
        frequency_hz=frequency_hz,
        sample_rates=[(1.0 / max(float(np.median(np.diff(time_s))), 1e-12), len(time_s))] if time_s.size > 1 else [],
        analog_channels=channels,
        digital_channel_names=[],
        time_s=time_s,
        analog_values=analog_values,
        digital_values=np.zeros((analog_values.shape[0], 0), dtype=int),
        file_type='WDF' if path and Path(path).suffix.lower() == '.wdf' else 'WVF',
        cfg_path=hdr_path,
        dat_path=wvf_path,
    )


def _convert_wdf_to_wvf(path: Path) -> Path:
    converter = os.environ.get('POWER_TOOL_WDF_CONVERTER') or os.environ.get('WDF2WVF_EXE') or os.environ.get('WDFCON_EXE')
    if not converter:
        raise ValueError(
            'WDF 为横河专有格式，当前实现需要通过外部转换器先转成 WVF/HDR。'
            '请设置环境变量 POWER_TOOL_WDF_CONVERTER 指向官方 WDF2WVF/WDFCon 可执行文件。'
        )
    converter_path = Path(converter)
    if not converter_path.exists():
        raise ValueError(f'未找到 WDF 转换器：{converter_path}')
    try:
        subprocess.run([str(converter_path), str(path)], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or '').strip()
        stdout = (exc.stdout or '').strip()
        detail = stderr or stdout or str(exc)
        raise ValueError(f'WDF 转换失败：{detail}') from exc
    wvf_path = path.with_suffix('.WVF')
    if not wvf_path.exists():
        wvf_path = _resolve_companion_file(path, '.WVF')
    if not wvf_path.exists():
        raise ValueError(f'转换完成后未找到输出文件：{wvf_path.name}')
    return wvf_path




def _parse_wdf_waveform(path: Path) -> ComtradeRecord:
    try:
        header, raw_path = _extract_wdf_embedded_header(path)
        analog_values, time_s = _read_yokogawa_wvf(raw_path, header)
    except ValueError:
        raw_path = _convert_wdf_to_wvf(path)
        header = _parse_yokogawa_hdr(_resolve_companion_file(raw_path, '.HDR'))
        analog_values, time_s = _read_yokogawa_wvf(raw_path, header)
    channels = [
        ComtradeChannel(
            index=idx + 1,
            name=str(trace['name']),
            phase='',
            unit=str(trace['y_unit']),
            a=1.0,
            b=0.0,
        )
        for idx, trace in enumerate(header['traces'])
    ]
    frequency_hz = _infer_nominal_frequency(time_s)
    return ComtradeRecord(
        station_name=path.stem,
        device_id='Yokogawa',
        revision='WDF',
        frequency_hz=frequency_hz,
        sample_rates=[(1.0 / max(float(np.median(np.diff(time_s))), 1e-12), len(time_s))] if time_s.size > 1 else [],
        analog_channels=channels,
        digital_channel_names=[],
        time_s=time_s,
        analog_values=analog_values,
        digital_values=np.zeros((analog_values.shape[0], 0), dtype=int),
        file_type='WDF',
        cfg_path=path,
        dat_path=raw_path,
    )


def _extract_wdf_embedded_header(path: Path) -> tuple[dict, Path]:
    raw = path.read_bytes()
    marker = b'//YOKOGAWA ASCII FILE FORMAT'
    start = raw.find(marker)
    if start < 0:
        raise ValueError('WDF 文件中未找到嵌入式 Yokogawa ASCII 头信息。')
    tail = raw[start:].decode('ascii', errors='ignore')
    end_marker = '\nFeND'
    end = tail.find(end_marker)
    if end >= 0:
        tail = tail[:end]
    header = _parse_yokogawa_text_header(tail)
    header['raw_bytes'] = raw
    return header, path


def _parse_yokogawa_text_header(text: str) -> dict:
    sections: dict[str, dict[str, object]] = {}
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('//'):
            continue
        if line.startswith('$'):
            current = line[1:].strip()
            sections.setdefault(current, {})
            continue
        if current is None:
            continue
        parts = [part for part in re.split(r'\s{2,}', raw_line.strip()) if part]
        if len(parts) < 2:
            continue
        key = parts[0]
        values = [_coerce_token(token) for token in parts[1:]]
        sections[current][key] = values[0] if len(values) == 1 else values
    return _build_yokogawa_header(sections)


def _build_yokogawa_header(sections: dict[str, dict[str, object]]) -> dict:
    public = sections.get('PublicInfo', {})
    groups = [sections[name] for name in sorted(sections) if re.match(r'Group\d+', name)]
    if not groups:
        raise ValueError('HDR 文件中未找到 Group 段，无法解析横河录波。')
    endian_text = str(public.get('Endian', 'Little'))
    endian = '>' if endian_text.startswith('Big') else '<'
    trace_fields = {
        'name': [],
        'block_size': [],
        'x_offset': [],
        'x_gain': [],
        'x_unit': [],
        'y_offset': [],
        'y_gain': [],
        'y_unit': [],
        'data_type': [],
    }
    mapping = {
        'TraceName': 'name',
        'BlockSize': 'block_size',
        'HOffset': 'x_offset',
        'HResolution': 'x_gain',
        'HUnit': 'x_unit',
        'VOffset': 'y_offset',
        'VResolution': 'y_gain',
        'VUnit': 'y_unit',
        'VDataType': 'data_type',
    }
    for group in groups:
        for hdr_key, field_name in mapping.items():
            value = group.get(hdr_key)
            if value is None:
                raise ValueError(f'HDR 缺少关键字段：{hdr_key}')
            if isinstance(value, list):
                trace_fields[field_name].extend(value)
            else:
                trace_fields[field_name].append(value)
    traces = []
    for idx, name in enumerate(trace_fields['name']):
        dtype_text = str(trace_fields['data_type'][idx])
        num_bytes, fmt_code = _decode_yokogawa_data_type(dtype_text)
        traces.append(
            {
                'index': idx,
                'name': str(name),
                'block_size': int(trace_fields['block_size'][idx]),
                'x_offset': float(trace_fields['x_offset'][idx]),
                'x_gain': float(trace_fields['x_gain'][idx]),
                'x_unit': str(trace_fields['x_unit'][idx]),
                'y_offset': float(trace_fields['y_offset'][idx]),
                'y_gain': float(trace_fields['y_gain'][idx]),
                'y_unit': str(trace_fields['y_unit'][idx]),
                'fmt': endian + fmt_code,
                'num_bytes': num_bytes,
            }
        )
    first_group = groups[0]
    return {
        'data_offset': int(public.get('DataOffset', 0)),
        'number_of_blocks': int(first_group.get('BlockNumber', 1)),
        'traces': traces,
    }


def _resolve_companion_file(path: Path, suffix: str) -> Path:
    direct = path.with_suffix(suffix)
    if direct.exists():
        return direct
    lower = path.with_suffix(suffix.lower())
    if lower.exists():
        return lower
    upper = path.with_suffix(suffix.upper())
    if upper.exists():
        return upper
    return direct


def _parse_yokogawa_hdr(hdr_path: Path) -> dict:
    sections: dict[str, dict[str, object]] = {}
    current = None
    for raw_line in hdr_path.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('$'):
            current = line[1:].strip()
            sections.setdefault(current, {})
            continue
        if current is None:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        key = parts[0]
        values = [_coerce_token(token) for token in parts[1:]]
        sections[current][key] = values[0] if len(values) == 1 else values
    return _build_yokogawa_header(sections)


def _decode_yokogawa_data_type(dtype_text: str) -> tuple[int, str]:
    kind = dtype_text[:1].upper()
    size = dtype_text[-1]
    table = {
        ('I', '1'): ('b', 1),
        ('I', '2'): ('h', 2),
        ('I', '4'): ('i', 4),
        ('I', '8'): ('q', 8),
        ('F', '4'): ('f', 4),
        ('F', '8'): ('d', 8),
    }
    if (kind, size) not in table:
        raise ValueError(f'暂不支持的 Yokogawa 数据类型：{dtype_text}')
    code, num_bytes = table[(kind, size)]
    if dtype_text[:2].upper() == 'IU':
        code = code.upper()
    return num_bytes, code


def _read_yokogawa_wvf(wvf_path: Path, header: dict) -> tuple[np.ndarray, np.ndarray]:
    traces = header['traces']
    block_count = header['number_of_blocks']
    data_offset = header['data_offset']
    if not traces:
        return np.zeros((0, 0), dtype=float), np.zeros(0, dtype=float)
    trace_arrays = []
    time_s = None
    raw = header.get('raw_bytes') if isinstance(header.get('raw_bytes'), (bytes, bytearray)) else wvf_path.read_bytes()
    for trace in traces:
        block_size = trace['block_size']
        dtype = np.dtype(trace['fmt'])
        sample_bytes = trace['num_bytes'] * block_size
        values = np.empty((block_count, block_size), dtype=float)
        for block_number in range(block_count):
            offset = data_offset + ((trace['index'] * block_count) + block_number) * sample_bytes
            chunk = raw[offset:offset + sample_bytes]
            if len(chunk) != sample_bytes:
                raise ValueError('WVF 文件长度与 HDR 描述不匹配。')
            values[block_number, :] = np.frombuffer(chunk, dtype=dtype, count=block_size).astype(float)
        scaled = values * trace['y_gain'] + trace['y_offset']
        trace_arrays.append(scaled.reshape(-1))
        if time_s is None:
            dt = trace['x_gain']
            time_s = trace['x_offset'] + np.arange(block_count * block_size, dtype=float) * dt
    analog_values = np.column_stack(trace_arrays) if trace_arrays else np.zeros((0, 0), dtype=float)
    return analog_values, time_s if time_s is not None else np.zeros(0, dtype=float)


def _coerce_token(token: str) -> object:
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return token


def _infer_nominal_frequency(time_s: np.ndarray) -> float:
    if time_s.size < 2:
        return 0.0
    sample_rate = 1.0 / max(float(np.median(np.diff(time_s))), 1e-12)
    for nominal in (50.0, 60.0):
        ratio = sample_rate / nominal
        if abs(ratio - round(ratio)) < 0.05:
            return nominal
    return 0.0


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
