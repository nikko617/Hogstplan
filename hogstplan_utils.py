from qgis.core import QgsWkbTypes


def to_float(verdi):
    if verdi is None:
        return 0.0
    try:
        return float(verdi)
    except (TypeError, ValueError):
        return 0.0


def lag_periode(hogstaar):
    if hogstaar is None:
        return None
    try:
        aar = int(float(hogstaar))
    except (TypeError, ValueError):
        return None

    start = (aar // 5) * 5
    slutt = start + 5
    return f"{start}-{slutt}"


def merge_tekstar(tekstar):
    sett = set()
    liste = []
    for t in tekstar:
        if t is None:
            continue
        txt = str(t).strip()
        if not txt:
            continue
        if txt not in sett:
            sett.add(txt)
            liste.append(txt)
    return " | ".join(liste)


def finn_felt(layer, felt_namn):
    idx = layer.fields().indexOf(felt_namn)
    if idx < 0:
        raise Exception(f"Feltet '{felt_namn}' finst ikkje i laget '{layer.name()}'.")
    return idx


def valider_polygonlag(layer, rolle):
    if layer is None:
        raise Exception(f"Manglar lag for {rolle}.")
    if QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.PolygonGeometry:
        raise Exception(f"Laget '{layer.name()}' for {rolle} må vere polygonlag.")


def hent_unike_verdiar(layer, felt_namn, som_periodar=False):
    verdiar = set()
    for feat in layer.getFeatures():
        verdi = feat[felt_namn]
        if verdi is None:
            continue

        if som_periodar:
            periode = lag_periode(verdi)
            if periode:
                verdiar.add(periode)
        else:
            txt = str(verdi).strip()
            if txt:
                verdiar.add(txt)

    return sorted(verdiar)
