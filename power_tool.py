
# -*- coding: utf-8 -*-
"""项目入口与兼容导出层。

- 直接运行：`python power_tool.py`
- 作为库使用：建议从各 `power_tool_*.py` 模块导入
"""

from __future__ import annotations

from power_tool_common import *  # noqa: F401,F403
from power_tool_params import *  # noqa: F401,F403
from power_tool_approximations import *  # noqa: F401,F403
from power_tool_faults import *  # noqa: F401,F403
from power_tool_stability import *  # noqa: F401,F403
from power_tool_smib import *  # noqa: F401,F403
from power_tool_line_geometry import *  # noqa: F401,F403
from power_tool_loop_closure import *  # noqa: F401,F403
from power_tool_avc import *  # noqa: F401,F403
from power_tool_ai import *  # noqa: F401,F403


def main() -> None:
    from power_tool_gui import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
