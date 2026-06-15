import csv
import os
import html
from datetime import datetime

from qgis.PyQt.QtGui import QTextDocument, QPageLayout, QPageSize
from qgis.PyQt.QtPrintSupport import QPrinter


def _safe_export_path(folder, base_name, extension):
    return os.path.join(folder, f"{base_name}{extension}")


def _fallback_export_path(folder, base_name, extension):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(folder, f"{base_name}_{timestamp}{extension}")


def _format_csv_tal(verdi):
    try:
        return f"{float(verdi):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return ""


def _format_csv_tekst(verdi):
    if verdi is None:
        return ""
    return str(verdi)


def _format_csv_excel_tekst(verdi):
    if verdi is None:
        return ""
    tekst = str(verdi)
    return f'="{tekst}"'


def skriv_csv(csv_fil, rader):
    headers = [
        "Driftsomrade nummer",
        "Hogstmoden i perioden",
        "Driftsmetode",
        "Volum gran i 2025",
        "Volum furu i 2025",
        "Volum lauv i 2025",
        "Volum sum i 2025",
        "Berekna total volum nar skogen vert hogstmoden",
        "MERK",
        "MERKNAD",
    ]

    with open(csv_fil, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers)
        for rad in rader:
            writer.writerow(
                [
                    _format_csv_excel_tekst(rad.get("drift_nr")),
                    _format_csv_excel_tekst(rad.get("periode")),
                    _format_csv_tekst(rad.get("driftm")),
                    _format_csv_tal(rad.get("gran_2025")),
                    _format_csv_tal(rad.get("furu_2025")),
                    _format_csv_tal(rad.get("lauv_2025")),
                    _format_csv_tal(rad.get("sum_2025")),
                    _format_csv_tal(rad.get("hogstmoden")),
                    _format_csv_tekst(rad.get("merk")),
                    _format_csv_tekst(rad.get("merknad")),
                ]
            )


def skriv_csv_robust(folder, base_name, rader):
    os.makedirs(folder, exist_ok=True)

    forste = _safe_export_path(folder, base_name, ".csv")
    try:
        skriv_csv(forste, rader)
        return forste
    except PermissionError:
        reserve = _fallback_export_path(folder, base_name, ".csv")
        skriv_csv(reserve, rader)
        return reserve
    except OSError:
        reserve = _fallback_export_path(folder, base_name, ".csv")
        skriv_csv(reserve, rader)
        return reserve


