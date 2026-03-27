"""pandapower 模型文件解析：设备清单 + 拓扑连接摘要。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


def _coerce_table(value: Any) -> list[dict[str, Any]]:
    """把 pandapower JSON 中的表对象转成行字典列表。"""
    if isinstance(value, list):
        return [dict(v) for v in value if isinstance(v, dict)]
    if not isinstance(value, dict):
        return []

    # 常见结构：{"_object": "DataFrame", "columns": [...], "index": [...], "data": [[...], ...]}
    columns = value.get("columns")
    data = value.get("data")
    index = value.get("index", [])
    if isinstance(columns, list) and isinstance(data, list):
        rows: list[dict[str, Any]] = []
        for i, row in enumerate(data):
            item: dict[str, Any] = {}
            if isinstance(row, list):
                for c, col in enumerate(columns):
                    item[str(col)] = row[c] if c < len(row) else None
            elif isinstance(row, dict):
                item.update(row)
            if i < len(index):
                item.setdefault("index", index[i])
            else:
                item.setdefault("index", i)
            rows.append(item)
        return rows

    # 兼容列式结构：{"col1": [..], "col2": [..]}
    list_columns = {k: v for k, v in value.items() if isinstance(v, list)}
    if not list_columns:
        return []
    n = max((len(v) for v in list_columns.values()), default=0)
    rows = []
    for i in range(n):
        row = {k: (v[i] if i < len(v) else None) for k, v in list_columns.items()}
        row.setdefault("index", i)
        rows.append(row)
    return rows


def _bus_name_map(buses: list[dict[str, Any]]) -> dict[int, str]:
    names: dict[int, str] = {}
    for i, bus in enumerate(buses):
        idx_raw = bus.get("index", i)
        try:
            idx = int(idx_raw)
        except (TypeError, ValueError):
            idx = i
        name = bus.get("name")
        names[idx] = str(name) if name not in (None, "") else f"BUS{idx}"
    return names


def _edge(from_bus: Any, to_bus: Any, element_type: str, element_index: Any, in_service: Any, bus_names: dict[int, str]) -> JsonDict:
    try:
        fb = int(from_bus)
    except (TypeError, ValueError):
        fb = -1
    try:
        tb = int(to_bus)
    except (TypeError, ValueError):
        tb = -1
    return {
        "element_type": element_type,
        "element_index": element_index,
        "from_bus": fb,
        "to_bus": tb,
        "from_bus_name": bus_names.get(fb, f"BUS{fb}"),
        "to_bus_name": bus_names.get(tb, f"BUS{tb}"),
        "in_service": bool(True if in_service is None else in_service),
    }


def parse_pandapower_model_dict(net: JsonDict) -> JsonDict:
    buses = _coerce_table(net.get("bus"))
    lines = _coerce_table(net.get("line"))
    trafos = _coerce_table(net.get("trafo"))
    switches = _coerce_table(net.get("switch"))
    loads = _coerce_table(net.get("load"))
    gens = _coerce_table(net.get("gen"))
    sgens = _coerce_table(net.get("sgen"))
    ext_grids = _coerce_table(net.get("ext_grid"))

    bus_names = _bus_name_map(buses)
    edges: list[JsonDict] = []

    for line in lines:
        edges.append(
            _edge(
                line.get("from_bus"),
                line.get("to_bus"),
                "line",
                line.get("index"),
                line.get("in_service", True),
                bus_names,
            )
        )

    for trafo in trafos:
        edges.append(
            _edge(
                trafo.get("hv_bus"),
                trafo.get("lv_bus"),
                "trafo",
                trafo.get("index"),
                trafo.get("in_service", True),
                bus_names,
            )
        )

    # switch 的 bus + element 连接：仅处理 bus-bus 开关或 bus-line 的母线侧连接摘要
    for sw in switches:
        et = str(sw.get("et", ""))
        bus = sw.get("bus")
        target = sw.get("element")
        if et == "b":
            edges.append(_edge(bus, target, "switch_bus", sw.get("index"), not bool(sw.get("closed") is False), bus_names))

    adjacency: dict[str, list[str]] = {}
    for e in edges:
        a = e["from_bus_name"]
        b = e["to_bus_name"]
        adjacency.setdefault(a, [])
        adjacency.setdefault(b, [])
        if b not in adjacency[a]:
            adjacency[a].append(b)
        if a not in adjacency[b]:
            adjacency[b].append(a)

    inventory = {
        "bus": len(buses),
        "line": len(lines),
        "trafo": len(trafos),
        "switch": len(switches),
        "load": len(loads),
        "gen": len(gens),
        "sgen": len(sgens),
        "ext_grid": len(ext_grids),
    }

    return {
        "inventory": inventory,
        "buses": [
            {
                "index": int(b.get("index", i)) if str(b.get("index", i)).isdigit() else b.get("index", i),
                "name": bus_names.get(int(b.get("index", i)) if str(b.get("index", i)).isdigit() else i, f"BUS{i}"),
                "vn_kv": b.get("vn_kv"),
                "in_service": bool(b.get("in_service", True)),
            }
            for i, b in enumerate(buses)
        ],
        "loads": loads,
        "gens": gens,
        "ext_grids": ext_grids,
        "edges": edges,
        "adjacency": adjacency,
    }


def parse_pandapower_model_file(path: str | Path) -> JsonDict:
    file_path = Path(path)
    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("pandapower JSON 顶层必须是对象")
    return parse_pandapower_model_dict(data)


__all__ = [
    "parse_pandapower_model_dict",
    "parse_pandapower_model_file",
]
