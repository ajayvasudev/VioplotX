import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD

import pandas as pd
import numpy as np
import os
import threading
import functools

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import FancyBboxPatch


# ─────────────────────────────────────────────
# THEME  — Light, professional, standard colours
# ─────────────────────────────────────────────

BG_DARK       = "#F0F2F5"   # main window background — light grey
BG_PANEL      = "#FFFFFF"   # panel background — white
BG_CARD       = "#F7F8FA"   # dataset card background
BG_HOVER      = "#E8ECF2"   # hover state
ACCENT        = "#2563EB"   # primary blue (DATA INPUT header, Generate Plot)
ACCENT2       = "#7C3AED"   # purple (PLOT OPTIONS header)
SUCCESS       = "#059669"   # green (PLOT WINDOW header)
DANGER        = "#DC2626"   # red (Clear All Inputs, remove button)
WARNING       = "#D97706"   # amber (EXPORT header)
TEXT_PRIMARY  = "#1E293B"   # near-black text
TEXT_MUTED    = "#64748B"   # muted slate text
BORDER_COLOR  = "#CBD5E1"   # light border
BORDER_ACCENT = "#2563EB"   # accent border line

DEFAULT_COLORS = [
    "#2166AC",   # strong blue
    "#1A9850",   # strong green
    "#D6604D",   # muted red-orange
    "#762A83",   # deep violet
    "#F4A582",   # soft peach
    "#4DAC26",   # lime green
    "#0571B0",   # mid blue
    "#92C5DE",   # sky blue
    "#B2ABD2",   # lavender
]

FONT_TITLE  = ("Segoe UI", 13, "bold")
FONT_LABEL  = ("Segoe UI", 9)
FONT_LABEL_B= ("Segoe UI", 9, "bold")
FONT_SMALL  = ("Segoe UI", 8)
FONT_MONO   = ("Consolas", 8)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def styled_button(parent, text, command, style="default", width=None):
    """Flat styled button with hover effect."""
    styles = {
        "primary":  (ACCENT,   "#1D4ED8", "#FFFFFF"),
        "success":  (SUCCESS,  "#047857", "#FFFFFF"),
        "danger":   (DANGER,   "#B91C1C", "#FFFFFF"),
        "default":  (BG_CARD,  BG_HOVER,  TEXT_PRIMARY),
        "ghost":    (BG_HOVER, BORDER_COLOR, TEXT_MUTED),
    }
    bg, hover_bg, fg = styles.get(style, styles["default"])

    btn_opts = dict(
        text=text, command=command,
        bg=bg, fg=fg,
        relief="flat", bd=0,
        padx=12, pady=5,
        font=FONT_LABEL_B,
        cursor="hand2",
        anchor="center",
        activebackground=hover_bg,
        activeforeground=fg,
        highlightthickness=0,
    )
    if width:
        btn_opts["width"] = width

    btn = tk.Button(parent, **btn_opts)
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def labeled_panel(parent, title, accent=ACCENT, **grid_kwargs):
    """
    Creates a LabelFrame-style panel with a dark styled border and label.
    Returns the inner frame for child widgets.
    """
    outer = tk.Frame(parent, bg=BG_DARK)
    outer.grid(**grid_kwargs, padx=8, pady=6)

    # Top border label row
    header = tk.Frame(outer, bg=BG_DARK)
    header.pack(fill="x")

    tk.Label(
        header,
        text=f"  {title}  ",
        bg=accent,
        fg="#FFFFFF",
        font=FONT_LABEL_B,
        padx=6, pady=2,
    ).pack(side="left")

    # Border frame
    border = tk.Frame(outer, bg=accent, bd=0, height=2)
    border.pack(fill="x")

    # Content frame
    inner = tk.Frame(outer, bg=BG_PANEL, padx=10, pady=10)
    inner.pack(fill="both", expand=True, pady=(0, 0))

    # Bottom + side border simulation (thin lines)
    tk.Frame(outer, bg=BORDER_COLOR, height=1).pack(fill="x", side="bottom")

    return inner


# ─────────────────────────────────────────────
# DATA CACHE (LRU, thread-safe wrapper)
# ─────────────────────────────────────────────

