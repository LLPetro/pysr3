# 命名与术语表

本页是 pysr3 词汇的唯一权威：标识符、参数名、字典键、docstring、日志消息、散文均以此为准。

命名漂移的代价很快显现：同一个概念出现三种写法，会让 grep 跑空、让每个评审者在脑中维护翻译表。遇到分歧时，请优先使用本页中的规范名，即使近义词更短或读起来更顺。

## 时间步（time step）术语

CMG SR3 文件中包含三种相关但不同的"步"概念：

| 概念 | 规范单数 | 规范复数 | 说明 |
|---|---|---|---|
| 整数步索引（单值） | `time_step` | — | 用作每个返回值方法的参数。不要使用 `ts`、`timestep`（合写）、`step_idx`。 |
| 自模拟起始的浮点偏移（天） | `time_offset`（`get_time_offset`） | — | DataFrame 中的数值列叫 `Time`。 |
| 步对应的日期字符串 | `step_date`（`get_step_date`） | — | DataFrame 列保留为 `Date`。 |
| `/SpatialProperties/<step>` 中所有步 | — | `spatial_time_steps` | 方法：`get_spatial_time_steps()`。 |
| 上述中仅写入 `/GRID` 的子集 | `grid_time_step`（`get_nearest_grid_time_step`） | `grid_time_steps`（`get_grid_time_steps`） | 几何通常只写少数几个步。 |
| 单个 TimeSeries 实体（井/组/段……）的时间轴 | — | `time_steps`（`get_timeseries_data`/`get_well_data` 参数） | 在 `get_timeseries_info()` 上以 `info['time_steps']` 存储。 |
| 零填充步**字符串**（`"000000"`，用于构造 HDF5 路径） | `step_key` | `spatial_step_keys` | 仅供内部使用，不暴露给用户。 |
| SR3 步整数对应的 DataFrame 列 | `TimeIndex` | — | 已稳定，不要重命名。 |

**代码约定：**
- 参数与局部变量：`time_step`（单数 int）、`time_steps`（int 列表）。
- 聚合中层级下降的循环变量：`level_idx`（不要用 `lvl`）。
- 当次调用解析得到的网格步：`grid_time_step`。
- 浮点对齐过程中的中间值：`best_step`（不要用 `best_ts`）。

## 属性与变量标识

CMG 把 `/General/NameRecordTable` 的列称为 "keywords"。pysr3 区分两种类型：

| 概念 | 规范名 | 出现位置 |
|---|---|---|
| 空间属性 keyword（`PRES`、`SO`、`MODBVOL`、`BLOCKPVOL`……） | `keyword` | `get_property_data(keyword, ...)`、`get_property_info(keyword, ...)`、`map_prop(keywords=...)`、`get_unit(keyword, ...)`、`convert(keyword, ...)`。DataFrame 列：`Keyword`。 |
| TimeSeries 变量 keyword（`BHP`、`OILRATSC`……） | `variable` | `get_timeseries_data(variables=[...])`、`get_well_data(variables=[...])`。DataFrame 列：`Variable`。 |
| TimeSeries origin（井名、组名……） | `origin`（抽象）/`well`（具体） | `get_timeseries_data(origins=[...])`、`get_well_data(wells=[...])`。列：`Origin`/`Well`。 |

切勿使用 `name`、`prop_name`、`var_name` 或 `kw` 命名这些标识。它们太泛或与 Python 内建/局部上下文冲突。

## 储层单元（cell）术语

| 概念 | pysr3 散文中的规范 | CMG/SR3 约定 |
|---|---|---|
| 离散化储层体积 | **cell**（`n_cells`、`GlobalCellID`、`active_cell_mask`、`total_cells`） | "block"（`BLOCKSIZE`、`BLOCKDEPTH`、`BLOCKPVOL`、`MODBVOL` = "Modified Block Volume"） |

**规则：** pysr3 的 docstring、注释、散文中一律说 **cell**。PyVista/VTK 同样使用 cell，与下游表示一致。**例外：** 字面引用 CMG keyword 或 NRT Long Name 时保留原文（例如 `MODBVOL` 仍称为 "Modified Block Volume"，不改写为 "Modified Cell Volume" —— 这是 CMG 命名，不应重写）。

`concepts/volumes.md` 和 `concepts/dfn-vs-lgr.md` 各有一段词汇对照说明此等价。

## 子网格（sub-grid）与 DFN 段（segment）

清理之前"segment"一词曾有三种含义：

1. **矩阵子网格** —— `IGNTGT`/`IGNTID/JD/KD` 中的一项（顶层矩阵 + 各 LGR 细化）。规范名：**subgrid**。
   标识：`subgrid_ijk()`、`subgrid_idx`、`n_subgrids`。
2. **DFN 平面四边形** —— 离散裂缝网络中的一片裂缝。规范名：**segment**（保留）。
   标识：`build_dfn_segments`、`DFNSegmentID`。
