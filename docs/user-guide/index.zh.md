# 用户指南

本指南面向 **pysr3 的使用者**——希望读取 CMG SR3 结果、构建网格、映射属性以及
提取井/时序数据的工程师和分析人员。

如果您希望了解或扩展内部实现，请参阅
[开发者指南](../developer-guide/index.md)。

## 阅读顺序

<div class="grid cards" markdown>

-   :material-download: **[安装](installation.md)**

    安装 pysr3 及其依赖项，包含无头渲染的相关说明。

-   :material-rocket-launch: **[快速开始](quickstart.md)**

    在一个简短脚本中完成完整的读取 → 构建 → 映射流程。

-   :material-grid: **[构建网格](grid-building.md)**

    网格类型、LGR 显示模式、DFN 曲面，以及所得的单元数据数组。

-   :material-book-open-variant: **[概念](concepts/grid-types.md)**

    网格类型、坐标系、DFN 与 LGR 的区别以及时序的背景知识。

-   :material-school: **[教程](tutorials/index.md)**

    针对真实 STARS SR3 文件的目标导向图文演练。

-   :material-code-braces: **[示例](examples/grid-cases.md)**

    每个支持场景的可直接复制的代码片段。

</div>

## 三个层次

pysr3 由三个小型、可组合的层次构成。大多数工作流按顺序使用全部三层：

```python
from pysr3 import SR3Indexer, GridBuilder, DataMapper
```

| 层次 | 类 | 用途 |
|---|---|---|
| 访问层 | `SR3Indexer` | 打开文件并查询其内容（时间、属性、井）。 |
| 几何层 | `GridBuilder` | 将某一网格时间步转换为 PyVista `UnstructuredGrid`。 |
| 属性层 | `DataMapper` | 将 `PRES`/`SO`/…值附加到网格单元。 |

完整的函数签名请参阅 [API 参考](../api/index.md)。