@functools.lru_cache(maxsize=32)
def _cached_load(filepath: str, mtime: float):
    """
    Cached file loader keyed by path + modification time.

    Handles files like:
        Title   MSGFScore          ← mixed text + numeric columns
        A       1.1
        B       5.0

    Strategy:
      1. Read the file (Excel / CSV / TSV / auto-detect).
      2. Try pandas select_dtypes(number) first.
      3. If that finds nothing, coerce every column to numeric and
         keep whichever columns have at least one valid number.
      4. Return the LAST numeric column found (rightmost), which is
         the actual value column in Title+Value style files.
    """
    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(filepath)

        elif ext == ".csv":
            # Try comma first; if only one column found, retry with tab
            df = pd.read_csv(filepath, sep=",", low_memory=False)
            if df.shape[1] == 1:
                df = pd.read_csv(filepath, sep="\t", low_memory=False)

        elif ext in (".tsv",):
            df = pd.read_csv(filepath, sep="\t", low_memory=False)

        else:
            # Auto-detect separator (covers .txt and others)
            try:
                df = pd.read_csv(filepath, sep=None, engine="python", low_memory=False)
            except Exception:
                df = pd.read_csv(filepath, sep="\t", low_memory=False)
            # If auto-detect collapsed everything into one column, retry with tab
            if df.shape[1] == 1:
                try:
                    df_tab = pd.read_csv(filepath, sep="\t", low_memory=False)
                    if df_tab.shape[1] > 1:
                        df = df_tab
                except Exception:
                    pass

    except Exception:
        return None, None

    # ── Step 1: native numeric columns ───────────────────────────────────
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    # ── Step 2: if nothing found, coerce each column and check ───────────
    if not numeric_cols:
        for col in df.columns:
            coerced = pd.to_numeric(df[col], errors="coerce")
            if coerced.notna().sum() > 0:
                numeric_cols.append(col)
                # Replace the column in df with coerced values so dropna works
                df[col] = coerced

    if not numeric_cols:
        return None, None

    # ── Step 3: pick best column ──────────────────────────────────────────
    # For Title+Value style files the value column is the LAST numeric col.
    # For single-column files it will simply be that one column.
    col = numeric_cols[-1]
    values = pd.to_numeric(df[col], errors="coerce").dropna().values

    if len(values) == 0:
        return None, None

    return values, str(col)


def load_file(filepath):
    try:
        mtime = os.path.getmtime(filepath)
        return _cached_load(filepath, mtime)
    except Exception:
        return None, None


# ─────────────────────────────────────────────
# DATASET BLOCK
# ─────────────────────────────────────────────