def bygg_html_rapport(rader, takstlag_namn, driftslag_namn, filter_periodar, filter_metodar):
    total_gran = sum(r["gran_2025"] for r in rader)
    total_furu = sum(r["furu_2025"] for r in rader)
    total_lauv = sum(r["lauv_2025"] for r in rader)
    total_sum = sum(r["sum_2025"] for r in rader)
    total_hogstmoden = sum(r["hogstmoden"] for r in rader)

    periode_txt = ", ".join(filter_periodar) if filter_periodar else "Alle"
    metode_txt = ", ".join(filter_metodar) if filter_metodar else "Alle"

    rows_html = []
    for r in rader:
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(str(r['drift_nr'] or ''))}</td>"
            f"<td>{html.escape(str(r['periode'] or ''))}</td>"
            f"<td>{html.escape(str(r['driftm'] or ''))}</td>"
            f"<td class='num'>{r['gran_2025']:.2f}</td>"
            f"<td class='num'>{r['furu_2025']:.2f}</td>"
            f"<td class='num'>{r['lauv_2025']:.2f}</td>"
            f"<td class='num'>{r['sum_2025']:.2f}</td>"
            f"<td class='num'>{r['hogstmoden']:.2f}</td>"
            f"<td>{html.escape(str(r['merk'] or ''))}</td>"
            f"<td>{html.escape(str(r['merknad'] or ''))}</td>"
            "</tr>"
        )

    html_txt = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        @page {{
          size: A4 landscape;
          margin: 10mm;
        }}
        body {{
          font-family: Arial, sans-serif;
          font-size: 8pt;
          margin: 0;
          padding: 0;
        }}
        h1 {{
          font-size: 16pt;
          margin: 0 0 8px 0;
        }}
        h2 {{
          font-size: 11pt;
          margin: 12px 0 6px 0;
        }}
        p, div {{
          margin: 0 0 6px 0;
        }}
        table {{
          border-collapse: collapse;
          width: 100%;
          font-size: 7pt;
          table-layout: fixed;
        }}
        th, td {{
          border: 1px solid #666;
          padding: 3px;
          vertical-align: top;
          word-wrap: break-word;
        }}
        th {{
          background: #e8e8e8;
        }}
        .num {{
          text-align: right;
          white-space: nowrap;
        }}
        .meta {{
          margin-bottom: 10px;
        }}
        .totaltabell {{
          width: 55%;
          margin-bottom: 14px;
          table-layout: auto;
        }}
      </style>
    </head>
    <body>
      <h1>Hogstplan</h1>

      <div class="meta">
        <b>Takstlag:</b> {html.escape(takstlag_namn)}<br>
        <b>Driftsmetodelag:</b> {html.escape(driftslag_namn)}<br>
        <b>Volumfelt:</b> staande volum i 2025<br>
        <b>Periodar:</b> {html.escape(periode_txt)}<br>
        <b>Driftsmetodar:</b> {html.escape(metode_txt)}
      </div>

      <h2>Samandrag</h2>
      <table class="totaltabell">
        <tr><th>Storleik</th><th>Verdi</th></tr>
        <tr><td>Tal driftsomrade</td><td class='num'>{len(rader)}</td></tr>
        <tr><td>Volum gran i 2025</td><td class='num'>{total_gran:.2f}</td></tr>
        <tr><td>Volum furu i 2025</td><td class='num'>{total_furu:.2f}</td></tr>
        <tr><td>Volum lauv i 2025</td><td class='num'>{total_lauv:.2f}</td></tr>
        <tr><td>Volum sum i 2025</td><td class='num'>{total_sum:.2f}</td></tr>
        <tr><td>Berekna total volum nar skogen vert hogstmoden</td><td class='num'>{total_hogstmoden:.2f}</td></tr>
      </table>

      <h2>Driftsomrade</h2>
      <table>
        <thead>
          <tr>
            <th style="width:5%;">Nr</th>
            <th style="width:9%;">Hogstmoden periode</th>
            <th style="width:10%;">Driftsmetode</th>
            <th style="width:8%;">Gran 2025</th>
            <th style="width:8%;">Furu 2025</th>
            <th style="width:8%;">Lauv 2025</th>
            <th style="width:8%;">Sum 2025</th>
            <th style="width:12%;">Volum ved hogstmodenheit</th>
            <th style="width:15%;">MERK</th>
            <th style="width:17%;">MERKNAD</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
    </body>
    </html>
    """
    return html_txt


def skriv_pdf(pdf_fil, html_txt):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(pdf_fil)
    printer.setPageSize(QPageSize(QPageSize.A4))
    printer.setPageOrientation(QPageLayout.Landscape)
    printer.setFullPage(False)

    doc = QTextDocument()
    doc.setHtml(html_txt)
    doc.print_(printer)


def skriv_pdf_robust(folder, base_name, html_txt):
    os.makedirs(folder, exist_ok=True)

    forste = _safe_export_path(folder, base_name, ".pdf")
    try:
        skriv_pdf(forste, html_txt)
        return forste
    except PermissionError:
        reserve = _fallback_export_path(folder, base_name, ".pdf")
        skriv_pdf(reserve, html_txt)
        return reserve
    except OSError:
        reserve = _fallback_export_path(folder, base_name, ".pdf")
        skriv_pdf(reserve, html_txt)
        return reserve
