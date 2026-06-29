# 第一个 SR3 案例

## 目标

读取一个 STARS SR3 文件，构建网格，并将压力（`PRES`）映射到各单元上。

## 输入

```text
test/cartesian/cartesian.sr3
```

## 代码

```python
from sr3kit import SR3Indexer, GridBuilder, DataMapper

with SR3Indexer("test/cartesian/cartesian.sr3", eager_list_steps=None) as sr3:
    grid = GridBuilder(sr3).build(
        grid_type="Cartesian",
        grid_mode="mixed",
        time_step=0,
    )

    df = DataMapper(sr3).map_prop(grid=grid, keywords="PRES", time_steps=[0])

print(grid.n_cells)
print(df.head())
```

## 结果

![Cartesian overview](../../assets/images/cartesian_overview.png)

## 原理说明

- `SR3Indexer` 打开文件并对其内容建立索引。
- `GridBuilder` 将网格数组转换为 PyVista `UnstructuredGrid`，
  并为每个单元打上 `PropGlobalID` 和 `GlobalCellID` 标记。
- `DataMapper` 读取 `PRES` 数组，利用 `PropGlobalID` 将每个值放置到
  对应单元，返回带标签的 DataFrame。

下一步：[构建显示资产](grid-visualization.md)，或完整了解
[读取 → 构建 → 映射流程](../quickstart.md)。
