"""Block-based dialog for assembly manual creation with reorderable steps."""

import base64
import io
import logging
import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path
from tkinter.filedialog import askopenfilenames
from tkinter.messagebox import showerror
from typing import Callable, Optional

from PIL import Image, ImageTk

from wireviz_gui._base import NormButton, ToplevelBase
from wireviz_gui.assembly_spec import (
    BLOCK_TYPES,
    AssemblyManualSpec,
    ManualBlock,
    default_blocks_from_yaml,
    default_fields_for,
)

# ─────────────────────────────────────────────────────────────────────────────
# Colours
# ─────────────────────────────────────────────────────────────────────────────
_NAVY  = "#0d1b2a"
_RED   = "#e30613"
_LGRAY = "#f4f4f4"
_DGRAY = "#cccccc"

_LABEL_W = 26   # width of field labels in characters


# ─────────────────────────────────────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────────────────────────────────────

def _labeled_entry(parent, label: str, row: int, default: str = "") -> tk.StringVar:
    tk.Label(parent, text=label, anchor="e", width=_LABEL_W, font=("Arial", 9)).grid(
        row=row, column=0, sticky="e", padx=(4, 2), pady=1
    )
    var = tk.StringVar(value=default)
    tk.Entry(parent, textvariable=var, font=("Arial", 9), width=30).grid(
        row=row, column=1, sticky="ew", padx=(2, 4), pady=1
    )
    return var


def _labeled_check(parent, label: str, row: int, default: bool = False) -> tk.BooleanVar:
    var = tk.BooleanVar(value=default)
    tk.Checkbutton(parent, text=label, variable=var, font=("Arial", 9)).grid(
        row=row, column=0, columnspan=2, sticky="w", padx=8, pady=1
    )
    return var


def _labeled_textarea(parent, label: str, row: int, default: str = "") -> tk.StringVar:
    tk.Label(parent, text=label, anchor="nw", width=_LABEL_W, font=("Arial", 9)).grid(
        row=row, column=0, sticky="ne", padx=(4, 2), pady=1
    )
    var = tk.StringVar(value=default)
    text = tk.Text(parent, font=("Arial", 9), width=30, height=3, wrap="word")
    text.insert("1.0", default)
    text.grid(row=row, column=1, sticky="ew", padx=(2, 4), pady=1)
    # Keep StringVar in sync (one-way: read on collect)
    text._strvar = var  # type: ignore[attr-defined]
    return text  # type: ignore[return-value]  – we return the Text widget for textarea


def _image_to_data_uri(path: str, max_px: int = 1800) -> str:
    """Encode image to base64 data URI. Preserves PNG; JPEG at high quality."""
    img = Image.open(path)
    img.thumbnail((max_px, max_px), Image.LANCZOS)
    buf = io.BytesIO()
    ext = Path(path).suffix.lower()
    if ext == ".png":
        img.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    else:
        img.convert("RGB").save(buf, format="JPEG", quality=92)
        mime = "image/jpeg"
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:{mime};base64,{b64}"


