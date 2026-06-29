# 测试与验证

sr3kit 在三个层面进行验证：快速单元测试、基于**真实 STARS SR3 文件**的集成测试，以及用于重构的基线核验框架。

```mermaid
flowchart LR
    A[DAT] --> B[STARS]
    B --> C[SR3]
    C --> D[SR3Indexer]
    D --> E[GridBuilder]
    E --> F[DataMapper]
```

## 运行测试套件

```bash
pip install -e ".[dev]"
pytest                       # 28 tests
```

测试套件（`test/`）包含：

- **单元测试**：使用模拟索引器和小型合成网格（`test_basic_grid_types.py`）。
- **几何工具函数测试**：针对可复用函数（`test_grid_geometry.py`），包括 `infer_levels` 的死锁检测。
- **`DataMapper` 聚合测试**：覆盖 `mean`/`sum`/`min`/`max`（`test_data_mapper.py`）。
- **真实 SR3 集成测试**：针对 LGR、DFN 和 convert-to-corner 案例，断言精确的单元计数、层级和属性有限性。

## 真实 SR3 测试样本

11 个测试案例位于 `test/<case>/`（DAT + SR3 + 日志），在 `tools/export_case_assets.py` 中注册：

| 案例 | grid_type | 说明 |
|---|---|---|
| `cartesian` | Cartesian | `*GRID *CART` |
| `vari` | Cartesian | `*GRID *VARI` |
| `radial` | Radial | `*GRID *RADIAL` |
| `lgr` | Cartesian | 单层 `*REFINE` |
| `lgr_nested` | Cartesian | 两层 `*REFINE`（层级 0/1/2） |
| `corner` | CornerPoint | `XCORNCRCN/...` 压缩角点 |
| `corner_coord` | CornerPoint | `COORD/ZCORN` 支柱(pillar)网格 |
| `tutorial_hm` | CornerPoint | 较大的真实角点模型 |
| `convert_to_corner` | CornerPoint | `*CONVERT-TO-CORNER-POINT` + DFN |
| `dfn_multi` | CornerPoint | 4 个 DFU |
| `dfn_refine` | CornerPoint | `*DFN_REFINE`；回退至 Cartesian 数组 |

## 验证流水线

`tools/export_case_assets.py` 端到端驱动每个已注册案例——构建、映射并导出资产——写入各案例的 `artifacts/` 目录以及顶层 `test/case_assets_summary.json`：

```bash
python tools/export_case_assets.py                       # all cases
python tools/export_case_assets.py --case convert_to_corner
python tools/export_timeseries_assets.py                 # well/time-series CSVs
```

参考结果（单元数 / 点数）：

| 案例 | 单元数 | 点数 |
|---|---:|---:|
| cartesian | 52 | 110 |
| vari | 110 | 768 |
| radial | 3752 | 6125 |
| lgr | 15 | 48 |
| lgr_nested | 36 | 98 |
| corner | 75 | 192 |
| corner_coord | 351 | 588 |
| tutorial_hm | 2616 | 3259 |
| convert_to_corner | 294 | 704 |
| dfn_multi | 294 | 704 |
| dfn_refine | 402 | 1012 |

## 基线核验框架

对于行为保持的重构，在变更**前**对每个案例生成指纹，变更后进行比对。指纹记录 `n_cells`、`n_points`、边界范围、全部单元数据数组，以及所有网格模式和 DFN 的映射 `PRES`，浮点数使用 `np.allclose` 比较，整数使用 `array_equal` 比较。

这正是网格策略重构和 `core → sr3kit` 重命名被证明在全部 11 个案例中产生逐位相同输出的方式。

!!! tip "经验法则"
    修改了网格构建或属性映射？请对真实测试样本进行验证，而不仅仅是模拟单元测试——风险最高的代码（LGR 原点、COORD/ZCORN、径向细分）只有真实文件才能有效测试。