3. CornerPoint 连接块 —— 以散文形式称作"connectivity block"；不需要专属标识。

在 `grid/dfn.py` 之外，"segment" 不应作为 Python 标识符出现；选 "subgrid" 才安全。

## LGR 相关标识

| 概念 | 规范名 |
|---|---|
| LGR 细化深度（逐单元 `int`） | `level`（数组）、`max_level`（标量）、`level_idx`（循环变量） |
| 显示模式字符串（`grid_mode=`） | `"mixed"`、`"refined"`、`"level0"`、`"level1"`…… |
| 0 基的 CS 索引，标识已被 LGR 子单元替换的父单元 | `refined_parents`（不要用 `rp`） |
| `grid_mode` 的布尔保留掩码辅助函数 | `grid_mode_keep_mask(...)`（不是 `display_mode_keep_mask`） |
| `GridBuilder.build` 的 `keep_refined_parents=True` 标志 | 不变 |
| 逐单元的子网格指针（ICSTCG） | `icstcg` 参数；散文中可读作 "child sub-grid" |

## 属性槽（prop slot）标识

| 概念 | 规范名 |
|---|---|
| `ICSTPS - 1`（属性数组的 0 基索引） | `prop_slots`（复数）、`prop_slot`（单数） |
| 上述中位于有效范围的子集 | `valid_prop_slots` |
| 构建网格上的公开 cell_data 数组名 | `PropGlobalID`（保留，磁盘上已稳定） |

## 单位子系统

| 概念 | 规范名 |
|---|---|
| 每个返回值方法的 `to_unit=` 参数 | `to_unit` |
| 每个维度的默认输出单位（`UnitsTable.Output Unit`） | `output_unit`（`name_records[k]`、`units[i]` 的字典键） |
| 每个维度的 CMG 内部单位 | `internal_unit` |
| DataFrame 列标签 | `Unit` |
| `agg_method` 加权变体 | `'bulk_volume_mean'`（MODBVOL 加权）与 `'pore_volume_mean'`（BLOCKPVOL 加权） |

## 公共方法前缀约定

`get_X` 是 `SR3Indexer` 上的主流模式。**所有返回值的访问器**都应采用该模式。仅保留**执行动作**的方法用动词前缀（build、convert、detect、register、close）。

| 风格 | 示例 |
|---|---|
| `get_X`（访问器） | `get_grid_data`、`get_grid_array`、`get_property_data`、`get_property_info`、`get_available_properties`、`get_grid_time_steps`、`get_spatial_time_steps`、`get_nearest_grid_time_step`、`get_time_offset`、`get_step_date`、`get_unit`、`get_well_data`、`get_timeseries_data`、`get_timeseries_info`、`get_timeseries_entities` |
| 动词前缀（动作） | `build`、`build_dfn_segments`、`build_dfn_units`、`convert`、`detect_grid_type`、`register_strategy`、`close` |
| 模块级纯函数 | `available_grid_types()`（无 `get_`，因为它不是 indexer/mapper/builder 上的方法） |

## 散文约定

| 概念 | `.md` 中的规范 | 避免 |
|---|---|---|
| 时间步（名词） | "time step" | 合写 "timestep"、"Time Step" |
| 时间步（形容词） | "time-step"（带连字符） | 用作形容词时不带连字符的 "time step" |
| 时间序列（名词） | "time series" | "time-series"（带连字符）、"timeseries"（合写） |
| 时间序列（形容词） | "time-series"（带连字符） | 用作形容词时不带连字符的 "time series" |
| HDF5 组名 | `` `TimeSeries` ``（字面 `/TimeSeries`） | 等宽字体里写 "Time Series" |
| 文件路径中的组件 | `timeseries`（一词、小写）—— 保持现有磁盘路径 | 重命名目录 |
| 标题与表格中的网格家族 | `Cartesian`、`CornerPoint`、`Radial` | "Corner-point"、"corner-point"、"RADIAL" |
| 叙述性散文中的网格家族 | "corner-point grid"、"the radial grid" | 大小写不一致 |
| LGR | `LGR`（全大写）；每页首次出现展开为 "local grid refinement" | "lgr" |
| DFN | `DFN`（全大写）；每页首次出现展开为 "discrete fracture network" | "dfn" |

中文（`*.zh.md`）译文沿用相同的英文技术标识符；仅翻译自然语言部分。中文"时间步"对应 "time step"；"时间序列"对应 "time series"。

## 不确定时

- 如果本页规范名不适合某个新概念，**扩充本页**，不要引入一次性变体。
- 如果觉得某个现有标识值得重命名，请先在 PR 中讨论 —— 跨文件的一致性比任何单一名字"更好"更重要。
- 本页中的名字有意倾向显式而非简短。`time_step` 比 `ts` 更优，因为 `ts` 含义太多（TypeScript、tablespoon、time series……），也更难 grep。
