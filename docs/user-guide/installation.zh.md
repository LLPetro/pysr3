# 安装

## 环境要求

- **Python** ≥ 3.9
- **NumPy**、**h5py**、**PyVista**、**pandas**（自动安装）

pysr3 通过 `h5py` 读取 SR3 文件，使用 NumPy 构建几何体，以 PyVista
`UnstructuredGrid` 对象返回网格，并使用 pandas 整理结果。

## 从源码安装

在 pysr3 发布到 PyPI 之前，请从检出的代码安装：

```bash
git clone <repository-url>
cd pysr3
pip install -e .
```

在 API 仍在演进阶段，推荐使用可编辑安装（`-e`）。
若仅需安装运行时依赖而不安装包本身，请使用：

```bash
pip install -r requirements.txt
```

## 可选附加依赖

```bash
pip install -e ".[dev]"    # pytest, for running the test suite
pip install -e ".[docs]"   # mkdocs-material, to build this site
```

## 验证安装

```python
import pysr3
print(pysr3.__version__)
print(pysr3.available_grid_types())   # ['Cartesian', 'CornerPoint', 'Radial']
```

## 无头/服务器渲染

PyVista 使用 VTK 进行渲染，VTK 需要显示器。在无头环境
（CI、服务器、无 X 服务器的 WSL）中，请在绘图或导出图像之前启用离屏渲染：

```python
import pyvista as pv
pv.OFF_SCREEN = True
```

内置导出工具 `tools/export_case_assets.py` 已设置此选项。在 Linux 上，
您可能还需要虚拟帧缓冲：

```bash
sudo apt-get install -y libgl1 xvfb
xvfb-run -a python tools/export_case_assets.py
```

!!! tip "测试数据已包含在内"
    仓库在 `test/` 目录下附带了真实的 STARS 2025.20 SR3 文件，
    因此本指南中的每个示例无需额外下载即可运行。
