from qgis.PyQt.QtGui import QColor, QFont

from qgis.core import (
    QgsSymbol,
    QgsRendererCategory,
    QgsCategorizedSymbolRenderer,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
)


def periode_farge(periode):
    mapping = {
        "2020-2025": "#00B050",
        "2025-2030": "#FFD966",
        "2030-2035": "#ED7D31",
        "2035-2040": "#8C5A2B",
        "2040-2045": "#7030A0",
    }

    if not periode:
        return "#BFBFBF"

    return mapping.get(periode, "#C00000")


def stilsett_resultatlag(resultatlag):
    idx = resultatlag.fields().indexOf("periode")
    if idx < 0:
        symbol = QgsSymbol.defaultSymbol(resultatlag.geometryType())
        if symbol is not None:
            symbol.setColor(QColor(0, 0, 0, 0))
            layer0 = symbol.symbolLayer(0)
            if layer0 is not None:
                layer0.setStrokeColor(QColor("#4F4F4F"))
                layer0.setStrokeWidth(1.2)
        renderer = QgsCategorizedSymbolRenderer("", [QgsRendererCategory(None, symbol, "Alle")])
        resultatlag.setRenderer(renderer)
        resultatlag.triggerRepaint()
        return

    periodar = sorted(
        [str(v) if v is not None else "" for v in resultatlag.uniqueValues(idx)]
    )

    if not periodar:
        periodar = [""]

    kategoriar = []
    for periode in periodar:
        symbol = QgsSymbol.defaultSymbol(resultatlag.geometryType())
        if symbol is not None:
            symbol.setColor(QColor(0, 0, 0, 0))
            layer0 = symbol.symbolLayer(0)
            if layer0 is not None:
                layer0.setStrokeColor(QColor(periode_farge(periode)))
                layer0.setStrokeWidth(1.2)

        label = periode if periode else "Ukjend"
        kategoriar.append(QgsRendererCategory(periode, symbol, label))

    renderer = QgsCategorizedSymbolRenderer("periode", kategoriar)
    resultatlag.setRenderer(renderer)
    resultatlag.triggerRepaint()


def set_labels(resultatlag):
    if resultatlag.fields().indexOf("drift_nr") < 0:
        resultatlag.setLabelsEnabled(False)
        return

    settings = QgsPalLayerSettings()
    settings.fieldName = "drift_nr"
    settings.enabled = True

    text_format = QgsTextFormat()
    text_format.setFont(QFont("Arial", 9))
    text_format.setSize(9)
    text_format.setColor(QColor("black"))
    settings.setFormat(text_format)

    labeling = QgsVectorLayerSimpleLabeling(settings)
    resultatlag.setLabelsEnabled(True)
    resultatlag.setLabeling(labeling)
    resultatlag.triggerRepaint()
