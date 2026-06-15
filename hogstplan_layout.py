import os
import tempfile
from datetime import datetime

from qgis.PyQt.QtCore import QSize, Qt, QRectF, QPointF
from qgis.PyQt.QtGui import (
    QImage,
    QPainter,
    QColor,
    QPageLayout,
    QPageSize,
    QFont,
    QPen,
    QBrush,
    QFontMetrics,
    QPolygonF,
)
from qgis.PyQt.QtPrintSupport import QPrinter

from qgis.core import (
    QgsProject,
    QgsMapSettings,
    QgsMapRendererCustomPainterJob,
)

from .hogstplan_export import _safe_export_path, _fallback_export_path
from .hogstplan_style import periode_farge


def _synlege_kartlag_med_resultat_ovst(resultatlag):
    prosjekt = QgsProject.instance()
    root = prosjekt.layerTreeRoot()
    synlege_lag = []

    def _samle_synlege_lag(node):
        for child in node.children():
            if hasattr(child, "children"):
                _samle_synlege_lag(child)

            layer = getattr(child, "layer", lambda: None)()
            if layer is not None and child.isVisible() and child.isItemVisibilityCheckedRecursive():
                synlege_lag.append(layer)

    _samle_synlege_lag(root)

    lagliste = []
    if resultatlag is not None:
        lagliste.append(resultatlag)

    for lag in synlege_lag:
        if resultatlag is not None and lag.id() == resultatlag.id():
            continue
        lagliste.append(lag)

    return lagliste


def _lag_kartbilete_med_mapsettings(resultatlag, png_fil):
    if resultatlag is None:
        raise Exception("Manglar resultatlag for kartbilete.")

    extent = resultatlag.extent()
    if extent is None or extent.isEmpty():
        raise Exception("Resultatlaget har tom extent og kan ikkje teiknast.")

    kart_extent = extent
    kart_extent.scale(1.55)

    biletstorleik = QSize(2600, 1700)

    settings = QgsMapSettings()
    settings.setLayers(_synlege_kartlag_med_resultat_ovst(resultatlag))
    settings.setExtent(kart_extent)
    settings.setOutputSize(biletstorleik)
    settings.setBackgroundColor(QColor(255, 255, 255))
    settings.setDestinationCrs(resultatlag.crs())

    image = QImage(biletstorleik, QImage.Format_ARGB32)
    image.fill(Qt.white)

    painter = QPainter(image)
    try:
        job = QgsMapRendererCustomPainterJob(settings, painter)
        job.start()
        job.waitForFinished()
    finally:
        painter.end()

    if image.isNull():
        raise Exception("Kartbiletet vart tomt etter rendering.")

    if not image.save(png_fil, "PNG"):
        raise Exception("Klarte ikkje a lagre kartbilete som PNG.")


def _hent_periodar_fra_resultatlag(resultatlag):
    if resultatlag is None:
        return []

    idx = resultatlag.fields().indexOf("periode")
    if idx < 0:
        return []

    verdiar = resultatlag.uniqueValues(idx)
    return sorted([str(v).strip() for v in verdiar if v is not None and str(v).strip()])


def _lag_forklaringsbilete(resultatlag):
    periodar = _hent_periodar_fra_resultatlag(resultatlag)
    if not periodar:
        return None

    title_font = QFont("Arial", 20)
    text_font = QFont("Arial", 16)

    temp_image = QImage(10, 10, QImage.Format_ARGB32)
    temp_painter = QPainter(temp_image)
    title_metrics = QFontMetrics(title_font)
    text_metrics = QFontMetrics(text_font)

    tittel = "Hogstmoden periode"
    tekstbredde = max([text_metrics.horizontalAdvance(p) for p in periodar] + [0])
    tittelbredde = title_metrics.horizontalAdvance(tittel)

    padding = 18
    boksstorleik = 18
    linje_h = 32

    bredde = max(260, tittelbredde, tekstbredde + boksstorleik + 3 * padding) + 20
    hogde = 20 + 34 + len(periodar) * linje_h + 16

    image = QImage(int(bredde), int(hogde), QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor(70, 70, 70), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255, 245)))
        painter.drawRect(1, 1, image.width() - 2, image.height() - 2)

        painter.setPen(Qt.black)
        painter.setFont(title_font)
        painter.drawText(
            QRectF(padding, 10, image.width() - 2 * padding, 28),
            Qt.AlignLeft | Qt.AlignVCenter,
            tittel,
        )

        painter.setFont(text_font)

        start_y = 44
        for i, periode in enumerate(periodar):
            rad_y = start_y + i * linje_h

            farge = QColor(periode_farge(periode))
            painter.setBrush(QBrush(farge))
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.drawRect(padding, rad_y + 4, boksstorleik, boksstorleik)

            painter.setPen(Qt.black)
            painter.drawText(
                QRectF(
                    padding + boksstorleik + 12,
                    rad_y,
                    image.width() - (padding + boksstorleik + 24),
                    26,
                ),
                Qt.AlignLeft | Qt.AlignVCenter,
                periode,
            )
    finally:
        painter.end()
        temp_painter.end()

    return image


