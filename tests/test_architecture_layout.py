from __future__ import annotations

import json
from pathlib import Path


def test_powertool_boundary_folder_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    pt = root / "PowerTool"
    assert (pt / "README.md").exists()
    assert (pt / "main.py").exists()
    assert (pt / "core_manifest.json").exists()


def test_core_manifest_has_expected_keys() -> None:
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "PowerTool" / "core_manifest.json").read_text(encoding="utf-8"))
    assert "core_entry" in data
    assert "gui" in data
    assert isinstance(data.get("core_modules"), list)
    assert "power_tool_smib.py" in data["core_modules"]