class DatasetBlock:

    def __init__(self, parent, app, color, index):
        self.app    = app
        self.color  = color
        self.index  = index

        self.filepath  = None
        self._data     = None
        self._col_name = None
        self._loading  = False

        # Card frame
        self.frame = tk.Frame(
            parent,
            bg=BG_CARD,
            bd=0,
            padx=10, pady=8
        )

        # Left accent bar
        accent_bar = tk.Frame(self.frame, bg=self.color, width=3)
        accent_bar.pack(side="left", fill="y", padx=(0, 8))
        self._accent_bar = accent_bar

        content = tk.Frame(self.frame, bg=BG_CARD)
        content.pack(side="left", fill="both", expand=True)

        # Row 0: index badge + name entry
        row0 = tk.Frame(content, bg=BG_CARD)
        row0.pack(fill="x", pady=(0, 4))

        tk.Label(
            row0,
            text=f"#{self.index}",
            bg=ACCENT2, fg="#FFFFFF",
            font=FONT_SMALL,
            width=3, anchor="center"
        ).pack(side="left", padx=(0, 6))

        self.name_entry = tk.Entry(
            row0,
            width=18,
            bg=BG_HOVER,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            font=FONT_LABEL,
            bd=4,
        )
        self.name_entry.insert(0, f"Dataset {self.index}")
        self.name_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        # Remove button
        styled_button(row0, "✕", self.remove, style="danger").pack(side="right")

        # Row 1: file drop zone
        row1 = tk.Frame(content, bg=BG_CARD)
        row1.pack(fill="x", pady=2)

        self.file_label = tk.Label(
            row1,
            text="⬇  Drop file here or Browse",
            width=28,
            anchor="w",
            bg=BG_HOVER,
            fg=TEXT_MUTED,
            font=FONT_SMALL,
            relief="flat",
            padx=6, pady=5,
        )
        self.file_label.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.file_label.drop_target_register(DND_FILES)
        self.file_label.dnd_bind("<<Drop>>",      self.drop_file)
        self.file_label.dnd_bind("<<DragEnter>>", self._drag_enter)
        self.file_label.dnd_bind("<<DragLeave>>", self._drag_leave)

        styled_button(row1, "Browse", self.browse_file, style="ghost").pack(side="right")

        # Row 2: color + status
        row2 = tk.Frame(content, bg=BG_CARD)
        row2.pack(fill="x", pady=(4, 0))

        self.color_swatch = tk.Label(
            row2,
            bg=self.color,
            width=3, height=1,
            relief="flat",
            cursor="hand2",
        )
        self.color_swatch.pack(side="left", padx=(0, 4))
        self.color_swatch.bind("<Button-1>", lambda e: self.choose_color())

        self.status_label = tk.Label(
            row2,
            text="No file loaded",
            bg=BG_CARD,
            fg=TEXT_MUTED,
            font=FONT_SMALL,
        )
        self.status_label.pack(side="left")

        # Separator line
        tk.Frame(self.frame, bg=BORDER_COLOR, height=1).pack(
            side="bottom", fill="x", after=content
        )

    # ── Drag visuals ──────────────────────────

    def _drag_enter(self, e):
        self.file_label.config(bg=ACCENT, fg="#FFFFFF")

    def _drag_leave(self, e):
        self.file_label.config(
            bg=BG_HOVER,
            fg=TEXT_MUTED if not self.filepath else TEXT_PRIMARY
        )

    # ── File loading ──────────────────────────

    def browse_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Data files", "*.csv *.tsv *.txt *.xlsx *.xls")]
        )
        if path:
            self.set_file(path)

    def drop_file(self, event):
        path = event.data.strip("{}")
        if os.path.isfile(path):
            self.set_file(path)
        self._drag_leave(None)

    def set_file(self, path):
        self.filepath = path
        self._data    = None
        self._col_name = None
        self._loading  = True

        name = os.path.basename(path)
        self.file_label.config(
            text=f"⏳ {name[:30]}…" if len(name) > 30 else f"⏳ {name}",
            fg=WARNING
        )
        self.status_label.config(text="Loading…", fg=WARNING)

        thread = threading.Thread(target=self._load_async, daemon=True)
        thread.start()

    def _load_async(self):
        values, col = load_file(self.filepath)
        self._data     = values
        self._col_name = col
        self._loading  = False
        self.app.root.after(0, self._on_load_done)

    def _on_load_done(self):
        name = os.path.basename(self.filepath)
        short = name[:26] + "…" if len(name) > 26 else name

        if self._data is not None:
            n = len(self._data)
            self.file_label.config(text=f"✓ {short}", fg=SUCCESS)
            self.status_label.config(
                text=f"{n:,} values · col: {self._col_name}",
                fg=SUCCESS
            )
            # Auto-fill dataset name from filename stem
            if self.name_entry.get().startswith("Dataset "):
                stem = os.path.splitext(name)[0][:18]
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, stem)
        else:
            self.file_label.config(text=f"⚠ {short}", fg=DANGER)
            self.status_label.config(text="No numeric column found", fg=DANGER)

        self._auto_add_if_needed()

    def _auto_add_if_needed(self):
        if all(b.filepath for b in self.app.datasets):
            self.app.add_dataset()

    # ── Color ─────────────────────────────────

    def choose_color(self):
        result = colorchooser.askcolor(color=self.color, title="Pick dataset color")
        if result[1]:
            self.color = result[1]
            self.color_swatch.config(bg=self.color)
            self._accent_bar.config(bg=self.color)

    def remove(self):
        if len(self.app.datasets) <= 2:
            messagebox.showwarning("Warning", "Minimum two datasets required.")
            return
        self.frame.destroy()
        self.app.datasets.remove(self)

    def get_data(self):
        return self._data, self._col_name


# ─────────────────────────────────────────────
# PLOT OPTIONS PANEL
# ─────────────────────────────────────────────

