"""HTML/ZIP exporter for assembly manuals with Torsa visual style."""

import base64
import io
import logging
import sys
import zipfile
from pathlib import Path
from typing import Optional

from jinja2 import BaseLoader, Environment

from wireviz_gui.assembly_spec import BLOCK_TYPES, AssemblyManualSpec

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Logo loader  (works both in dev and in PyInstaller .exe)
# ─────────────────────────────────────────────────────────────────────────────

def _load_logo_b64() -> str:
    """Return the Torsa logo as a base64 JPEG data URI, or empty string on failure."""
    candidates = [
        Path(__file__).parent.parent / "images" / "logo-torsa.jpg",  # dev
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.insert(0, Path(sys._MEIPASS) / "images" / "logo-torsa.jpg")  # type: ignore[attr-defined]

    for p in candidates:
        if p.exists():
            try:
                b64 = base64.b64encode(p.read_bytes()).decode()
                return f"data:image/jpeg;base64,{b64}"
            except Exception:
                pass
    return ""


_LOGO_DATA_URI: str = ""   # lazily loaded on first render


def _get_logo() -> str:
    global _LOGO_DATA_URI
    if not _LOGO_DATA_URI:
        _LOGO_DATA_URI = _load_logo_b64()
    return _LOGO_DATA_URI


# ─────────────────────────────────────────────────────────────────────────────
# Jinja2 template
# ─────────────────────────────────────────────────────────────────────────────

_STYLE = """
@page { size: A4 portrait; margin: 10mm; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10.5pt;
    color: #0d1b2a;
    background: #e8e8e8;
}
/* ── Page ── */
.page {
    width: 190mm;
    min-height: 267mm;
    background: #fff;
    border: 1.5px solid #aaa;
    margin: 8mm auto;
    padding: 0;
    page-break-after: always;
    position: relative;
    display: flex;
    flex-direction: column;
}
.page:last-child { page-break-after: avoid; }
/* ── Header ── */
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #0d1b2a;
    padding: 6px 14px;
    min-height: 80px;
    background: #fff;
}
.header-logo img { height: 90px; max-height: 90px; }
.header-logo-text {
    font-size: 20pt;
    font-weight: 900;
    color: #0d1b2a;
    letter-spacing: -1px;
}
.header-ref {
    border: 3px solid #0d1b2a;
    padding: 8px 20px;
    font-size: 14pt;
    font-weight: bold;
    color: #0d1b2a;
    letter-spacing: 0.5px;
}
/* ── Content ── */
.content {
    flex: 1;
    padding: 14px 16px 10px 16px;
    display: flex;
    flex-direction: column;
}
.step-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 12px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 6px;
}
.step-title {
    font-size: 14pt;
    font-weight: bold;
    color: #0d1b2a;
    text-transform: uppercase;
}
.step-counter {
    font-size: 9pt;
    color: #666;
}
/* ── Tables ── */
.info-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 9.5pt;
}
.info-table th {
    background: #0d1b2a;
    color: #fff;
    padding: 5px 10px;
    text-align: left;
    width: 42%;
    font-weight: normal;
}
.info-table td {
    border: 1px solid #ccc;
    padding: 5px 10px;
}
.info-table tr:nth-child(even) td { background: #f8f8f8; }
/* ── Highlight boxes ── */
.box-blue {
    background: #ddeeff;
    border: 2px solid #0066cc;
    border-radius: 6px;
    padding: 10px 16px;
    margin: 10px 0;
    text-align: center;
    font-size: 13pt;
    font-weight: bold;
    color: #003380;
}
.box-red {
    background: #fde2e2;
    border-left: 5px solid #e30613;
    padding: 8px 12px;
    margin: 8px 0;
    font-weight: bold;
    font-size: 10pt;
    color: #8b0000;
}
.box-yellow {
    background: #fff8cc;
    border-left: 5px solid #e6b800;
    padding: 8px 12px;
    margin: 8px 0;
    font-size: 10pt;
}
.box-green {
    background: #d4edda;
    border: 2px solid #28a745;
    border-radius: 6px;
    padding: 10px 16px;
    margin: 10px 0;
    text-align: center;
    font-size: 12pt;
    font-weight: bold;
    color: #155724;
}
/* ── Images ── */
.images-grid {
    flex: 1;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 8px 0 0 0;
    justify-content: center;
    align-items: center;
    align-content: center;
}
.images-grid img {
    max-width: 100%;
    max-height: 200mm;
    border: none;
    object-fit: contain;
    display: block;
    margin: 2px auto;
}
/* ── Footer ── */
.footer {
    border-top: 1px solid #ccc;
    padding: 4px 14px;
    font-size: 7.5pt;
    color: #888;
    display: flex;
    justify-content: space-between;
    background: #fafafa;
}
"""

_PAGE_TEMPLATE = r"""
<div class="page">
  <div class="header">
    <div class="header-logo">
      {% if logo_uri %}
        <img src="{{ logo_uri }}" alt="TORSA">
      {% else %}
        <span class="header-logo-text">TORSA</span>
      {% endif %}
    </div>
    <div class="header-ref">{{ spec.referencia }}</div>
  </div>

  <div class="content">
    <div class="step-header">
      <div class="step-title">{{ block.title }}</div>
      <div class="step-counter">Paso {{ block.step_number }} de {{ block.total }}</div>
    </div>

    {# ── CORTE ── #}
    {% if block.block_type == "Corte" %}
      <table class="info-table">
        {% if block.fields.pn_cable %}<tr><th>PN Cable</th><td>{{ block.fields.pn_cable }}</td></tr>{% endif %}
        {% if block.fields.programa_cortadora %}<tr><th>Programa cortadora</th><td>{{ block.fields.programa_cortadora }}</td></tr>{% endif %}
      </table>
      {% if block.fields.longitud_mm %}
      <div class="box-blue">LONGITUD DEL CABLE: {{ block.fields.longitud_mm }} mm</div>
      {% endif %}
      {% if block.fields.notas %}
      <div class="box-yellow">{{ block.fields.notas }}</div>
      {% endif %}

    {# ── PROCESADO ── #}
    {% elif block.block_type == "Procesado" %}
      <table class="info-table">
        {% if block.fields.extremo %}<tr><th>Extremo</th><td><b>{{ block.fields.extremo }}</b></td></tr>{% endif %}
        {% if block.fields.seccion_mm2 or block.fields.awg %}
        <tr><th>Sección / AWG</th><td>{{ block.fields.seccion_mm2 }} mm² &nbsp;/&nbsp; AWG {{ block.fields.awg }}</td></tr>
        {% endif %}
        {% if block.fields.funda_mm %}<tr><th>Desforre funda exterior</th><td>{{ block.fields.funda_mm }} mm</td></tr>{% endif %}
        {% if block.fields.camisa_mm %}<tr><th>Desforre camisa hilos</th><td>{{ block.fields.camisa_mm }} mm</td></tr>{% endif %}
        {% if block.fields.programa_peladora %}<tr><th>Programa peladora</th><td>{{ block.fields.programa_peladora }}</td></tr>{% endif %}
      </table>

    {# ── CRIMPADO ── #}
    {% elif block.block_type == "Crimpado" %}
      <table class="info-table">
        {% if block.fields.extremo %}<tr><th>Extremo</th><td><b>{{ block.fields.extremo }}</b></td></tr>{% endif %}
        {% if block.fields.pn_pin %}<tr><th>PN Pin / Terminal</th><td>{{ block.fields.pn_pin }}</td></tr>{% endif %}
        {% if block.fields.ref_crimpado %}<tr><th>Molde / Referencia</th><td>{{ block.fields.ref_crimpado }}</td></tr>{% endif %}
        {% if block.fields.parametros %}<tr><th>Parámetros</th><td>{{ block.fields.parametros }}</td></tr>{% endif %}
        {% if block.fields.programa_crimpadora %}<tr><th>Programa crimpadora</th><td>{{ block.fields.programa_crimpadora }}</td></tr>{% endif %}
      </table>
      {% if block.fields.crimp_sobre_funda %}
      <div class="box-red">⚠ DEBE ESTAR CRIMPADO SOBRE LA FUNDA</div>
      {% endif %}
      {% if block.fields.crimp_sobre_conductores %}
      <div class="box-red">⚠ DEBE ESTAR CRIMPADO SOBRE LOS CONDUCTORES</div>
      {% endif %}
      <div class="box-yellow">🔍 Revisión visual de cada terminal</div>

    {# ── TRAZABILIDAD ── #}
    {% elif block.block_type == "Trazabilidad" %}
      <table class="info-table">
        {% if block.fields.extremo %}<tr><th>Extremo</th><td><b>{{ block.fields.extremo }}</b></td></tr>{% endif %}
        {% if block.fields.tamaño_label_mm %}<tr><th>Tamaño label</th><td>{{ block.fields.tamaño_label_mm }} mm</td></tr>{% endif %}
      </table>
      {% if block.fields.texto_label %}
      <div class="box-blue">{{ block.fields.texto_label }}</div>
      {% endif %}

    {# ── MONTAJE CONECTOR ── #}
    {% elif block.block_type == "Montaje conector" %}
      <table class="info-table">
        {% if block.fields.extremo %}<tr><th>Extremo</th><td><b>{{ block.fields.extremo }}</b></td></tr>{% endif %}
        {% if block.fields.pn_conector %}<tr><th>PN Conector</th><td>{{ block.fields.pn_conector }}</td></tr>{% endif %}
        {% if block.fields.has_lock %}
        <tr><th>Lock</th><td>SÍ — Verificar que el lock está cerrado correctamente</td></tr>
        {% endif %}
      </table>
      {% if block.fields.observaciones %}
      <div class="box-yellow">{{ block.fields.observaciones }}</div>
      {% endif %}

    {# ── TEST ── #}
    {% elif block.block_type == "Test" %}
      <table class="info-table">
        {% if block.fields.tipo_test %}<tr><th>Tipo de test</th><td>{{ block.fields.tipo_test }}</td></tr>{% endif %}
        {% if block.fields.ubicacion_test %}<tr><th>Ubicación</th><td>{{ block.fields.ubicacion_test }}</td></tr>{% endif %}
        {% if block.fields.equipo_test %}<tr><th>Equipo / Adaptador</th><td>{{ block.fields.equipo_test }}</td></tr>{% endif %}
        {% if block.fields.criterio_aprobado %}<tr><th>Criterio aprobado</th><td>{{ block.fields.criterio_aprobado }}</td></tr>{% endif %}
      </table>
      <div class="box-green">✔ VERIFICAR CONTINUIDAD DE TODOS LOS PINES</div>

    {# ── EMBALAJE ── #}
    {% elif block.block_type == "Embalaje" %}
      <table class="info-table">
        {% if block.fields.pn_bolsa %}<tr><th>PN Bolsa</th><td>{{ block.fields.pn_bolsa }}</td></tr>{% endif %}
        {% if block.fields.tipo_bolsa %}<tr><th>Tipo de bolsa</th><td>{{ block.fields.tipo_bolsa }}</td></tr>{% endif %}
        {% if block.fields.unidades_por_bolsa %}<tr><th>Unidades por bolsa</th><td>{{ block.fields.unidades_por_bolsa }}</td></tr>{% endif %}
        {% if block.fields.observaciones %}<tr><th>Observaciones</th><td>{{ block.fields.observaciones }}</td></tr>{% endif %}
      </table>

    {# ── PERSONALIZADO ── #}
    {% else %}
      {% if block.fields.instrucciones %}
      <div class="box-yellow" style="white-space:pre-wrap;">{{ block.fields.instrucciones }}</div>
      {% endif %}
    {% endif %}

    {# ── IMAGES (all types) ── #}
    {% if block.images %}
    <div class="images-grid">
      {% for img in block.images %}
      <img src="{{ img.data_uri }}" alt="{{ img.name }}">
      {% endfor %}
    </div>
    {% endif %}

  </div>{# end content #}

  <div class="footer">
    <span>Rev. {{ spec.revision }} &nbsp;|&nbsp; {{ spec.fecha }} &nbsp;|&nbsp; {{ spec.autor }}</span>
    <span>{{ spec.referencia }} — Paso {{ block.step_number }} / {{ block.total }}</span>
  </div>
</div>
"""

_FULL_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Manual {{ spec.referencia }}</title>
<style>{{ style }}</style>
</head>
<body>
{% for block in blocks %}
""" + _PAGE_TEMPLATE + r"""
{% endfor %}
</body>
</html>
"""

_SINGLE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{{ spec.referencia }} — Paso {{ block.step_number }}</title>
<style>{{ style }}</style>
</head>
<body>
""" + _PAGE_TEMPLATE + r"""
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_env() -> Environment:
    env = Environment(loader=BaseLoader(), autoescape=True)
    return env


def render_full_html(spec: AssemblyManualSpec) -> str:
    """Render all steps as a single self-contained HTML file."""
    env = _make_env()
    tmpl = env.from_string(_FULL_TEMPLATE)
    return tmpl.render(
        spec=spec,
        blocks=spec.numbered_blocks(),
        style=_STYLE,
        logo_uri=_get_logo(),
    )


def render_step_html(spec: AssemblyManualSpec, block_dict: dict) -> str:
    """Render a single step as a self-contained HTML file."""
    env = _make_env()
    tmpl = env.from_string(_SINGLE_TEMPLATE)
    return tmpl.render(
        spec=spec,
        block=block_dict,
        style=_STYLE,
        logo_uri=_get_logo(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ZIP export
# ─────────────────────────────────────────────────────────────────────────────

def _safe_filename(text: str, maxlen: int = 40) -> str:
    import re
    s = re.sub(r"[^\w\-. ]", "", text).strip().replace(" ", "_")
    return s[:maxlen] or "paso"


def export_manual_zip(spec: AssemblyManualSpec, output_path: str) -> str:
    """
    Export the assembly manual as a ZIP file containing:
      - manual_completo.html          (all steps, self-contained)
      - paso_XX_<title>.html          (one per step, self-contained)
      - images/logo-torsa.jpg         (logo file for reference)
    Optional (if weasyprint available):
      - manual_completo.pdf
      - paso_XX_<title>.pdf
    """
    blocks = spec.numbered_blocks()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:

        # ── Combined HTML ──────────────────────────────────────────────────
        full_html = render_full_html(spec)
        zf.writestr("manual_completo.html", full_html.encode("utf-8"))

        # ── Individual step HTMLs ──────────────────────────────────────────
        for block in blocks:
            n = block["step_number"]
            fname = f"paso_{n:02d}_{_safe_filename(block['title'])}.html"
            html = render_step_html(spec, block)
            zf.writestr(fname, html.encode("utf-8"))

        # ── Logo image (original file, for external reference) ─────────────
        candidates = [
            Path(__file__).parent.parent / "images" / "logo-torsa.jpg",
        ]
        if hasattr(sys, "_MEIPASS"):
            candidates.insert(0, Path(sys._MEIPASS) / "images" / "logo-torsa.jpg")  # type: ignore[attr-defined]
        for p in candidates:
            if p.exists():
                zf.write(p, "images/logo-torsa.jpg")
                break

        # ── Optional PDF export ────────────────────────────────────────────
        pdf_ok = _try_pdf_export(spec, blocks, zf)
        if not pdf_ok:
            logger.info("WeasyPrint not available — PDFs skipped. Open HTML in browser to print PDF.")

    return output_path


def _try_pdf_export(spec: AssemblyManualSpec, blocks: list, zf: zipfile.ZipFile) -> bool:
    """Try to add PDFs to the zip. Returns True if successful."""
    try:
        from weasyprint import HTML as WP_HTML  # type: ignore[import]
    except ImportError:
        return False

    try:
        # Combined PDF
        full_html = render_full_html(spec)
        pdf_bytes = WP_HTML(string=full_html).write_pdf()
        zf.writestr("manual_completo.pdf", pdf_bytes)

        # Individual PDFs
        for block in blocks:
            n = block["step_number"]
            fname = f"paso_{n:02d}_{_safe_filename(block['title'])}.pdf"
            html = render_step_html(spec, block)
            pdf_bytes = WP_HTML(string=html).write_pdf()
            zf.writestr(fname, pdf_bytes)

        return True
    except Exception as exc:
        logger.warning("PDF export failed: %s", exc)
        return False
