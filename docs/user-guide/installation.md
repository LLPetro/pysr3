# Installation

## Requirements

- **Python** ≥ 3.9
- **NumPy**, **h5py**, **PyVista**, **pandas** (installed automatically)

sr3kit reads SR3 files through `h5py`, builds geometry with NumPy, returns
meshes as PyVista `UnstructuredGrid` objects, and tabulates results with
pandas.

## Install from source

Until sr3kit is published to PyPI, install it from a checkout:

```bash
git clone <repository-url>
cd sr3kit
pip install -e .
```

The editable install (`-e`) is recommended while the API is still evolving.
To install just the runtime dependencies without the package, use:

```bash
pip install -r requirements.txt
```

## Optional extras

```bash
pip install -e ".[dev]"    # pytest, for running the test suite
pip install -e ".[docs]"   # mkdocs-material, to build this site
```

## Verify

```python
import sr3kit
print(sr3kit.__version__)
print(sr3kit.available_grid_types())   # ['Cartesian', 'CornerPoint', 'Radial']
```

## Headless / server rendering

PyVista renders with VTK, which expects a display. On a headless machine
(CI, a server, WSL without an X server), enable off-screen rendering before
plotting or exporting images:

```python
import pyvista as pv
pv.OFF_SCREEN = True
```

The bundled exporter `tools/export_case_assets.py` already sets this. On Linux
you may also need a virtual framebuffer:

```bash
sudo apt-get install -y libgl1 xvfb
xvfb-run -a python tools/export_case_assets.py
```

!!! tip "Test data is included"
    The repository ships real STARS SR3 files under `test/`, so every
    example in this guide runs without extra downloads.
