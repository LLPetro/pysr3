# 网格策略内部机制

`GridBuilder` 是一个分发层(facade)。几何逻辑位于 `sr3kit/grid/`，其组织方式使每个网格族相互隔离，共享的数学运算得到复用。

## 策略注册表

`grid/base.py` 定义了一个抽象基类和一个注册表：

```python
class GridStrategy(ABC):
    grid_type: str = ""
    def __init__(self, indexer): ...
    @abstractmethod
    def build(self, data, time_step, grid_mode, include_inactive) -> pv.UnstructuredGrid: ...
```

`@register_strategy("Cartesian")` 装饰器以其公开名称注册该类。`GridBuilder.build()` 解析策略，一次性获取 `get_grid_data`，调用 `strategy.build(...)`，然后合并重合点：

```python
strategy = get_strategy(grid_type, self.indexer)
data = self.indexer.get_grid_data(time_step)
grid = strategy.build(data=data, time_step=time_step,
                      grid_mode=grid_mode, include_inactive=include_inactive)
# ... grid.clean(...) if merge_points
```

策略是纯变换：它们接收已读取的 `data` 字典，从不接触文件。因此添加新网格族是纯增量操作——参见[贡献指南](contributing.md#adding-a-grid-type)。

## 共享几何工具函数

`grid/geometry.py` 包含可复用的纯 NumPy 构建模块。它们接收纯数组，因此可在隔离环境中进行单元测试（`test/test_grid_geometry.py`）。

| 工具函数 | 用途 |
|---|---|
| `infer_levels(icstpb, igntnc)` | 每个单元的 LGR 层级；遇到循环/无效父指针时报错 |
| `refined_parent_ids(icstpb, igntnc)` | 被 LGR 子单元替换的父单元 |
| `grid_mode_keep_mask(mode, level, icstpb, igntnc)` | mixed/refined/levelN 过滤掩码 |
| `active_cell_mask(icstps, data)` | `ICSTPS > 0` **且** `IPSTAC != 0` |
| `parse_kdir(data, default)` | 解码 `KDIR` 属性 |
| `hexahedra_from_corners(corners)` | 从 8 个角点数组生成分解六面体的 `(cells, types, points)` |
| `polygon_cells(n, n_verts, type)` | 连续顶点多边形的 VTK 连接关系 |
| `segment_ijk(igntid, jd, kd, nc, total)` | 所有线段的每单元局部 I/J/K |
| `compute_parent_ijk(icstpb, level, i, j, k)` | 细化单元的父 I/J/K |

`infer_levels` 之所以放在此处，正是为了让 `GridBuilder` 和 `DataMapper` 共享同一实现。参见 [API 参考](../api/grid-geometry.md)。

## Cartesian / VARI

构建**分解六面体**网格：每个单元展开为 8 个显式角点，因此可变块尺寸和 LGR 细分无需特殊处理；重合角点随后由分发层(facade)合并。`BLOCKDEPTH`（正值向下）映射为 Z-up 坐标（`Z = -depth`）。

!!! warning "LGR 原点假设"
    对于 LGR 线段，子单元坐标以细化父单元的左下角（父单元 `xmin`/`ymin` 的 `min`）为锚点，再按累积 `BLOCKSIZE` 平铺。这假设**一个线段仅细化单个连续的父单元块**。将多个不连续父单元分组的线段不受支持。`test/test_basic_grid_types.py::test_lgr_children_tile_parent_footprint` 固定了支持的单父单元情形。

## 径向网格

从 `BLOCKSIZE`（Δr, 弧长, Δz）和 `WELLRADIUS` 重建楔形：`r` 由累积 Δr 得出，`dθ = arc_length / r_center`，`θ` 由累积 `dθ` 得出，Z 由累积 Δz 及 `KDIR` 方向决定。宽楔形将被**细分**以渲染为平滑弧形（`MAX_ANGLE_DEG = 5°`），通过 `np.repeat` 向量化扩展。第一环（I=0）折叠所有 J 列，因此这些重复项会被过滤掉。

## 角点网格

检测编码方式并生成 `(nodes, blocks)`：

1. `NODES` + `BLOCKS` — 直接使用。
2. `XCORNCRCN/YCORNCRCN/ZCORNCRCN` — `_crcn_to_nodes_blocks` 构建结构化连接关系（按线段向量化）。
3. `COORD` + `ZCORN` — `_coord_zcorn_to_nodes_blocks` 沿每根支柱(pillar)从角点 Z 插值 XY（向量化），并对 Z 取反以用于显示。
4. 以上均不存在但 Cartesian 数组存在 — **回退**至 `CartesianStrategy`（例如部分 `DFN_REFINE` convert-to-corner 案例）。

当没有引用节点 0 时，块索引从 1 为基转换为 0 为基。

## DFN

`grid/dfn.py` 构建 QUAD 面（通过 `polygon_cells`），独立于矩阵层次结构：

- `build_dfn_units` — 原始 DFU 四边形（`DFUCO*`），含 `DFUAPT`/`DFUPERM`（若存在）。
- `build_dfn_segments` — 嵌入线段四边形（`SGCOR*`），由 `IPSTPS` 和 `IPSTAC` 过滤，携带 `PropGlobalID` 和宿主反向引用（`HostGlobalCellID`、`Host I/J/K` 通过 `segment_ijk` 计算）。

当文件不含 DFN 数组时，两者均返回空的 `UnstructuredGrid`。