class PlotOptionsPanel:

    def __init__(self, parent):

        self.frame = parent

        row = tk.Frame(parent, bg=BG_PANEL)
        row.pack(fill="x", pady=3)

        # Plot title
        tk.Label(row, text="Plot Title", bg=BG_PANEL, fg=TEXT_MUTED,
                 font=FONT_LABEL).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.title_var = tk.StringVar(value="")
        tk.Entry(row, textvariable=self.title_var, width=22,
                 bg=BG_HOVER, fg=TEXT_PRIMARY,
                 insertbackground=TEXT_PRIMARY,
                 relief="flat", font=FONT_LABEL, bd=4
                 ).grid(row=0, column=1, columnspan=3, sticky="ew", pady=2)

        # Y-axis label
        tk.Label(row, text="Y-axis Label", bg=BG_PANEL, fg=TEXT_MUTED,
                 font=FONT_LABEL).grid(row=1, column=0, sticky="w", padx=(0, 6))
        self.ylabel_var = tk.StringVar(value="")
        tk.Entry(row, textvariable=self.ylabel_var, width=22,
                 bg=BG_HOVER, fg=TEXT_PRIMARY,
                 insertbackground=TEXT_PRIMARY,
                 relief="flat", font=FONT_LABEL, bd=4
                 ).grid(row=1, column=1, columnspan=3, sticky="ew", pady=2)

        # Toggle row
        trow = tk.Frame(parent, bg=BG_PANEL)
        trow.pack(fill="x", pady=4)

        self.show_violin  = self._toggle(trow, "Violin",   True,  0)
        self.show_box     = self._toggle(trow, "Box",      True,  1)
        self.show_points  = self._toggle(trow, "Jitter",   False, 2)
        self.show_mean    = self._toggle(trow, "Mean dot", False, 3)

        # Log scale toggle row
        lrow = tk.Frame(parent, bg=BG_PANEL)
        lrow.pack(fill="x", pady=(0, 4))
        self._log_manually_set = False
        self.use_log_scale = self._toggle(lrow, "Log Y-axis", False, 0)
        self.use_log_scale.trace_add("write", lambda *_: setattr(self, "_log_manually_set", True))

        # Fixed internal values (not exposed in UI)
        self.alpha_var     = tk.DoubleVar(value=0.7)
        self.box_width_var = tk.DoubleVar(value=0.15)

    def _toggle(self, parent, label, default, col):
        var = tk.BooleanVar(value=default)
        cb = tk.Checkbutton(
            parent,
            text=label,
            variable=var,
            bg=BG_PANEL, fg=TEXT_PRIMARY,
            selectcolor="#FFFFFF",
            activebackground=BG_PANEL,
            activeforeground=TEXT_PRIMARY,
            font=FONT_SMALL,
        )
        cb.grid(row=0, column=col, padx=4)
        return var


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

