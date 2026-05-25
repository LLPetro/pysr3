# 网格案例

以下为每种受支持网格族的可直接复制代码片段，使用 `test/` 目录下捆绑的真实 STARS SR3 文件。

## Cartesian

```python
from pysr3 import SR3Indexer, GridBuilder

with SR3Indexer("test/cartesian/cartesian.sr3") as sr3:
    grid = GridBuilder(sr3).build("Cartesian")

print(grid.n_cells)
```

## VARI

`VARI` 使用 `Cartesian` 策略构建。

```python
with SR3Indexer("test/vari/vari.sr3") as sr3:
    grid = GridBuilder(sr3).build("Cartesian")
```

## Radial

```python
with SR3Indexer("test/radial/radial.sr3") as sr3:
    grid = GridBuilder(sr3).build("Radial")
```

## LGR

```python
with SR3Indexer("test/lgr/lgr.sr3") as sr3:
    builder = GridBuilder(sr3)
    mixed   = builder.build("Cartesian", grid_mode="mixed")
    refined = builder.build("Cartesian", grid_mode="refined")
    level0  = builder.build("Cartesian", grid_mode="level0")
```

嵌套（多层）LGR：

```python
with SR3Indexer("test/lgr_nested/lgr_nested.sr3", list_props_ts=None) as sr3:
    builder = GridBuilder(sr3)
    mixed  = builder.build("Cartesian", grid_mode="mixed")
    level2 = builder.build("Cartesian", grid_mode="level2")
```

## 角点网格

```python
with SR3Indexer("test/corner_coord/corner_coord.sr3") as sr3:
    grid = GridBuilder(sr3).build("CornerPoint")
```

更大、更贴近实际的角点网格模型：

```python
with SR3Indexer("test/50the_datafile/tutorial_hm.sr3") as sr3:
    grid = GridBuilder(sr3).build("CornerPoint")
```

## 转换为角点 + DFN

```python
with SR3Indexer("test/convert_to_corner/convert_to_corner.sr3", list_props_ts=None) as sr3:
    builder = GridBuilder(sr3)
    matrix       = builder.build("CornerPoint")
    dfn_segments = builder.build_dfn_segments()
    dfn_units    = builder.build_dfn_units()
```

多个 DFU 与 `DFN_REFINE`：

```python
with SR3Indexer("test/dfn_multi/dfn_multi.sr3", list_props_ts=None) as sr3:
    builder = GridBuilder(sr3)
    dfn_segments = builder.build_dfn_segments()
    dfn_units    = builder.build_dfn_units()

with SR3Indexer("test/dfn_refine/dfn_refine.sr3", list_props_ts=None) as sr3:
    builder = GridBuilder(sr3)
    matrix         = builder.build("CornerPoint")           # falls back to Cartesian arrays
    active_segs    = builder.build_dfn_segments()
    all_segs       = builder.build_dfn_segments(include_inactive=True)
```

## 属性映射

```python
from pysr3 import SR3Indexer, GridBuilder, DataMapper

with SR3Indexer("test/cartesian/cartesian.sr3", list_props_ts=None) as sr3:
    grid = GridBuilder(sr3).build("Cartesian")
    df = DataMapper(sr3).map_prop(grid, ["PRES", "SO"], [0])

print(df.columns)
print(df.head())
```

## 导出资产

```bash
python tools/export_case_assets.py
python tools/export_case_assets.py --case tutorial_hm --scale-z 10
```

每个案例生成以下文件（DFN 文件仅在存在时生成）：

```text
artifacts/grid.vtu
artifacts/grid_display.vtu
artifacts/dfn_segments.vtu
artifacts/dfn_units.vtu
artifacts/overview.png
artifacts/slice.png
artifacts/summary.json
```
