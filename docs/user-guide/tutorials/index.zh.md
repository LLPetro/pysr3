# 教程

每个教程均遵循相同的结构 — **目标 → 代码 → 结果 → 原理说明** —
并针对 `test/` 目录下的真实 STARS SR3 文件运行。建议初次阅读时按顺序学习。

<div class="gallery-grid" markdown>

<div class="gallery-card" markdown>
![Cartesian overview](../../assets/images/cartesian_overview.png)
<div markdown>
### [第一个 SR3 案例](first-sr3-case.md)
读取 SR3 文件，构建网格，映射 `PRES`。
</div>
</div>

<div class="gallery-card" markdown>
![Tutorial HM overview](../../assets/images/tutorial_hm_overview.png)
<div markdown>
### [网格可视化](grid-visualization.md)
导出 VTU 文件及渲染图，支持垂向夸张。
</div>
</div>

<div class="gallery-card" markdown>
![Convert to corner overview](../../assets/images/convert_to_corner_overview.png)
<div markdown>
### [角点网格](corner-grid.md)
`CornerPoint`、Z 方向显示，以及转换为角点 + DFN 的案例。
</div>
</div>

<div class="gallery-card" markdown>
![Well BHP curve](../../assets/images/well_bhp_curve.png)
<div markdown>
### [井时序数据](well-timeseries.md)
读取井 BHP，导出 CSV，绘制曲线。
</div>
</div>

<div class="gallery-card" markdown>
![HM model pressure](../../assets/images/guide_3d.png)
<div markdown>
### [深入：HM 模型](inspect-hm-model.md)
3D 场景、等值面、过滤、剖面、等值线与时序绘图。
</div>
</div>

</div>

## 重新生成图表

图片来源于 `test/` 目录下的真实 STARS SR3 案例：

```bash
python tools/export_case_assets.py
python tools/export_timeseries_assets.py
```
