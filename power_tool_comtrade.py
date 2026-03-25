from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
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


def _read_text_with_fallback_encodings(path: Path, encodings: tuple[str, ...] = ('utf-8-sig', 'gb2312')) -> str:
    last_error: UnicodeDecodeError | None = None
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    names = ', '.join(encodings)
    raise ValueError(f'文件编码不受支持：{path.name}（已尝试：{names}）') from last_error


def parse_cfg(cfg_path: str | Path) -> dict:
    path = Path(cfg_path)
    lines = [line.strip() for line in _read_text_with_fallback_encodings(path).splitlines() if line.strip()]
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
    if suffix == '.mat':
        return parse_mat_waveform(source_path)
    if suffix in {'.hdr', '.wvf', '.wdf'}:
        return parse_yokogawa_waveform(source_path)
    raise ValueError(f'暂不支持的录波文件类型：{source_path.suffix or "(无扩展名)"}')


def _decode_mat_v4_mopt(mopt: int) -> tuple[str, np.dtype]:
    platform = mopt // 1000
    precision = (mopt // 10) % 10
    data_type = mopt % 10
    if platform == 0:
        endian = '<'
    elif platform == 1:
        endian = '>'
    else:
        raise ValueError('仅支持 little/big endian 的 MATLAB v4 文件。')
    if precision not in (0, 1):
        raise ValueError('仅支持 full matrix 的 MATLAB v4 文件。')
    type_map = {
        0: np.float64,
        1: np.float32,
        2: np.int32,
        3: np.int16,
        4: np.uint16,
        5: np.uint8,
    }
    if data_type not in type_map:
        raise ValueError(f'不支持的 MATLAB v4 数据类型标记：{data_type}')
    return endian, np.dtype(type_map[data_type]).newbyteorder(endian)


def _read_mat_level4(path: Path) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    data = path.read_bytes()
    pos = 0
    while pos + 20 <= len(data):
        mopt, mrows, ncols, imagf, namelen = struct.unpack_from('<iiiii', data, pos)
        if mrows <= 0 or ncols <= 0 or namelen <= 0:
            break
        pos += 20
        if pos + namelen > len(data):
            break
        name_raw = data[pos:pos + namelen]
        pos += namelen
        name = name_raw.split(b'\x00', 1)[0].decode('utf-8', errors='ignore').strip() or f'var{len(out) + 1}'
        if imagf != 0:
            raise ValueError('暂不支持复数 MATLAB v4 变量。')
        endian, dtype = _decode_mat_v4_mopt(mopt)
        item_count = mrows * ncols
        item_size = dtype.itemsize
        total_size = item_count * item_size
        if pos + total_size > len(data):
            break
        arr = np.frombuffer(data, dtype=dtype, count=item_count, offset=pos).copy()
        pos += total_size
        if endian != '<':
            arr = arr.byteswap().view(arr.dtype.newbyteorder('<'))
        out[name] = arr.reshape((mrows, ncols), order='F')
    if not out:
        raise ValueError('未识别到 MATLAB v4 变量，请确认 .mat 文件格式。')
    return out


def _mat5_pad(length: int) -> int:
    return (8 - (length % 8)) % 8


def _read_mat_level5(path: Path) -> dict[str, np.ndarray]:
    data = path.read_bytes()
    if len(data) < 128:
        raise ValueError('MATLAB v5 文件头长度不足。')
    if data[126:128] == b'IM':
        endian = '<'
    elif data[126:128] == b'MI':
        endian = '>'
    else:
        raise ValueError('无法识别 MATLAB v5 字节序。')

    miINT8 = 1
    miUINT16 = 4
    miINT32 = 5
    miUINT32 = 6
    miDOUBLE = 9
    miMATRIX = 14
    mxCHAR_CLASS = 4

    pos = 128
    out: dict[str, np.ndarray] = {}
    while pos + 8 <= len(data):
        dt, nbytes = struct.unpack_from(f'{endian}II', data, pos)
        pos += 8
        if nbytes == 0:
            break
        if pos + nbytes > len(data):
            break
        payload = data[pos:pos + nbytes]
        pos += nbytes + _mat5_pad(nbytes)
        if dt != miMATRIX:
            continue

        cur = 0
        # array flags
        sdt, sn = struct.unpack_from(f'{endian}II', payload, cur)
        cur += 8
        flags = payload[cur:cur + sn]
        cur += sn + _mat5_pad(sn)
        if sdt != miUINT32 or len(flags) < 8:
            continue
        mx_class = struct.unpack_from(f'{endian}I', flags, 0)[0] & 0xFF

        # dimensions
        sdt, sn = struct.unpack_from(f'{endian}II', payload, cur)
        cur += 8
        dims_raw = payload[cur:cur + sn]
        cur += sn + _mat5_pad(sn)
        if sdt != miINT32 or len(dims_raw) < 8:
            continue
        dims = struct.unpack_from(f'{endian}{sn // 4}i', dims_raw, 0)
        mrows = int(dims[0]) if dims else 0
        ncols = int(dims[1]) if len(dims) > 1 else 1
        if mrows <= 0 or ncols <= 0:
            continue

        # name
        sdt, sn = struct.unpack_from(f'{endian}II', payload, cur)
        cur += 8
        name_raw = payload[cur:cur + sn]
        cur += sn + _mat5_pad(sn)
        if sdt != miINT8:
            continue
        name = name_raw.decode('utf-8', errors='ignore').strip('\x00').strip() or f'var{len(out)+1}'

        # real data
        sdt, sn = struct.unpack_from(f'{endian}II', payload, cur)
        cur += 8
        real_raw = payload[cur:cur + sn]
        if mx_class == mxCHAR_CLASS and sdt == miUINT16:
            arr = np.frombuffer(real_raw, dtype=np.dtype(np.uint16).newbyteorder(endian)).copy()
            out[name] = arr.reshape((mrows, ncols), order='F')
            continue
        if sdt == miDOUBLE:
            arr = np.frombuffer(real_raw, dtype=np.dtype(np.float64).newbyteorder(endian)).copy()
            out[name] = arr.reshape((mrows, ncols), order='F')
    if not out:
        raise ValueError('未识别到 MATLAB v5 变量。')
    return out


def _encode_names_to_uint16(names: list[str]) -> np.ndarray:
    width = max((len(name) for name in names), default=1)
    matrix = np.zeros((len(names), width), dtype=np.uint16)
    for i, name in enumerate(names):
        for j, ch in enumerate(name[:width]):
            matrix[i, j] = ord(ch)
    return matrix


def _decode_uint16_names(matrix: np.ndarray) -> list[str]:
    arr = np.asarray(matrix)
    if arr.ndim == 1:
        arr = arr.reshape((1, -1))
    names: list[str] = []
    for row in arr:
        chars = ''.join(chr(int(v)) for v in row if int(v) > 0)
        names.append(chars.strip() or f'CH{len(names)+1}')
    return names


def parse_mat_waveform(path: str | Path) -> ComtradeRecord:
    source_path = Path(path)
    try:
        vars_map = _read_mat_level5(source_path)
    except Exception:
        vars_map = _read_mat_level4(source_path)
    normalized = {k.lower(): v for k, v in vars_map.items()}
    time = None
    for key in ('time_s', 'time', 't', 'x'):
        if key in normalized:
            time = np.asarray(normalized[key], dtype=float).reshape(-1)
            break
    if time is None:
        raise ValueError('MATLAB 文件缺少时间变量（time_s/time/t/x）。')

    analog = None
    for key in ('analog_values', 'signals', 'data', 'y'):
        if key in normalized:
            analog = np.asarray(normalized[key], dtype=float)
            break
    if analog is None:
        analog = np.asarray(next(iter(vars_map.values())), dtype=float)
    if analog.ndim == 1:
        analog = analog.reshape((-1, 1))
    if analog.shape[0] != time.size and analog.shape[1] == time.size:
        analog = analog.T
    if analog.shape[0] != time.size:
        raise ValueError('MATLAB 文件中的数据长度与时间轴不一致。')

    names_var = normalized.get('channel_names')
    units_var = normalized.get('channel_units')
    if names_var is not None:
        names = _decode_uint16_names(names_var)
    else:
        names = [f'CH{i+1}' for i in range(analog.shape[1])]
    if units_var is not None:
        units = _decode_uint16_names(units_var)
    else:
        units = ['' for _ in range(analog.shape[1])]
    if len(names) < analog.shape[1]:
        names.extend(f'CH{i+1}' for i in range(len(names), analog.shape[1]))
    if len(units) < analog.shape[1]:
        units.extend('' for _ in range(len(units), analog.shape[1]))

    channels = [
        ComtradeChannel(index=i + 1, name=names[i], phase='', unit=units[i], a=1.0, b=0.0)
        for i in range(analog.shape[1])
    ]
    sample_rate = 0.0
    if time.size > 1:
        dt = np.median(np.diff(time))
        if dt > 0:
            sample_rate = float(1.0 / dt)
    return ComtradeRecord(
        station_name=source_path.stem,
        device_id='MATLAB',
        revision='MAT',
        frequency_hz=50.0,
        sample_rates=[(sample_rate, int(time.size))] if sample_rate > 0 else [],
        analog_channels=channels,
        digital_channel_names=[],
        time_s=np.asarray(time, dtype=float),
        analog_values=np.asarray(analog, dtype=float),
        digital_values=np.zeros((time.size, 0), dtype=np.int16),
        file_type='MATLAB',
        cfg_path=source_path,
        dat_path=source_path,
    )


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
    for raw_line in _read_text_with_fallback_encodings(hdr_path).splitlines():
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
    for raw in _read_text_with_fallback_encodings(dat_path).splitlines():
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


def _write_mat_level4(path: Path, variables: dict[str, np.ndarray]) -> None:
    with path.open('wb') as f:
        for name, arr in variables.items():
            name_bytes = name.encode('utf-8') + b'\x00'
            mat = np.asarray(arr)
            if mat.ndim == 1:
                mat = mat.reshape((-1, 1))
            mat = np.asarray(mat, dtype=np.float64 if mat.dtype.kind == 'f' else mat.dtype)
            dtype_to_t = {
                np.dtype(np.float64): 0,
                np.dtype(np.float32): 1,
                np.dtype(np.int32): 2,
                np.dtype(np.int16): 3,
                np.dtype(np.uint16): 4,
                np.dtype(np.uint8): 5,
            }
            dtype_key = np.dtype(mat.dtype).newbyteorder('=')
            if dtype_key not in dtype_to_t:
                mat = mat.astype(np.float64)
                dtype_key = np.dtype(np.float64)
            mopt = dtype_to_t[dtype_key]
            mrows, ncols = int(mat.shape[0]), int(mat.shape[1])
            header = struct.pack('<iiiii', mopt, mrows, ncols, 0, len(name_bytes))
            f.write(header)
            f.write(name_bytes)
            f.write(np.asfortranarray(mat).tobytes(order='F'))


def _mat5_data_element(data_type: int, payload: bytes) -> bytes:
    return struct.pack('<II', data_type, len(payload)) + payload + (b'\x00' * _mat5_pad(len(payload)))


def _pack_mat5_variable(name: str, arr: np.ndarray) -> bytes:
    miINT8 = 1
    miUINT16 = 4
    miINT32 = 5
    miUINT32 = 6
    miDOUBLE = 9
    miMATRIX = 14
    mxDOUBLE_CLASS = 6
    mxCHAR_CLASS = 4

    mat = np.asarray(arr)
    if mat.ndim == 1:
        mat = mat.reshape((-1, 1))
    name_bytes = name.encode('utf-8')
    dims = np.array(mat.shape, dtype=np.int32).tobytes(order='C')
    if mat.dtype == np.uint16:
        mx_class = mxCHAR_CLASS
        data_type = miUINT16
        payload = np.asfortranarray(mat.astype(np.uint16)).tobytes(order='F')
    else:
        mx_class = mxDOUBLE_CLASS
        data_type = miDOUBLE
        payload = np.asfortranarray(mat.astype(np.float64)).tobytes(order='F')

    flags = struct.pack('<II', mx_class, 0)
    content = b''.join([
        _mat5_data_element(miUINT32, flags),
        _mat5_data_element(miINT32, dims),
        _mat5_data_element(miINT8, name_bytes),
        _mat5_data_element(data_type, payload),
    ])
    return _mat5_data_element(miMATRIX, content)


def _write_mat_level5(path: Path, variables: dict[str, np.ndarray]) -> None:
    header_text = b'MATLAB 5.0 MAT-file, Platform: GLNXA64, Created by power_tool'
    header = header_text.ljust(116, b' ') + (b'\x00' * 8) + struct.pack('<H', 0x0100) + b'IM'
    with path.open('wb') as f:
        f.write(header)
        for name, arr in variables.items():
            f.write(_pack_mat5_variable(name, arr))


def export_waveform_record(
    record: ComtradeRecord,
    channel_indices: list[int],
    output_path: str | Path,
    export_format: str,
) -> list[Path]:
    if not channel_indices:
        raise ValueError('请至少选择一个通道用于导出。')
    selected = sorted({int(i) for i in channel_indices if 0 <= int(i) < len(record.analog_channels)})
    if not selected:
        raise ValueError('未找到可导出的有效通道。')
    out = Path(output_path)
    fmt = export_format.strip().upper()
    time = np.asarray(record.time_s, dtype=float).reshape(-1)
    data = np.asarray(record.analog_values[:, selected], dtype=float)
    channels = [record.analog_channels[i] for i in selected]

    if fmt == 'CSV':
        if out.suffix.lower() != '.csv':
            out = out.with_suffix('.csv')
        with out.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            header = ['time_s'] + [f"{ch.name} [{ch.unit}]" if ch.unit else ch.name for ch in channels]
            writer.writerow(header)
            for idx in range(time.size):
                writer.writerow([f'{time[idx]:.12g}', *[f'{v:.12g}' for v in data[idx, :]]])
        return [out]

    if fmt == 'MATLAB':
        if out.suffix.lower() != '.mat':
            out = out.with_suffix('.mat')
        vars_map: dict[str, np.ndarray] = {
            'time_s': time.reshape((-1, 1)),
            'analog_values': data,
            'channel_names': _encode_names_to_uint16([ch.name for ch in channels]),
            'channel_units': _encode_names_to_uint16([ch.unit for ch in channels]),
        }
        _write_mat_level5(out, vars_map)
        return [out]

    if fmt == 'COMTRADE':
        base = out.with_suffix('') if out.suffix else out
        cfg_path = base.with_suffix('.cfg')
        dat_path = base.with_suffix('.dat')
        sample_rate = estimate_sampling_rate(record)
        if sample_rate <= 0:
            sample_rate = 1.0
        cfg_lines = [
            f"{record.station_name or 'STATION'},{record.device_id or 'DEVICE'},1999",
            f"{len(channels)},{len(channels)}A,0D",
        ]
        for idx, ch in enumerate(channels, start=1):
            cfg_lines.append(f"{idx},{ch.name},{ch.phase},,{ch.unit or 'pu'},1,0,0,-999999,999999,1,1,P")
        cfg_lines.extend([
            f"{record.frequency_hz or 50.0:.6g}",
            "1",
            f"{sample_rate:.12g},{len(time)}",
            "01/01/2026,00:00:00.000000",
            "01/01/2026,00:00:00.000000",
            "ASCII",
            "1",
        ])
        cfg_path.write_text('\n'.join(cfg_lines) + '\n', encoding='utf-8')
        with dat_path.open('w', encoding='utf-8') as f:
            for i in range(time.size):
                row = [str(i + 1), f"{time[i] * 1e6:.0f}"]
                row.extend(f"{float(v):.12g}" for v in data[i, :])
                f.write(','.join(row) + '\n')
        return [cfg_path, dat_path]

    raise ValueError('导出格式仅支持 COMTRADE、CSV、MATLAB。')
