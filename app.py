from flask import Flask, request, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from datetime import datetime
import os
import re

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reportes_generados")
LOGO_PATH = os.path.join(BASE_DIR, "static", "logo.jpg")


def safe_filename(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:60] if text else "sin_nombre"


def draw_multiline(c: canvas.Canvas, x, y, text, max_chars=95, line_height=12):
    """
    Dibuja texto en varias líneas haciendo wrap simple por longitud.
    Devuelve la nueva coordenada y (más abajo).
    """
    if text is None:
        text = ""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        while len(paragraph) > max_chars:
            cut = paragraph.rfind(" ", 0, max_chars)
            if cut == -1:
                cut = max_chars
            lines.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        lines.append(paragraph)

    for line in lines:
        c.drawString(x, y, line)
        y -= line_height
    return y


@app.route("/")
def formulario():
    return """
    <html>
    <head><meta charset="utf-8"><title>Reporte Biosford</title></head>
    <body style="font-family: Arial; max-width: 900px; margin: 30px auto;">
        <h2>Reporte de Mantenimiento - Biosford</h2>

        <form method="POST" action="/generar">

            <fieldset style="padding: 12px;">
                <legend><b>Datos del Cliente</b></legend>
                Cliente / IPS: <input type="text" name="cliente" style="width:60%;" required><br><br>
                Sede / Área: <input type="text" name="sede" style="width:60%;"><br><br>
                Contacto: <input type="text" name="contacto" style="width:60%;"><br><br>
                Teléfono / Email: <input type="text" name="telefono" style="width:60%;"><br><br>
            </fieldset><br>

            <fieldset style="padding: 12px;">
                <legend><b>Datos del Equipo</b></legend>
                Equipo: <input type="text" name="equipo" style="width:60%;" required><br><br>
                Marca: <input type="text" name="marca" style="width:60%;"><br><br>
                Modelo: <input type="text" name="modelo" style="width:60%;"><br><br>
                Serial: <input type="text" name="serial" style="width:60%;"><br><br>
                Inventario / Activo fijo: <input type="text" name="inventario" style="width:60%;"><br><br>
                Ubicación exacta: <input type="text" name="ubicacion" style="width:60%;"><br><br>
            </fieldset><br>

            <fieldset style="padding: 12px;">
                <legend><b>Orden / Mantenimiento</b></legend>
                Tipo: 
                <select name="tipo">
                    <option>Correctivo</option>
                    <option>Preventivo</option>
                    <option>Instalación</option>
                    <option>Calibración</option>
                    <option>Diagnóstico</option>
                </select><br><br>

                Prioridad:
                <select name="prioridad">
                    <option>Baja</option>
                    <option>Media</option>
                    <option>Alta</option>
                    <option>Crítica</option>
                </select><br><br>

                Fecha inicio: <input type="date" name="fecha_inicio"><br><br>
                Fecha fin: <input type="date" name="fecha_fin"><br><br>

                Técnico responsable: <input type="text" name="tecnico" style="width:60%;" required><br><br>
            </fieldset><br>

            <fieldset style="padding: 12px;">
                <legend><b>Detalle Técnico</b></legend>
                Falla reportada:<br>
                <textarea name="falla" rows="4" cols="90" required></textarea><br><br>

                Diagnóstico:<br>
                <textarea name="diagnostico" rows="4" cols="90"></textarea><br><br>

                Actividades realizadas:<br>
                <textarea name="actividades" rows="5" cols="90"></textarea><br><br>

                Repuestos / consumibles:<br>
                <textarea name="repuestos" rows="3" cols="90"></textarea><br><br>

                Recomendaciones / observaciones:<br>
                <textarea name="observaciones" rows="4" cols="90"></textarea><br><br>

                Estado final:
                <select name="estado_final">
                    <option>Operativo</option>
                    <option>Operativo con observaciones</option>
                    <option>Fuera de servicio</option>
                    <option>Pendiente repuesto</option>
                </select><br><br>
            </fieldset><br>

            <button type="submit" style="padding:10px 18px; font-size: 16px;">
                Generar PDF Profesional
            </button>
        </form>
    </body>
    </html>
    """


