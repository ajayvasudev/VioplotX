# VioPlotX

**Violin + Box Plot Overlay Tool for Omic & Biological Data**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)](https://github.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)](https://github.com)

VioPlotX is a desktop application for generating **publication-quality Violin + Box Plot overlays** from biological and omic datasets. Built entirely in Python, it is designed for researchers in proteomics, transcriptomics, and related fields who need fast, accurate, and statistically annotated visualizations — without writing a single line of code.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [How to Use](#how-to-use)
- [Supported File Formats](#supported-file-formats)
- [Plot Options](#plot-options)
- [Statistical Testing](#statistical-testing)
- [Export](#export)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Data Input
- Drag and drop files directly onto dataset cards
- Supports CSV, TSV, TXT, XLSX, XLS
- Auto-detects the numeric value column (works with `Title | Value` style files)
- Background threaded loading — UI never freezes, even on large datasets
- LRU cache — reloading the same file is instant
- Chunked CSV reading for proteomics-scale files (millions of rows)
- Auto-names datasets from file stem

### Visualization
- Violin + Box Plot overlay in one click
- Individual toggles: Violin, Box, Jitter points, Mean dot
- `bw_method = 0.3` — fixed bandwidth prevents KDE over-smoothing on small datasets
- Both horizontal and vertical dashed gridlines for clean readability
- Custom per-dataset colors with a color picker
- Colorblind-friendly default palette (RdBu-inspired scientific colors)
- Plot title at the top only — no duplicate labels

### Scale Intelligence
- **Auto log-scale detection** — automatically switches Y-axis to log scale when:
  - Any dataset has outliers beyond 3× the IQR whisker range
  - Global data spans more than one decade (10× ratio)
- Manual override via checkbox
- Essential for proteomics/mass spectrometry data where outliers compress distributions

### Export
- PNG, JPG, TIFF, PDF, SVG
- Fixed 300 DPI for publication quality
- Custom filename
- White background matching theme_bw style

### Interface
- Clean light professional UI
- Color-coded labeled panels: DATA INPUT, PLOT OPTIONS, PLOT WINDOW, EXPORT
- Always-visible scrollbar in the data input panel
- Centered button text with hover effects
- Status bar with real-time feedback

---

## Screenshots

<img width="1919" height="1019" alt="image" src="https://github.com/user-attachments/assets/e2d82c09-604d-4fb8-b39b-bfe6a92d8b96" />
<img width="1919" height="1017" alt="image" src="https://github.com/user-attachments/assets/3e6b8637-23bd-4e3c-9396-0ce22e540158" />


---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/vioplotX.git
cd vioplotx
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
python vioplotX.py
```

---

## How to Use

### Step 1 — Load your data
- Click **Browse** or drag and drop a file onto a dataset card
- The app automatically detects your numeric column (e.g. `MSGFScore`, `Intensity`, `Hyperscore`)
- Status shows number of values loaded and column name
- Add more datasets with **+ Add Dataset**

### Step 2 — Configure your plot
In the **PLOT OPTIONS** panel:
- Set a **Plot Title** (appears at the top of the plot only)
- Set a **Y-axis Label** (auto-filled from column name if left blank)
- Toggle **Violin**, **Box**, **Jitter**, **Mean dot** on/off
- **Log Y-axis** auto-activates for compressed distributions — or toggle manually

### Step 3 — Generate
Click **Generate Plot** — the plot appears in the PLOT WINDOW.

### Step 4 — Export
In the **EXPORT** panel:
- Browse to your output folder
- Set a filename
- Choose format (PNG / JPG / TIFF / PDF / SVG)
- Click **Export Figure** — saved at 300 DPI

---

## Supported File Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| CSV | `.csv` | Comma or tab separated |
| TSV | `.tsv` | Tab separated |
| Text | `.txt` | Auto-delimiter detection |
| Excel | `.xlsx`, `.xls` | First numeric column used |

### Expected file structure

VioPlotX works with **any file that has at least one numeric column**. The most common format is:

```
Title    MSGFScore
A        1.1
B        5.0
C        3.2
D        2.5
```

The app automatically picks the **last numeric column** as the value column, so `Title | Value` style files work out of the box.

---

## Plot Options

| Option | Default | Description |
|--------|---------|-------------|
| Violin | ✅ On | KDE violin shape, `bw=0.3` |
| Box | ✅ On | IQR box, whiskers, outlier dots |
| Jitter | ❌ Off | Individual data points (subsampled to 500 max) |
| Mean dot | ❌ Off | White dot at mean position |
| Log Y-axis | Auto | Auto-detected from data; manual override available |
| Plot Title | blank | Shown at top of plot only |
| Y-axis Label | Auto | Auto-filled from column name |

---

## Export

All exports are saved at **300 DPI** on a white background — ready for journal submission.

| Format | Use case |
|--------|----------|
| PNG | General purpose, presentations |
| JPG | Smaller file size |
| TIFF | High-quality journal submission |
| PDF | Vector, scalable |
| SVG | Vector, editable in Illustrator/Inkscape |

---

## Project Structure

```
vioplotX/
├── vioplotX.py          ← Main application (single file, run this)
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
├── LICENSE             ← MIT License
├── .gitignore          ← Git ignore rules
└── screenshots/        ← Add your own screenshots here
    ├── main_ui.png
    └── plot_example.png
```
## ⬇️ Download

Download the latest version from the Releases section:

👉 https://github.com/ajayvasudev/VioplotX/releases

⚠️ If Windows SmartScreen blocks the app:
Click "More info" → "Run anyway"

---

## Requirements

| Package | Version | Purpose |
|---------|---------|---------|
| `tkinterdnd2` | ≥ 0.3.0 | Drag and drop support |
| `pandas` | ≥ 1.5.0 | File reading (CSV, TSV, XLSX) |
| `numpy` | ≥ 1.23.0 | Numerical operations |
| `matplotlib` | ≥ 3.6.0 | Plot rendering |
| `scipy` | ≥ 1.9.0 | Statistical tests (Mann-Whitney, t-test) |
| `openpyxl` | ≥ 3.0.10 | Excel file support |

Install all at once:

```bash
pip install -r requirements.txt
```

---

## Contributing

Contributions are welcome. To contribute:

1. Fork the repository
2. Create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Commit your changes
   ```bash
   git commit -m "Add: your feature description"
   ```
4. Push to your branch
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a Pull Request

### Ideas for contributions
- Support for multi-column file selection (choose which column to plot)
- Additional statistical tests (ANOVA, Kruskal-Wallis)
- Color palette presets (colorblind-safe, publication palettes)
- Batch export (export all datasets as separate figures)
- Dark mode toggle

---

## License

MIT License — see [LICENSE](LICENSE) for full details.

---

## Acknowledgements

Built with:
- [Matplotlib](https://matplotlib.org/) — plotting engine
- [Pandas](https://pandas.pydata.org/) — data loading
- [SciPy](https://scipy.org/) — statistical tests
- [NumPy](https://numpy.org/) — numerical operations
- [TkinterDnD2](https://github.com/pmgagne/tkinterdnd2) — drag and drop

---

*Developed for omic data analysis. If you use VioPlotX in your research, consider starring the repository.*