def _make_thumbnail(path: str, size: int = 80) -> ImageTk.PhotoImage:
    img = Image.open(path)
    img.thumbnail((size, size), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


# ─────────────────────────────────────────────────────────────────────────────
# _BlockWidget  – one step/block
# ─────────────────────────────────────────────────────────────────────────────

class _BlockWidget(tk.LabelFrame):
    """Visual representation of one manual block with fields + images."""

    _TYPE_COLORS = {
        "Corte":            "#fff3cd",
        "Procesado":        "#d4edda",
        "Crimpado":         "#cce5ff",
        "Trazabilidad":     "#e2d9f3",
        "Montaje conector": "#fde2e2",
        "Test":             "#d1ecf1",
        "Embalaje":         "#f8d7da",
        "Personalizado":    "#f0f0f0",
    }

    def __init__(self, parent, block: ManualBlock, index: int, total: int,
                 on_up: Callable, on_down: Callable, on_delete: Callable, **kwargs):
        bg = self._TYPE_COLORS.get(block.block_type, "#f0f0f0")
        super().__init__(parent, bg=bg, relief="ridge", bd=2, **kwargs)

        self._block = block
        self._field_vars: dict = {}   # key -> StringVar | BooleanVar | tk.Text
        self._images: list = list(block.images)   # copy
        self._thumb_refs: list = []   # keep refs to avoid GC

        # ── Title bar ──────────────────────────────────────────────────────
        bar = tk.Frame(self, bg=_NAVY)
        bar.pack(fill=tk.X)

        # Step number badge
        tk.Label(bar, text=f" {index+1} ", bg=_RED, fg="white",
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(4, 0), pady=2)

        # Type label
        tk.Label(bar, text=f"[{block.block_type}]", bg=_NAVY, fg=_DGRAY,
                 font=("Arial", 8)).pack(side=tk.LEFT, padx=4)

        # Editable title
        self._title_var = tk.StringVar(value=block.title)
        tk.Entry(bar, textvariable=self._title_var, font=("Arial", 10, "bold"),
                 bg="#1e3050", fg="white", insertbackground="white",
                 relief="flat", width=32).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # Move / delete buttons
        btn_cfg = dict(bg=_NAVY, fg="white", relief="flat", font=("Arial", 10), padx=3)
        tk.Button(bar, text="▲", command=on_up,     **btn_cfg).pack(side=tk.RIGHT, pady=2)
        tk.Button(bar, text="▼", command=on_down,   **btn_cfg).pack(side=tk.RIGHT, pady=2)
        tk.Button(bar, text="✕", command=on_delete,
                  fg="#ff9999", **{**btn_cfg, "fg": "#ff9999"}).pack(side=tk.RIGHT, pady=2, padx=(0, 4))

        # ── Fields ─────────────────────────────────────────────────────────
        fields_frame = tk.Frame(self, bg=bg)
        fields_frame.pack(fill=tk.X, padx=4, pady=(4, 2))
        fields_frame.columnconfigure(1, weight=1)

        for row_idx, (key, label, wtype) in enumerate(BLOCK_TYPES.get(block.block_type, [])):
            current = block.fields.get(key, "")
            if wtype == "check":
                var = _labeled_check(fields_frame, label, row_idx, default=bool(current))
            elif wtype == "textarea":
                var = _labeled_textarea(fields_frame, label, row_idx, default=str(current))
            else:
                var = _labeled_entry(fields_frame, label, row_idx, default=str(current))
            self._field_vars[key] = var

        # ── Images section ─────────────────────────────────────────────────
        img_bar = tk.Frame(self, bg=bg)
        img_bar.pack(fill=tk.X, padx=4, pady=(2, 4))

        tk.Label(img_bar, text="Imágenes:", font=("Arial", 9, "bold"), bg=bg).pack(side=tk.LEFT)
        tk.Button(img_bar, text="+ Agregar imagen",
                  command=self._add_images, font=("Arial", 9),
                  bg="#2d6a2d", fg="white", relief="flat").pack(side=tk.LEFT, padx=6)

        self._thumb_frame = tk.Frame(self, bg=bg)
        self._thumb_frame.pack(fill=tk.X, padx=8)
        self._refresh_thumbnails()

    # ── Public interface ───────────────────────────────────────────────────

    def collect(self) -> ManualBlock:
        """Read current widget state into a ManualBlock."""
        fields: dict = {}
        for key, _label, wtype in BLOCK_TYPES.get(self._block.block_type, []):
            widget = self._field_vars.get(key)
            if widget is None:
                fields[key] = ""
            elif wtype == "check":
                fields[key] = widget.get()
            elif wtype == "textarea":
                # widget is a tk.Text
                fields[key] = widget.get("1.0", "end-1c")
            else:
                fields[key] = widget.get()

        return ManualBlock(
            block_type=self._block.block_type,
            title=self._title_var.get().strip(),
            fields=fields,
            images=list(self._images),
        )

    # ── Private ────────────────────────────────────────────────────────────

    def _add_images(self):
        paths = askopenfilenames(
            title="Seleccionar imágenes",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"), ("All", "*.*")],
        )
        for path in paths:
            try:
                data_uri = _image_to_data_uri(path)
                name = Path(path).name
                self._images.append({"name": name, "data_uri": data_uri, "path": path})
            except Exception as exc:
                showerror("Error imagen", f"No se pudo cargar {path}:\n{exc}")
        self._refresh_thumbnails()

    def _refresh_thumbnails(self):
        for w in self._thumb_frame.winfo_children():
            w.destroy()
        self._thumb_refs.clear()

        for idx, img_data in enumerate(self._images):
            cell = tk.Frame(self._thumb_frame, bg=self._thumb_frame.cget("bg"),
                            relief="ridge", bd=1)
            cell.pack(side=tk.LEFT, padx=4, pady=2)
            try:
                thumb = _make_thumbnail(img_data["path"])
                self._thumb_refs.append(thumb)
                tk.Label(cell, image=thumb, bg="white").pack()
            except Exception:
                tk.Label(cell, text="🖼", font=("Arial", 20)).pack()
            tk.Label(cell, text=img_data["name"][:14], font=("Arial", 7),
                     wraplength=80).pack()
            # Remove button
            tk.Button(cell, text="✕", font=("Arial", 7), relief="flat",
                      command=lambda i=idx: self._remove_image(i)).pack()

    def _remove_image(self, idx: int):
        if 0 <= idx < len(self._images):
            self._images.pop(idx)
        self._refresh_thumbnails()


# ─────────────────────────────────────────────────────────────────────────────
# AssemblyManualDialog  – main dialog
# ─────────────────────────────────────────────────────────────────────────────

class AssemblyManualDialog(ToplevelBase):
    """Dialog for creating a block-based assembly manual."""

    def __init__(
        self,
        parent,
        yaml_text: str = "",
        on_generate_callback: Optional[Callable] = None,
        loglevel=logging.INFO,
    ):
        super().__init__(parent, loglevel=loglevel)
        self.title("Generador de Manual de Ensamblaje")
        self.geometry("820x860")
        self.minsize(700, 600)

        self._yaml_text = yaml_text
        self._on_generate = on_generate_callback
        self._block_data: list = default_blocks_from_yaml(yaml_text)
        self._block_widgets: list = []   # explicit widget tracking to avoid winfo_children issues

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        # Top header strip
        hdr = tk.Frame(self, bg=_NAVY, pady=6)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Manual de Ensamblaje", bg=_NAVY, fg="white",
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=12)

        # Header fields row
        meta = tk.Frame(self, bg=_LGRAY, pady=4)
        meta.pack(fill=tk.X, padx=8, pady=(6, 2))

        def _mf(label, default="", width=20):
            tk.Label(meta, text=label, font=("Arial", 9), bg=_LGRAY).pack(side=tk.LEFT, padx=(8, 0))
            var = tk.StringVar(value=default)
            tk.Entry(meta, textvariable=var, width=width, font=("Arial", 9)).pack(side=tk.LEFT, padx=(2, 6))
            return var

        self._ref_var      = _mf("Referencia:", width=22)
        self._rev_var      = _mf("Rev:", default="A", width=4)
        self._autor_var    = _mf("Autor:", width=16)
        self._fecha_var    = _mf("Fecha:", default=_today(), width=12)

        # Toolbar
        toolbar = tk.Frame(self, bg=_DGRAY, pady=3)
        toolbar.pack(fill=tk.X, padx=8)

        for btype in BLOCK_TYPES:
            color = _BlockWidget._TYPE_COLORS.get(btype, "#f0f0f0")
            tk.Button(
                toolbar, text=f"+ {btype}", font=("Arial", 8),
                bg=color, relief="flat", cursor="hand2",
                command=lambda t=btype: self._add_block(t),
            ).pack(side=tk.LEFT, padx=2, pady=2)

        # Scrollable block area
        scroll_container = tk.Frame(self)
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._canvas = tk.Canvas(scroll_container, bg="white")
        sb = ttk.Scrollbar(scroll_container, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)

        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._block_frame = tk.Frame(self._canvas, bg="white")
        self._canvas_window = self._canvas.create_window((0, 0), window=self._block_frame, anchor="nw")

        self._block_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Bottom buttons
        btn_row = tk.Frame(self, bg=_LGRAY, pady=6)
        btn_row.pack(fill=tk.X, padx=8)

        tk.Button(btn_row, text="⟳ Vista previa HTML",
                  font=("Arial", 10), bg="#005580", fg="white", relief="flat",
                  command=self._preview).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_row, text="📦 Exportar ZIP",
                  font=("Arial", 11, "bold"), bg="#1a6b1a", fg="white", relief="flat",
                  command=self._generate).pack(side=tk.RIGHT, padx=6)

        self._rebuild_blocks()

    # ── Block list management ──────────────────────────────────────────────

    def _collect_current(self):
        """Sync self._block_data from explicit widget list."""
        try:
            self._block_data = [w.collect() for w in self._block_widgets]
        except Exception as exc:
            showerror("Error interno", f"Error al leer datos de los bloques:\n{exc}")
            raise

    def _rebuild_blocks(self):
        # Destroy old widgets
        for w in self._block_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        self._block_widgets.clear()
        # Safety: clear any orphaned children
        for w in self._block_frame.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        total = len(self._block_data)
        for i, block in enumerate(self._block_data):
            bw = _BlockWidget(
                self._block_frame, block, index=i, total=total,
                on_up=lambda i=i: self._move(i, -1),
                on_down=lambda i=i: self._move(i, +1),
                on_delete=lambda i=i: self._delete_block(i),
            )
            bw.pack(fill=tk.X, padx=4, pady=4)
            self._block_widgets.append(bw)

    def _move(self, idx: int, direction: int):
        self._collect_current()
        new_idx = idx + direction
        if 0 <= new_idx < len(self._block_data):
            self._block_data[idx], self._block_data[new_idx] = (
                self._block_data[new_idx], self._block_data[idx]
            )
        self._rebuild_blocks()

    def _delete_block(self, idx: int):
        self._collect_current()
        if 0 <= idx < len(self._block_data):
            self._block_data.pop(idx)
        self._rebuild_blocks()

    def _add_block(self, block_type: str):
        try:
            self._collect_current()
            self._block_data.append(ManualBlock(
                block_type=block_type,
                title=block_type,
                fields=default_fields_for(block_type),
            ))
            self._rebuild_blocks()
            self._canvas.after(100, lambda: self._canvas.yview_moveto(1.0))
        except Exception as exc:
            showerror("Error", f"No se pudo añadir el bloque '{block_type}':\n{exc}")

    # ── Export actions ─────────────────────────────────────────────────────

    def _build_spec(self) -> AssemblyManualSpec:
        self._collect_current()
        return AssemblyManualSpec(
            referencia=self._ref_var.get().strip(),
            revision=self._rev_var.get().strip() or "A",
            fecha=self._fecha_var.get().strip(),
            autor=self._autor_var.get().strip(),
            blocks=list(self._block_data),
        )

    def _preview(self):
        import tempfile, webbrowser
        from wireviz_gui.assembly_export import render_full_html
        spec = self._build_spec()
        html = render_full_html(spec)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
        tmp.write(html)
        tmp.close()
        webbrowser.open(f"file:///{tmp.name}")

    def _generate(self):
        from tkinter.filedialog import asksaveasfilename
        from tkinter.messagebox import showinfo
        from wireviz_gui.assembly_export import export_manual_zip

        spec = self._build_spec()
        if not spec.referencia:
            showerror("Campo requerido", "La Referencia es obligatoria.")
            return

        default_name = spec.referencia.replace(" ", "_") or "manual"
        path = asksaveasfilename(
            title="Guardar Manual ZIP",
            defaultextension=".zip",
            initialfile=f"manual_{default_name}.zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            result = export_manual_zip(spec, path)
            showinfo("Exportado", f"Manual exportado en:\n{result}")
            self.destroy()
        except Exception as exc:
            showerror("Error", f"Error al exportar:\n{exc}")

    # ── Canvas scroll helpers ──────────────────────────────────────────────

    def _on_frame_configure(self, _event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ─────────────────────────────────────────────────────────────────────────────

def _today() -> str:
    from datetime import date
    return date.today().isoformat()
