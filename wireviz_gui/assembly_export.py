"""HTML template and PDF generator for assembly manuals."""

import logging
from datetime import date
from pathlib import Path
from typing import Optional

from jinja2 import Environment, BaseLoader

from wireviz_gui.assembly_spec import (
    AssemblyManualSpec,
    CuttingSpec,
    EndSpec,
    PackagingSpec,
    TestSpec,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Jinja2 HTML Template
# ─────────────────────────────────────────────────────────

MANUAL_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Manual {{ spec.referencia }}</title>
<style>
@page {
    size: A4 portrait;
    margin: 10mm;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt;
    color: #222;
}
.page {
    width: 190mm;
    min-height: 267mm;
    border: 2px solid #333;
    margin: 10mm auto;
    padding: 0;
    page-break-after: always;
    position: relative;
}
.page:last-child { page-break-after: avoid; }

/* Header */
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #333;
    padding: 6px 12px;
    min-height: 40px;
}
.header-logo {
    font-size: 18pt;
    font-weight: bold;
    color: #c00;
}
.header-ref {
    background: #003366;
    color: white;
    padding: 6px 16px;
    font-size: 12pt;
    font-weight: bold;
    border-radius: 4px;
}

/* Footer */
.footer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    border-top: 1px solid #999;
    padding: 4px 12px;
    font-size: 8pt;
    color: #666;
    display: flex;
    justify-content: space-between;
}

/* Content */
.content {
    padding: 12px 16px;
    padding-bottom: 30px;
}
.step-title {
    font-size: 14pt;
    font-weight: bold;
    margin-bottom: 12px;
    color: #003366;
}
.step-counter {
    font-size: 9pt;
    color: #666;
    float: right;
}

/* Tables */
.info-table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
}
.info-table td, .info-table th {
    border: 1px solid #ccc;
    padding: 6px 10px;
    text-align: left;
    font-size: 10pt;
}
.info-table th {
    background: #eef;
    font-weight: bold;
    width: 40%;
}

/* Highlight boxes */
.highlight-box {
    background: #ddeeff;
    border: 2px solid #0066cc;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 8px 0;
    text-align: center;
    font-size: 13pt;
    font-weight: bold;
}
.highlight-box.red {
    background: #ffe0e0;
    border-color: #cc0000;
    color: #cc0000;
}
.highlight-box.green {
    background: #e0ffe0;
    border-color: #009900;
    color: #006600;
}

/* Strip diagram */
.strip-diagram {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 12px 0;
    gap: 4px;
}
.strip-segment {
    height: 20px;
    background: #333;
    border-radius: 2px;
}
.strip-segment.bare {
    background: #cc8800;
}
.strip-label {
    font-size: 9pt;
    text-align: center;
    margin-top: 2px;
}

