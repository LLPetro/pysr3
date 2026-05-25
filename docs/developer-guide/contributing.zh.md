# 贡献指南

## 开发环境配置

```bash
git clone <repository-url>
cd pysr3
pip install -e ".[dev]"     # runtime + pytest
pytest                       # should report 28 passed
```

参与文档开发：

```bash
pip install -e ".[docs]"
mkdocs serve                 # live preview at http://127.0.0.1:8000
```

## 编码规范

- **语言：** 代码、注释和文档字符串均使用**英文**。文档字符串采用 **Google 风格**（`Args:`、`Returns:`、`Raises:`），以便 mkdocstrings 将其整洁地渲染至 [API 参考](../api/index.md)。
- **类型：** 为公开签名添加类型注解；API 页面将展示它们。
- **几何数学使用向量化 NumPy。** 避免在热路径上使用逐单元的 Python 循环；将可复用的数学运算放入 `grid/geometry.py`，而不是在策略中重复。
- **HDF5 访问留在 `SR3Indexer` 中。** 策略和 `DataMapper` 接收纯数组。
- **保持分发层(facade)轻量。** 新增几何逻辑应属于策略或工具函数，而非放入 `GridBuilder`。

## 添加新网格类型 { #adding-a-grid-type }

策略注册表使添加新类型成为纯增量操作——无需修改 `GridBuilder`：

```python
# pysr3/grid/my_family.py
import pyvista as pv
from .base import GridStrategy, register_strategy
from .geometry import active_cell_mask, infer_levels  # reuse helpers

@register_strategy("MyFamily")
class MyFamilyStrategy(GridStrategy):
    def build(self, data, time_step, grid_mode, include_inactive):
        # 1. read arrays from `data`
        # 2. assemble points/cells (prefer geometry helpers)
        # 3. stamp PropGlobalID, GlobalCellID, Level, I/J/K, ParentI/J/K
        grid = pv.UnstructuredGrid(...)
        return grid
```

然后在 `pysr3/grid_builder.py` 中导入它以触发注册副作用：

```python
from .grid import my_family as _my_family  # noqa: F401
```

此后 `available_grid_types()` 将包含 `"MyFamily"`。如果新族位于新子包中，请将其添加至 `pyproject.toml` 的包列表，并在[网格类型](../user-guide/concepts/grid-types.md)下进行文档说明。

## 验证变更

1. `pytest` — 必须保持全部通过（28 个测试）。
2. 对于网格/映射变更，运行[基线核验框架与真实 SR3 流水线](testing.md)，确认输出不变（或有意更新测试样本）。
3. `mkdocs build --strict` — 文档构建不得产生任何警告。

## Pull Request 规范

- 保持差异聚焦；将机械性变更（重命名）与行为变更分开提交。
- 在 PR 中说明输出是否预期为逐位相同，以及您是如何验证的。