def _lag_nordpilbilete():
    storleik = 220
    image = QImage(storleik, storleik, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.setPen(QPen(QColor(70, 70, 70), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.drawEllipse(10, 10, storleik - 20, storleik - 20)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(Qt.black))

        topp = QPointF(storleik / 2, 35)
        venstre = QPointF(storleik / 2 - 28, storleik / 2 + 30)
        hoyre = QPointF(storleik / 2 + 28, storleik / 2 + 30)
        pil = QPolygonF([topp, venstre, hoyre])
        painter.drawPolygon(pil)

        painter.setPen(QPen(Qt.black, 2))
        painter.setFont(QFont("Arial", 28, QFont.Bold))
        painter.drawText(
            QRectF(0, storleik / 2 + 35, storleik, 50),
            Qt.AlignHCenter | Qt.AlignVCenter,
            "N",
        )
    finally:
        painter.end()

    return image


def _teikn_forklaring(painter, kartrekt, resultatlag):
    legend_image = _lag_forklaringsbilete(resultatlag)
    if legend_image is None or legend_image.isNull():
        return

    max_w = kartrekt.width() * 0.28
    max_h = kartrekt.height() * 0.45
    scale = min(max_w / legend_image.width(), max_h / legend_image.height())
    scale = max(0.2, min(scale, 1.6))

    legend_w = legend_image.width() * scale
    legend_h = legend_image.height() * scale

    x = kartrekt.right() - legend_w - 30
    y = kartrekt.top() + 30

    malrekt = QRectF(x, y, legend_w, legend_h)
    kjelderekt = QRectF(0, 0, legend_image.width(), legend_image.height())

    painter.drawImage(malrekt, legend_image, kjelderekt)


def _teikn_nordpil(painter, kartrekt):
    nordpil = _lag_nordpilbilete()
    if nordpil.isNull():
        return

    max_w = kartrekt.width() * 0.12
    max_h = kartrekt.height() * 0.20
    scale = min(max_w / nordpil.width(), max_h / nordpil.height())
    scale = max(0.2, min(scale, 1.2))

    pil_w = nordpil.width() * scale
    pil_h = nordpil.height() * scale

    x = kartrekt.left() + 30
    y = kartrekt.top() + 30

    malrekt = QRectF(x, y, pil_w, pil_h)
    kjelderekt = QRectF(0, 0, nordpil.width(), nordpil.height())

    painter.drawImage(malrekt, nordpil, kjelderekt)


def _fit_rect(src_w, src_h, dst_rect):
    if src_w <= 0 or src_h <= 0:
        return QRectF(dst_rect)

    src_ratio = float(src_w) / float(src_h)
    dst_ratio = float(dst_rect.width()) / float(dst_rect.height())

    if src_ratio > dst_ratio:
        w = dst_rect.width()
        h = w / src_ratio
        x = dst_rect.x()
        y = dst_rect.y() + (dst_rect.height() - h) / 2.0
    else:
        h = dst_rect.height()
        w = h * src_ratio
        x = dst_rect.x() + (dst_rect.width() - w) / 2.0
        y = dst_rect.y()

    return QRectF(x, y, w, h)


def _teikn_pdf_direkte(
    pdf_fil,
    png_fil,
    resultatlag,
    takstlag_namn,
    driftslag_namn,
    filter_periodar,
    filter_metodar,
):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(pdf_fil)
    printer.setPageSize(QPageSize(QPageSize.A3))
    printer.setPageOrientation(QPageLayout.Landscape)
    printer.setPageMargins(8, 8, 8, 8, QPrinter.Millimeter)

    painter = QPainter()
    if not painter.begin(printer):
        raise Exception("Klarte ikkje a starte PDF-teikning.")

    try:
        page_rect = printer.pageRect(QPrinter.DevicePixel)
        x = page_rect.x()
        y = page_rect.y()
        w = page_rect.width()
        h = page_rect.height()

        topp_h = int(h * 0.12)
        kart_y = y + topp_h
        kart_h = h - topp_h

        title_font = QFont("Arial", 18)
        meta_font = QFont("Arial", 10)

        painter.setPen(Qt.black)

        painter.setFont(title_font)
        painter.drawText(QRectF(x, y, w, 40), "Hogstplan - kart")

        periode_txt = ", ".join(filter_periodar) if filter_periodar else "Alle"
        metode_txt = ", ".join(filter_metodar) if filter_metodar else "Alle"
        dato_txt = datetime.now().strftime("%Y-%m-%d %H:%M")

        meta_txt = (
            f"Takstlag: {takstlag_namn}\n"
            f"Driftsmetodelag: {driftslag_namn}\n"
            f"Periodar: {periode_txt}\n"
            f"Driftsmetodar: {metode_txt}\n"
            f"Dato: {dato_txt}"
        )

        painter.setFont(meta_font)
        painter.drawText(
            QRectF(x, y + 45, w, topp_h - 50),
            Qt.TextWordWrap,
            meta_txt,
        )

        image = QImage(png_fil)
        if image.isNull():
            raise Exception("Klarte ikkje a lese kartbiletet for PDF.")

        kartflate = QRectF(x, kart_y, w, kart_h - 10)
        malrekt = _fit_rect(image.width(), image.height(), kartflate)
        kjelderekt = QRectF(0, 0, image.width(), image.height())

        painter.drawImage(malrekt, image, kjelderekt)

        painter.setPen(QColor(80, 80, 80))
        painter.drawRect(malrekt)

        _teikn_nordpil(painter, malrekt)
        _teikn_forklaring(painter, malrekt, resultatlag)

    finally:
        painter.end()


def lag_kart_pdf(
    resultatlag,
    pdf_fil,
    takstlag_namn,
    driftslag_namn,
    filter_periodar,
    filter_metodar,
    iface,
):
    if resultatlag is None:
        raise Exception("Manglar resultatlag for kart-PDF.")

    with tempfile.TemporaryDirectory() as temp_dir:
        png_fil = os.path.join(temp_dir, "hogstplan_kart.png")

        _lag_kartbilete_med_mapsettings(resultatlag, png_fil)

        if not os.path.exists(png_fil):
            raise Exception("Kartbiletet vart ikkje oppretta.")

        _teikn_pdf_direkte(
            pdf_fil,
            png_fil,
            resultatlag,
            takstlag_namn,
            driftslag_namn,
            filter_periodar,
            filter_metodar,
        )


def skriv_kart_pdf_robust(
    folder,
    base_name,
    resultatlag,
    takstlag_namn,
    driftslag_namn,
    filter_periodar,
    filter_metodar,
    iface,
):
    os.makedirs(folder, exist_ok=True)

    forste = _safe_export_path(folder, f"{base_name}_kart", ".pdf")

    try:
        lag_kart_pdf(
            resultatlag,
            forste,
            takstlag_namn,
            driftslag_namn,
            filter_periodar,
            filter_metodar,
            iface,
        )
        return forste
    except PermissionError:
        reserve = _fallback_export_path(folder, f"{base_name}_kart", ".pdf")
        lag_kart_pdf(
            resultatlag,
            reserve,
            takstlag_namn,
            driftslag_namn,
            filter_periodar,
            filter_metodar,
            iface,
        )
        return reserve
    except OSError:
        reserve = _fallback_export_path(folder, f"{base_name}_kart", ".pdf")
        lag_kart_pdf(
            resultatlag,
            reserve,
            takstlag_namn,
            driftslag_namn,
            filter_periodar,
            filter_metodar,
            iface,
        )
        return reserve