/* Pin assignment table */
.pin-table {
    width: 80%;
    margin: 12px auto;
    border-collapse: collapse;
}
.pin-table td, .pin-table th {
    border: 1px solid #999;
    padding: 5px 8px;
    text-align: center;
    font-size: 10pt;
}
.pin-table th { background: #ddd; }

/* Notes */
.note {
    background: #fff8e0;
    border-left: 4px solid #ffaa00;
    padding: 8px 12px;
    margin: 8px 0;
    font-size: 10pt;
}
.warning {
    background: #ffe8e8;
    border-left: 4px solid #cc0000;
    padding: 8px 12px;
    margin: 8px 0;
    font-size: 10pt;
    font-weight: bold;
}
</style>
</head>
<body>

{% for step in steps %}
<div class="page">
    <div class="header">
        <div class="header-logo">TORSA &#x27B0;</div>
        <div class="header-ref">{{ spec.referencia }}</div>
    </div>

    <div class="content">
        <div class="step-counter">Paso {{ step.numero }} de {{ step.total }}</div>

        {% if step.tipo == "corte" %}
        <div class="step-title">CORTE DEL CABLE</div>
        <table class="info-table">
            <tr><th>PN Cable</th><td>{{ step.data.pn_cable }}</td></tr>
            <tr><th>Programa cortadora</th><td>{{ step.data.programa_cortadora }}</td></tr>
        </table>
        <div class="highlight-box">
            LONGITUD DEL CABLE: {{ step.data.longitud_total_mm }} mm
        </div>
        {% if step.data.notas_corte %}
        <div class="note">{{ step.data.notas_corte }}</div>
        {% endif %}

        {% elif step.tipo == "procesado" %}
        <div class="step-title">PROCESADO {{ step.data.nombre | upper }}</div>
        <table class="info-table">
            <tr><th>Sección</th><td>{{ step.data.stripping.seccion_mm2 }} mm² / AWG {{ step.data.stripping.awg }}</td></tr>
            <tr><th>Desforre funda exterior</th><td>{{ step.data.stripping.longitud_desforre_funda_mm }} mm</td></tr>
            <tr><th>Desforre camisa hilos</th><td>{{ step.data.stripping.longitud_desforre_camisa_mm }} mm</td></tr>
            <tr><th>Programa peladora</th><td>{{ step.data.stripping.programa_peladora }}</td></tr>
        </table>

        <!-- Visual strip diagram -->
        <div style="text-align:center; margin: 16px 0;">
            <svg width="320" height="60" viewBox="0 0 320 60">
                <!-- Funda -->
                <rect x="10" y="20" width="120" height="20" fill="#222" rx="3"/>
                <!-- Bare area funda -->
                <rect x="130" y="20" width="{{ (step.data.stripping.longitud_desforre_funda_mm / (step.data.stripping.longitud_desforre_funda_mm + 20)) * 180 }}" height="20" fill="#999" rx="2"/>
                <!-- Dimension funda -->
                <line x1="130" y1="10" x2="{{ 130 + (step.data.stripping.longitud_desforre_funda_mm / (step.data.stripping.longitud_desforre_funda_mm + 20)) * 180 }}" y1="10" stroke="#0066cc" stroke-width="1.5"/>
                <text x="{{ 130 + (step.data.stripping.longitud_desforre_funda_mm / (step.data.stripping.longitud_desforre_funda_mm + 20)) * 90 }}" y="8" text-anchor="middle" font-size="9" fill="#0066cc">{{ step.data.stripping.longitud_desforre_funda_mm }}mm</text>
                <!-- Dimension camisa -->
                <line x1="{{ 130 + (step.data.stripping.longitud_desforre_funda_mm / (step.data.stripping.longitud_desforre_funda_mm + 20)) * 180 - (step.data.stripping.longitud_desforre_camisa_mm / (step.data.stripping.longitud_desforre_funda_mm + 20)) * 180 }}" y1="50" x2="{{ 130 + (step.data.stripping.longitud_desforre_funda_mm / (step.data.stripping.longitud_desforre_funda_mm + 20)) * 180 }}" y1="50" stroke="#cc0000" stroke-width="1.5"/>
                <text x="{{ 130 + (step.data.stripping.longitud_desforre_funda_mm / (step.data.stripping.longitud_desforre_funda_mm + 20)) * 180 - (step.data.stripping.longitud_desforre_camisa_mm / (step.data.stripping.longitud_desforre_funda_mm + 20)) * 90 }}" y="57" text-anchor="middle" font-size="9" fill="#cc0000">{{ step.data.stripping.longitud_desforre_camisa_mm }}mm</text>
            </svg>
        </div>

        {% elif step.tipo == "crimpado" %}
        <div class="step-title">CRIMPADO TERMINALES {{ step.data.nombre | upper }}</div>
        <table class="info-table">
            <tr><th>PN Pin / Terminal</th><td>{{ step.data.crimping.pn_pin }}</td></tr>
            <tr><th>Molde / Referencia</th><td>{{ step.data.crimping.ref_crimpado }}</td></tr>
            <tr><th>Parámetros</th><td>{{ step.data.crimping.parametros_crimpado }}</td></tr>
            <tr><th>Programa crimpadora</th><td>{{ step.data.crimping.programa_crimpadora }}</td></tr>
        </table>

        {% if step.data.crimping.crimp_sobre_funda %}
        <div class="warning">DEBE ESTAR CRIMPADO SOBRE LA FUNDA</div>
        {% endif %}
        {% if step.data.crimping.crimp_sobre_conductores %}
        <div class="warning">DEBE ESTAR CRIMPADO SOBRE LOS CONDUCTORES</div>
        {% endif %}
        <div class="note">Revisión visual de cada terminal</div>

        {% elif step.tipo == "trazabilidad" %}
        <div class="step-title">TRAZABILIDAD {{ step.data.nombre | upper }}</div>
        <div class="highlight-box">
            {{ step.data.traceability.texto }}
        </div>
        <table class="info-table">
            <tr><th>Tamaño label</th><td>{{ step.data.traceability.tamaño_label_mm }} mm</td></tr>
        </table>

        {% elif step.tipo == "montaje_conector" %}
        <div class="step-title">MONTAJE CONECTOR {{ step.data.nombre | upper }}</div>
        <table class="info-table">
            <tr><th>PN Conector</th><td>{{ step.data.connector.pn_conector }}</td></tr>
            {% if step.data.connector.has_lock %}
            <tr><th>Lock</th><td>SÍ - Verificar que el lock está cerrado</td></tr>
            {% endif %}
        </table>

        {% if step.data.connector.observaciones %}
        <div class="note">{{ step.data.connector.observaciones }}</div>
        {% endif %}

        {% if step.data.finish.punteras %}
        <div class="note">Punteras: {{ step.data.finish.pn_punteras }}</div>
        {% endif %}
        {% if step.data.finish.termoretractil %}
        <div class="note">Termorretráctil: {{ step.data.finish.pn_termoretractil }}</div>
        {% endif %}
        {% if step.data.finish.prestanado %}
        <div class="note">Prestañado requerido</div>
        {% endif %}

        {% elif step.tipo == "test" %}
        <div class="step-title">TEST DE FUNCIONAMIENTO</div>
        <table class="info-table">
            <tr><th>Tipo de test</th><td>{{ step.data.tipo_test }}</td></tr>
            <tr><th>Ubicación</th><td>{{ step.data.ubicacion_test }}</td></tr>
            <tr><th>Equipo</th><td>{{ step.data.equipo_test }}</td></tr>
            <tr><th>Criterio aprobado</th><td>{{ step.data.criterio_aprobado }}</td></tr>
        </table>
        <div class="highlight-box green">VERIFICAR CONTINUIDAD DE TODOS LOS PINES</div>

        {% elif step.tipo == "packaging" %}
        <div class="step-title">EMBALAJE</div>
        <table class="info-table">
            <tr><th>PN Bolsa</th><td>{{ step.data.pn_bolsa }}</td></tr>
            <tr><th>Tipo</th><td>{{ step.data.tipo_bolsa }}</td></tr>
            <tr><th>Unidades por bolsa</th><td>{{ step.data.unidades_por_bolsa }}</td></tr>
        </table>
        {% if step.data.observaciones %}
        <div class="note">{{ step.data.observaciones }}</div>
        {% endif %}

        {% endif %}
    </div>

    <div class="footer">
        <span>Rev. {{ spec.revision }} | {{ spec.fecha }} | {{ spec.autor }}</span>
        <span>{{ spec.referencia }} — Paso {{ step.numero }}/{{ step.total }}</span>
    </div>
</div>
{% endfor %}

</body>
</html>
"""


def render_manual_html(spec: AssemblyManualSpec) -> str:
    """Render the assembly manual as an HTML string."""
    env = Environment(loader=BaseLoader(), autoescape=True)
    template = env.from_string(MANUAL_HTML_TEMPLATE)

    steps = spec.generate_steps()

    return template.render(spec=spec, steps=steps)


def export_manual_pdf(spec: AssemblyManualSpec, output_path: str) -> str:
    """Export the assembly manual as a PDF file.

    Returns the path to the generated PDF.
    """
    html_content = render_manual_html(spec)

    # First try WeasyPrint (better quality), fallback to html-to-file approach
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
        return output_path
    except ImportError:
        pass

    # Fallback: save as HTML (user can print to PDF from browser)
    html_path = output_path.replace(".pdf", ".html")
    Path(html_path).write_text(html_content, encoding="utf-8")
    logger.warning("WeasyPrint not available. Saved as HTML: %s", html_path)
    return html_path


def export_manual_html(spec: AssemblyManualSpec, output_path: str) -> str:
    """Export the assembly manual as an HTML file."""
    html_content = render_manual_html(spec)
    Path(output_path).write_text(html_content, encoding="utf-8")
    return output_path