class VioPlotXApp:

    def __init__(self, root):
        self.root = root
        root.title("VioPlotX")
        root.geometry("1280x760")
        root.minsize(1000, 620)
        root.configure(bg=BG_DARK)

        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=0)
        root.grid_columnconfigure(1, weight=1)

        self.datasets    = []
        self.current_fig = None
        self.color_index = 0
        self._plot_thread = None

        self._build_left_panel()
        self._build_right_panel()

        # Seed two datasets
        self.add_dataset()
        self.add_dataset()

    # ─────────────────────────────────────────
    # LEFT PANEL — Data Input + Options
    # ─────────────────────────────────────────

    def _build_left_panel(self):

        left_outer = tk.Frame(self.root, bg=BG_DARK, width=320)
        left_outer.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        left_outer.grid_propagate(False)
        left_outer.grid_rowconfigure(0, weight=1)

        # ── Datasets panel ────────────────────
        ds_panel = tk.Frame(
            left_outer,
            bg=BG_PANEL,
            bd=0,
            highlightbackground=ACCENT,
            highlightthickness=2,
        )
        ds_panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        ds_panel.grid_rowconfigure(1, weight=1)
        ds_panel.grid_columnconfigure(0, weight=1)

        # Panel header
        dsh = tk.Frame(ds_panel, bg=ACCENT, height=28)
        dsh.grid(row=0, column=0, sticky="ew")
        dsh.grid_propagate(False)
        tk.Label(
            dsh, text="  📂  DATA INPUT",
            bg=ACCENT, fg="#FFFFFF",
            font=FONT_LABEL_B
        ).pack(side="left", pady=4)

        # Scrollable dataset list
        scroll_outer = tk.Frame(ds_panel, bg="#FFFFFF")
        scroll_outer.grid(row=1, column=0, sticky="nsew")

        # Use ttk.Scrollbar — always rendered visibly regardless of content size
        self.ds_scrollbar = ttk.Scrollbar(scroll_outer, orient="vertical")
        self.ds_scrollbar.pack(side="right", fill="y")

        # Canvas to the left of the scrollbar
        self.ds_canvas = tk.Canvas(
            scroll_outer,
            bg="#FFFFFF",
            bd=0,
            highlightthickness=0,
            yscrollcommand=self.ds_scrollbar.set,
        )
        self.ds_canvas.pack(side="left", fill="both", expand=True)

        self.ds_scrollbar.config(command=self.ds_canvas.yview)

        self.scroll_frame = tk.Frame(self.ds_canvas, bg="#FFFFFF")
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.ds_canvas.configure(
                scrollregion=self.ds_canvas.bbox("all")
            )
        )
        self.ds_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        # Smooth scroll with mouse wheel
        self.ds_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.ds_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"
            )
        )

        # Add dataset button
        btn_row = tk.Frame(ds_panel, bg=BG_PANEL, pady=4)
        btn_row.grid(row=2, column=0, sticky="ew", padx=8)
        styled_button(btn_row, "+ Add Dataset", self.add_dataset,
                      style="ghost").pack(side="left")
        styled_button(btn_row, "⟳ Reset", self.reset_app,
                      style="ghost").pack(side="right")

        # Clear All Inputs — canvas button guarantees text is pixel-perfect centered
        clear_row = tk.Frame(ds_panel, bg=BG_PANEL, pady=2)
        clear_row.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 6))

        def _make_canvas_button(parent, text, command, bg, hover_bg, fg="#FFFFFF", height=36):
            c = tk.Canvas(parent, bg=bg, height=height, bd=0,
                          highlightthickness=0, cursor="hand2")
            c.pack(fill="x")
            def _redraw(event=None):
                c.delete("all")
                w = c.winfo_width() or 1
                h = c.winfo_height() or height
                c.config(bg=c._cur_bg)
                c.create_text(w // 2, h // 2, text=text,
                              fill=fg, font=FONT_LABEL_B, anchor="center")
            c._cur_bg = bg
            c.bind("<Configure>", _redraw)
            c.bind("<Enter>",  lambda e: [setattr(c, '_cur_bg', hover_bg),
                                          c.config(bg=hover_bg), _redraw()])
            c.bind("<Leave>",  lambda e: [setattr(c, '_cur_bg', bg),
                                          c.config(bg=bg), _redraw()])
            c.bind("<Button-1>", lambda e: command())
            return c

        self._make_canvas_button = _make_canvas_button
        _make_canvas_button(clear_row, "Clear All Inputs",
                            self.clear_all_inputs,
                            bg=DANGER, hover_bg="#B91C1C")

        # ── Plot Options panel ─────────────────
        opt_outer = tk.Frame(
            left_outer,
            bg=BG_PANEL,
            bd=0,
            highlightbackground=ACCENT2,
            highlightthickness=2,
        )
        opt_outer.grid(row=1, column=0, sticky="ew", padx=4, pady=(4, 4))

        oh = tk.Frame(opt_outer, bg=ACCENT2, height=28)
        oh.pack(fill="x")
        oh.pack_propagate(False)
        tk.Label(
            oh, text="  ⚙  PLOT OPTIONS",
            bg=ACCENT2, fg="#FFFFFF",
            font=FONT_LABEL_B
        ).pack(side="left", pady=4)

        opt_content = tk.Frame(opt_outer, bg=BG_PANEL, padx=8, pady=6)
        opt_content.pack(fill="x")
        self.plot_options = PlotOptionsPanel(opt_content)

        # Generate button — canvas guarantees pixel-perfect centered text
        gen_frame = tk.Frame(left_outer, bg=BG_DARK, pady=4)
        gen_frame.grid(row=2, column=0, sticky="ew", padx=4)
        _make_canvas_button(gen_frame, "Generate Plot",
                            self.generate_plot,
                            bg=ACCENT, hover_bg="#1D4ED8", height=42)

        left_outer.grid_rowconfigure(0, weight=1)

    # ─────────────────────────────────────────
    # RIGHT PANEL — Plot + Export
    # ─────────────────────────────────────────

    def _build_right_panel(self):

        right_outer = tk.Frame(self.root, bg=BG_DARK)
        right_outer.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        right_outer.grid_rowconfigure(0, weight=1)
        right_outer.grid_rowconfigure(1, weight=0)
        right_outer.grid_columnconfigure(0, weight=1)

        # ── Plot panel ────────────────────────
        plot_outer = tk.Frame(
            right_outer,
            bg=BG_PANEL,
            bd=0,
            highlightbackground=SUCCESS,
            highlightthickness=2,
        )
        plot_outer.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 4))
        plot_outer.grid_rowconfigure(1, weight=1)
        plot_outer.grid_columnconfigure(0, weight=1)

        ph = tk.Frame(plot_outer, bg=SUCCESS, height=28)
        ph.grid(row=0, column=0, sticky="ew")
        ph.grid_propagate(False)
        tk.Label(
            ph, text="  📊  PLOT WINDOW",
            bg=SUCCESS, fg="#FFFFFF",
            font=FONT_LABEL_B
        ).pack(side="left", pady=4)

        self.plot_frame = tk.Frame(plot_outer, bg=BG_PANEL)
        self.plot_frame.grid(row=1, column=0, sticky="nsew")

        # Placeholder
        tk.Label(
            self.plot_frame,
            text="Generate a plot to see it here",
            bg=BG_PANEL, fg=TEXT_MUTED,
            font=("Segoe UI", 11)
        ).place(relx=0.5, rely=0.5, anchor="center")

        # ── Export panel ──────────────────────
        exp_outer = tk.Frame(
            right_outer,
            bg=BG_PANEL,
            bd=0,
            highlightbackground=WARNING,
            highlightthickness=2,
        )
        exp_outer.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))

        exph = tk.Frame(exp_outer, bg=WARNING, height=28)
        exph.pack(fill="x")
        exph.pack_propagate(False)
        tk.Label(
            exph, text="  💾  EXPORT",
            bg=WARNING, fg="#FFFFFF",
            font=FONT_LABEL_B
        ).pack(side="left", pady=4)

        exp_content = tk.Frame(exp_outer, bg=BG_PANEL, padx=10, pady=8)
        exp_content.pack(fill="x")

        # Output folder row
        r0 = tk.Frame(exp_content, bg=BG_PANEL)
        r0.pack(fill="x", pady=2)
        tk.Label(r0, text="Output Folder", bg=BG_PANEL, fg=TEXT_MUTED,
                 font=FONT_LABEL, width=12, anchor="w").pack(side="left")
        self.output_path = tk.Entry(
            r0, width=42,
            bg=BG_HOVER, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat", font=FONT_LABEL, bd=4
        )
        self.output_path.pack(side="left", padx=4, fill="x", expand=True)
        styled_button(r0, "Browse", self.choose_output,
                      style="ghost").pack(side="right")

        # Format + filename + export row
        r1 = tk.Frame(exp_content, bg=BG_PANEL)
        r1.pack(fill="x", pady=2)
        tk.Label(r1, text="Filename", bg=BG_PANEL, fg=TEXT_MUTED,
                 font=FONT_LABEL, width=12, anchor="w").pack(side="left")
        self.filename_var = tk.StringVar(value="ViolinBoxplot_overlay")
        tk.Entry(
            r1, textvariable=self.filename_var, width=28,
            bg=BG_HOVER, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat", font=FONT_LABEL, bd=4
        ).pack(side="left", padx=4)
        tk.Label(r1, text="Format", bg=BG_PANEL, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(side="left", padx=(8, 2))
        self.format_var = tk.StringVar(value="png")
        fmt_menu = tk.OptionMenu(r1, self.format_var, "png", "jpg", "tiff", "pdf", "svg")
        fmt_menu.config(
            bg=BG_HOVER, fg=TEXT_PRIMARY,
            activebackground=ACCENT,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            font=FONT_LABEL,
            indicatoron=False,
            padx=10,
            highlightthickness=0,
        )
        fmt_menu.pack(side="left", padx=4)

        styled_button(
            r1, "Export Figure",
            self.export_figure,
            style="primary"
        ).pack(side="right", padx=4, ipady=3)

        # Status bar
        self.status_bar = tk.Label(
            self.root,
            text="Ready",
            bg=BG_DARK, fg=TEXT_MUTED,
            font=FONT_MONO,
            anchor="w", padx=12
        )
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

    # ─────────────────────────────────────────
    # DATASET MANAGEMENT
    # ─────────────────────────────────────────

    def add_dataset(self):
        color = DEFAULT_COLORS[self.color_index % len(DEFAULT_COLORS)]
        self.color_index += 1
        idx   = len(self.datasets) + 1

        block = DatasetBlock(self.scroll_frame, self, color, idx)
        block.frame.pack(fill="x", padx=4, pady=4)
        self.datasets.append(block)

    def reset_app(self):
        for block in self.datasets:
            block.frame.destroy()
        self.datasets.clear()
        self.color_index = 0

        for widget in self.plot_frame.winfo_children():
            widget.destroy()
        self.current_fig = None

        tk.Label(
            self.plot_frame,
            text="Generate a plot to see it here",
            bg=BG_PANEL, fg=TEXT_MUTED,
            font=("Segoe UI", 11)
        ).place(relx=0.5, rely=0.5, anchor="center")

        self.add_dataset()
        self.add_dataset()
        self.plot_options._log_manually_set = False
        self._set_status("Reset complete.")

    def clear_all_inputs(self):
        """Clear all loaded file data from every dataset card in one click."""
        cleared = 0
        for block in self.datasets:
            if block.filepath:
                block.filepath   = None
                block._data      = None
                block._col_name  = None
                block._loading   = False
                block.file_label.config(
                    text="⬇  Drop file here or Browse",
                    fg=TEXT_MUTED,
                    bg=BG_HOVER,
                )
                block.status_label.config(text="No file loaded", fg=TEXT_MUTED)
                # Reset name entry back to default placeholder
                block.name_entry.delete(0, tk.END)
                block.name_entry.insert(0, f"Dataset {block.index}")
                cleared += 1
        self._set_status(f"Cleared {cleared} dataset input(s).")

    # ─────────────────────────────────────────
    # PLOT GENERATION (threaded data collection)
    # ─────────────────────────────────────────

    def generate_plot(self):
        # Check if any file is still loading
        if any(b._loading for b in self.datasets):
            messagebox.showwarning("Loading", "Some files are still loading. Please wait.")
            return

        data_list, labels, colors = [], [], []
        y_label = None

        for block in self.datasets:
            values, col = block.get_data()
            if values is None:
                continue
            if y_label is None and col:
                y_label = col
            name = block.name_entry.get().strip()
            if not name and block.filepath:
                name = os.path.splitext(os.path.basename(block.filepath))[0]
            data_list.append(values)
            labels.append(name or f"Set {len(data_list)}")
            colors.append(block.color)

        if not data_list:
            messagebox.showerror("Error", "No valid datasets loaded.")
            return

        self._set_status(f"Rendering {len(data_list)} datasets…")
        self.root.update_idletasks()

        # Render in a thread to keep UI responsive
        thread = threading.Thread(
            target=self._render_plot,
            args=(data_list, labels, colors, y_label),
            daemon=True
        )
        thread.start()

    def _render_plot(self, data_list, labels, colors, y_label):
        from scipy import stats as scipy_stats
        import itertools
        import matplotlib.ticker as ticker

        opts = self.plot_options
        fill_colors = list(colors)

        plt.style.use("default")
        fig, ax = plt.subplots(figsize=(10, 6), dpi=72)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        n         = len(data_list)
        positions = list(range(1, n + 1))

        # ── Fixed bw_method=0.3 for all datasets ──────────────────────────
        # 0.3 prevents KDE over-smoothing on small proteomics datasets
        BW = 0.3

        # ── Violin ────────────────────────────────────────────────────────
        if opts.show_violin.get():
            parts = ax.violinplot(
                data_list,
                positions=positions,
                showmeans=False,
                showmedians=False,
                showextrema=False,
                bw_method=BW,
            )
            for i, pc in enumerate(parts["bodies"]):
                pc.set_facecolor(fill_colors[i])
                pc.set_edgecolor(fill_colors[i])
                pc.set_alpha(1.0)

        # ── Box ───────────────────────────────────────────────────────────
        if opts.show_box.get():
            bp = ax.boxplot(
                data_list,
                positions=positions,
                widths=0.2,
                patch_artist=True,
                notch=False,
                medianprops =dict(color="black", linewidth=1.5),
                boxprops     =dict(facecolor="white", edgecolor="black",
                                   linewidth=1.0, alpha=0.5),
                whiskerprops =dict(color="black", linewidth=1.0),
                capprops     =dict(color="black", linewidth=1.0),
                flierprops   =dict(marker="o", markerfacecolor="black",
                                   markeredgecolor="black", markersize=3,
                                   alpha=0.5, linestyle="none"),
            )
            for patch in bp["boxes"]:
                r, g, b, _ = patch.get_facecolor()
                patch.set_facecolor((r, g, b, 0.5))

        # ── Jitter ────────────────────────────────────────────────────────
        if opts.show_points.get():
            for i, (vals, pos) in enumerate(zip(data_list, positions)):
                sample = vals if len(vals) <= 500 else np.random.choice(vals, 500, replace=False)
                jitter = np.random.uniform(-0.06, 0.06, len(sample))
                ax.scatter(pos + jitter, sample, color=fill_colors[i],
                           alpha=0.4, s=6, zorder=3, linewidths=0)

        # ── Mean dot ──────────────────────────────────────────────────────
        if opts.show_mean.get():
            for i, (vals, pos) in enumerate(zip(data_list, positions)):
                ax.scatter(pos, np.mean(vals), color="black", s=35,
                           zorder=5, edgecolors="white", linewidths=1.2)

        # ── Auto log scale ────────────────────────────────────────────────
        all_vals     = np.concatenate(data_list)
        all_vals_pos = all_vals[all_vals > 0]

        def _needs_log(datasets):
            for vals in datasets:
                q1, q3 = np.percentile(vals, [25, 75])
                iqr = q3 - q1
                upper_fence = q3 + 1.5 * iqr
                if upper_fence > 0 and np.max(vals) > 3 * upper_fence:
                    return True
            if len(all_vals_pos) > 0:
                ratio = np.max(all_vals_pos) / (np.min(all_vals_pos) + 1e-9)
                if ratio > 10:
                    return True
            return False

        auto_log = _needs_log(data_list) and len(all_vals_pos) == len(all_vals)
        use_log  = opts.use_log_scale.get() if opts._log_manually_set else auto_log
        opts.use_log_scale.set(use_log)

        if use_log:
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
            ax.yaxis.set_minor_formatter(ticker.NullFormatter())

        # ── Axes styling ──────────────────────────────────────────────────
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, rotation=45, ha="right",
                           fontsize=14, fontweight="bold", color="black")

        ax.tick_params(axis="y", labelsize=10, labelcolor="black", which="both")
        for lbl in ax.get_yticklabels():
            lbl.set_fontweight("bold")

        ylabel_text = opts.ylabel_var.get().strip() or (y_label or "Value")
        ax.set_ylabel(ylabel_text, fontsize=16, fontweight="bold", color="black")

        # X-label: blank always (no "Variable" or duplicate title at bottom)
        ax.set_xlabel("")

        ax.tick_params(axis="both", colors="black", direction="out",
                       length=4, width=0.8)

        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_edgecolor("black")
            spine.set_linewidth(0.8)

        # ── Grid — both horizontal AND vertical dashed lines ──────────────
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color="#DDDDDD", linewidth=0.6, linestyle="--", alpha=0.8)
        ax.xaxis.grid(True, color="#DDDDDD", linewidth=0.6, linestyle="--", alpha=0.8)

        # ── Title — top only, never duplicated at bottom ───────────────────
        plot_title = opts.title_var.get().strip()
        if plot_title:
            ax.set_title(plot_title, fontsize=13, fontweight="bold",
                         color="black", pad=10, loc="center")

        if ax.get_legend():
            ax.get_legend().remove()

        fig.tight_layout(pad=1.5)
        current = fig.subplotpars
        fig.subplots_adjust(left=max(current.left, 0.12))

        self.current_fig = fig
        self.root.after(0, self._show_plot, fig)

    def _show_plot(self, fig):
        for w in self.plot_frame.winfo_children():
            w.destroy()

        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        self._set_status("Plot rendered successfully.")

    # ─────────────────────────────────────────
    # EXPORT
    # ─────────────────────────────────────────

    def choose_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.delete(0, tk.END)
            self.output_path.insert(0, folder)

    def export_figure(self):
        if self.current_fig is None:
            messagebox.showerror("Error", "No plot to export. Generate one first.")
            return
        folder = self.output_path.get().strip()
        if not folder:
            messagebox.showerror("Error", "Please select an output folder.")
            return

        fmt      = self.format_var.get()
        filename = self.filename_var.get().strip() or "ViolinBoxplot_overlay"
        filepath = os.path.join(folder, f"{filename}.{fmt}")

        dpi = 300
        self.current_fig.savefig(filepath, dpi=dpi, bbox_inches="tight",
                                 facecolor="white")
        self._set_status(f"Exported → {filepath}")
        messagebox.showinfo("Saved", f"Figure saved:\n{filepath}")

    # ─────────────────────────────────────────
    # STATUS
    # ─────────────────────────────────────────

    def _set_status(self, msg):
        self.status_bar.config(text=f"  {msg}")
        self.root.update_idletasks()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    root.configure(bg=BG_DARK)

    # Apply ttk theme — make scrollbar clearly visible
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "Vertical.TScrollbar",
        gripcount=0,
        background="#94A3B8",        # thumb — medium slate, clearly visible
        darkcolor="#94A3B8",
        lightcolor="#94A3B8",
        troughcolor="#E2E8F0",       # track — light blue-grey
        bordercolor="#E2E8F0",
        arrowcolor="#475569",
        arrowsize=12,
        relief="flat",
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", "#2563EB"), ("pressed", "#1D4ED8")],
    )

    app = VioPlotXApp(root)
    root.mainloop()