@app.route("/generar", methods=["POST"])
def generar_pdf():
    # Datos
    now = datetime.now()
    fecha_hoy = now.strftime("%Y-%m-%d %H:%M")

    cliente = request.form.get("cliente", "")
    sede = request.form.get("sede", "")
    contacto = request.form.get("contacto", "")
    telefono = request.form.get("telefono", "")

    equipo = request.form.get("equipo", "")
    marca = request.form.get("marca", "")
    modelo = request.form.get("modelo", "")
    serial = request.form.get("serial", "")
    inventario = request.form.get("inventario", "")
    ubicacion = request.form.get("ubicacion", "")

    tipo = request.form.get("tipo", "")
    prioridad = request.form.get("prioridad", "")
    fecha_inicio = request.form.get("fecha_inicio", "")
    fecha_fin = request.form.get("fecha_fin", "")
    tecnico = request.form.get("tecnico", "")

    falla = request.form.get("falla", "")
    diagnostico = request.form.get("diagnostico", "")
    actividades = request.form.get("actividades", "")
    repuestos = request.form.get("repuestos", "")
    observaciones = request.form.get("observaciones", "")
    estado_final = request.form.get("estado_final", "")

    # Carpeta organizada por año/mes
    year = now.strftime("%Y")
    month = now.strftime("%m")
    out_dir = os.path.join(REPORTS_DIR, year, month)
    os.makedirs(out_dir, exist_ok=True)

    # Consecutivo simple (por fecha/hora) - luego lo hacemos tipo BIOS-2026-0001
    consecutivo = now.strftime("%Y%m%d_%H%M%S")

    nombre_base = f"BIOS_{consecutivo}_{safe_filename(cliente)}_{safe_filename(equipo)}"
    nombre_archivo = f"{nombre_base}.pdf"
    ruta_pdf = os.path.join(out_dir, nombre_archivo)

    # PDF
    c = canvas.Canvas(ruta_pdf, pagesize=letter)
    width, height = letter

    margen_x = 2 * cm
    y = height - 2 * cm

    # Encabezado con logo
    if os.path.exists(LOGO_PATH):
        try:
            logo = ImageReader(LOGO_PATH)
            c.drawImage(logo, margen_x, y - 1.6*cm, width=3.2*cm, height=1.6*cm, mask='auto')
        except:
            pass

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margen_x + 3.6*cm, y - 0.4*cm, "REPORTE DE MANTENIMIENTO")
    c.setFont("Helvetica", 10)
    c.drawString(margen_x + 3.6*cm, y - 0.9*cm, "Biosford Sistemas Integrados")
    c.drawString(margen_x + 3.6*cm, y - 1.3*cm, f"Fecha generación: {fecha_hoy}")
    c.drawRightString(width - margen_x, y - 0.4*cm, f"Código: BIOS-{consecutivo}")

    # Línea separadora
    y -= 2.2 * cm
    c.line(margen_x, y, width - margen_x, y)
    y -= 0.6 * cm

    # Bloque: datos cliente/equipo (en “tabla” simple)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margen_x, y, "1. Datos del Cliente")
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)
    c.drawString(margen_x, y, f"Cliente/IPS: {cliente}")
    c.drawString(margen_x + 9*cm, y, f"Sede/Área: {sede}")
    y -= 0.5 * cm
    c.drawString(margen_x, y, f"Contacto: {contacto}")
    c.drawString(margen_x + 9*cm, y, f"Tel/Email: {telefono}")
    y -= 0.8 * cm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margen_x, y, "2. Datos del Equipo")
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)
    c.drawString(margen_x, y, f"Equipo: {equipo}")
    c.drawString(margen_x + 9*cm, y, f"Marca: {marca}")
    y -= 0.5 * cm
    c.drawString(margen_x, y, f"Modelo: {modelo}")
    c.drawString(margen_x + 9*cm, y, f"Serial: {serial}")
    y -= 0.5 * cm
    c.drawString(margen_x, y, f"Inventario/Activo fijo: {inventario}")
    y -= 0.5 * cm
    c.drawString(margen_x, y, f"Ubicación: {ubicacion}")
    y -= 0.8 * cm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margen_x, y, "3. Orden / Mantenimiento")
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)
    c.drawString(margen_x, y, f"Tipo: {tipo}")
    c.drawString(margen_x + 6*cm, y, f"Prioridad: {prioridad}")
    c.drawString(margen_x + 11*cm, y, f"Técnico: {tecnico}")
    y -= 0.5 * cm
    c.drawString(margen_x, y, f"Fecha inicio: {fecha_inicio}")
    c.drawString(margen_x + 6*cm, y, f"Fecha fin: {fecha_fin}")
    y -= 0.8 * cm

    # Secciones largas con wrap
    def section(title, content):
        nonlocal y
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margen_x, y, title)
        y -= 0.5 * cm
        c.setFont("Helvetica", 10)
        y = draw_multiline(c, margen_x, y, content, max_chars=110, line_height=12)
        y -= 0.4 * cm

        # salto de página si se va muy abajo
        if y < 5 * cm:
            c.showPage()
            return height - 2 * cm
        return y

    y = section("4. Falla Reportada", falla)
    y = section("5. Diagnóstico", diagnostico)
    y = section("6. Actividades Realizadas", actividades)
    y = section("7. Repuestos / Consumibles", repuestos)
    y = section("8. Recomendaciones / Observaciones", observaciones)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margen_x, y, "9. Estado Final")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    c.drawString(margen_x, y, f"Estado: {estado_final}")
    y -= 1.2 * cm

    # Firmas (bloque final)
    if y < 6 * cm:
        c.showPage()
        y = height - 2 * cm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margen_x, y, "10. Firmas")
    y -= 1.2 * cm

    # Líneas de firma
    c.line(margen_x, y, margen_x + 7*cm, y)
    c.line(margen_x + 9*cm, y, margen_x + 16*cm, y)
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)
    c.drawString(margen_x, y, "Técnico Biosford")
    c.drawString(margen_x + 9*cm, y, "Recibido por (Cliente)")
    y -= 0.8 * cm

    # Pie de página
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(margen_x, 1.5*cm, "Documento generado por Biosford Sistemas Integrados. Este reporte corresponde a la intervención registrada.")
    c.drawRightString(width - margen_x, 1.5*cm, f"BIOS-{consecutivo}")

    c.save()

    # Enviar al navegador para descargar
    return send_file(ruta_pdf, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)