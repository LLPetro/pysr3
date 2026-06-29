# 开发者指南

本指南面向**贡献者和维护者**：介绍 sr3kit 的结构、贯穿各层的数据模型，以及如何扩展和验证它。

如果您只是想*使用* sr3kit，请从[用户指南](../user-guide/index.md)开始。

<div class="grid cards" markdown>

-   :material-sitemap: **[架构](architecture.md)**

    三层结构、模块布局与数据流。

-   :material-database: **[数据模型与类型](data-model.md)**

    单元数据数组、`PropGlobalID` / `GlobalCellID` 键，以及 SR3 数组术语表。

-   :material-relation-many-to-many: **[组件关系](components.md)**

    `SR3Indexer`、`GridBuilder`、策略与 `DataMapper` 之间的交互方式。

-   :material-cog: **[网格策略内部机制](grid-internals.md)**

    策略注册表、共享几何工具函数，以及各网格族的算法。

-   :material-test-tube: **[测试与验证](testing.md)**

    单元测试套件、真实 SR3 测试样本，以及基线核验框架。

-   :material-source-pull: **[贡献指南](contributing.md)**

    开发环境配置、编码规范，以及如何添加新网格类型。

</div>

## 源代码布局

```text
sr3kit/
├── __init__.py          # public API: SR3Indexer, GridBuilder, DataMapper, available_grid_types
├── sr3_indexer.py       # access layer
├── grid_builder.py      # geometry facade (dispatches to strategies)
├── data_mapper.py       # property layer
└── grid/
    ├── geometry.py      # reusable pure-NumPy helpers
    ├── base.py          # GridStrategy ABC + registry
    ├── cartesian.py     # Cartesian / VARI strategy
    ├── corner_point.py  # corner-point strategy (3 encodings + fallback)
    ├── radial.py        # radial strategy (adaptive subdivision)
    └── dfn.py           # embedded DFN unit/segment builders
```
