from qgis.PyQt.QtCore import QVariant

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsWkbTypes,
)

import processing

from .hogstplan_utils import (
    to_float,
    lag_periode,
    merge_tekstar,
    finn_felt,
    valider_polygonlag,
)
from .hogstplan_export import (
    skriv_csv_robust,
    bygg_html_rapport,
    skriv_pdf_robust,
)
from .hogstplan_style import (
    stilsett_resultatlag,
    set_labels,
)
from .hogstplan_layout import skriv_kart_pdf_robust


def _lag_takstlag_med_originalareal(takstlag):
    crs_authid = takstlag.crs().authid()
    geom_type = QgsWkbTypes.displayString(takstlag.wkbType())
    temp_layer = QgsVectorLayer(f"{geom_type}?crs={crs_authid}", "takst_med_areal", "memory")
    provider = temp_layer.dataProvider()

    feltliste = list(takstlag.fields())
    feltliste.append(QgsField("ORIG_AREA", QVariant.Double, len=20, prec=6))
    provider.addAttributes(feltliste)
    temp_layer.updateFields()

    nye_feats = []
    for feat in takstlag.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue

        ny = QgsFeature(temp_layer.fields())
        ny.setGeometry(geom)

        attrs = feat.attributes()
        attrs.append(geom.area())
        ny.setAttributes(attrs)
        nye_feats.append(ny)

    provider.addFeatures(nye_feats)
    temp_layer.updateExtents()
    return temp_layer


def _del_opp_geometri(geom):
    if geom is None or geom.isEmpty():
        return []

    if geom.isMultipart():
        delar = []
        for delgeom in geom.asGeometryCollection():
            if delgeom and not delgeom.isEmpty():
                delar.append(QgsGeometry(delgeom))
        return delar

    return [QgsGeometry(geom)]


def _lag_bufferklynger(geometriar, avstand):
    bufferar = []
    for geom in geometriar:
        if geom is None or geom.isEmpty():
            continue

        buf = geom.buffer(avstand, 8)
        if buf is not None and not buf.isEmpty():
            bufferar.append(buf)

    if not bufferar:
        return []

    union_geom = QgsGeometry.unaryUnion(bufferar)
    return _del_opp_geometri(union_geom)


def koyr_hogstplan(params):
    opprinneleg_takstlag = params["takstlag"]
    opprinneleg_driftslag = params["driftslag"]

    felt_hogstaar = params["felt_hogstaar"]
    felt_gran = params["felt_gran"]
    felt_furu = params["felt_furu"]
    felt_lauv = params["felt_lauv"]
    felt_total_hogstmoden = params["felt_total_hogstmoden"]
    felt_merk = params.get("felt_merk", "")
    felt_merknad = params.get("felt_merknad", "")
    felt_bestand_id = params["felt_bestand_id"]
    felt_driftm = params["felt_driftm"]

    resultat_namn = params["resultat_namn"]
    samleavstand_meter = params.get("samleavstand_meter", 20.0)
    arealveg = params["arealveg"]
    lag_polygon = params["lag_polygon"]
    lag_csv = params["lag_csv"]
    lag_pdf = params["lag_pdf"]
    lag_kart_pdf = params.get("lag_kart_pdf", False)
    eksportmappe = params["eksportmappe"]

    filter_periodar = params.get("filter_periodar", [])
    filter_metodar = params.get("filter_metodar", [])

    valider_polygonlag(opprinneleg_takstlag, "takstlag")
    valider_polygonlag(opprinneleg_driftslag, "driftsmetodelag")

    for felt in [
        felt_hogstaar,
        felt_gran,
        felt_furu,
        felt_lauv,
        felt_total_hogstmoden,
        felt_bestand_id,
    ]:
        finn_felt(opprinneleg_takstlag, felt)

    if felt_merk:
        finn_felt(opprinneleg_takstlag, felt_merk)
    if felt_merknad:
        finn_felt(opprinneleg_takstlag, felt_merknad)

    finn_felt(opprinneleg_driftslag, felt_driftm)

    try:
        takstlag = processing.run(
            "native:fixgeometries",
            {
                "INPUT": opprinneleg_takstlag,
                "METHOD": 1,
                "OUTPUT": "memory:",
            },
        )["OUTPUT"]
    except Exception as e:
        raise Exception(f"Klarte ikkje a fikse geometri for takstlag: {e}")

    try:
        driftslag = processing.run(
            "native:fixgeometries",
            {
                "INPUT": opprinneleg_driftslag,
                "METHOD": 1,
                "OUTPUT": "memory:",
            },
        )["OUTPUT"]
    except Exception as e:
        raise Exception(f"Klarte ikkje a fikse geometri for driftsmetodelag: {e}")

    takst_input = _lag_takstlag_med_originalareal(takstlag) if arealveg else takstlag

    try:
        inter_layer = processing.run(
            "native:intersection",
            {
                "INPUT": takst_input,
                "OVERLAY": driftslag,
                "INPUT_FIELDS": [],
                "OVERLAY_FIELDS": [felt_driftm],
                "OVERLAY_FIELDS_PREFIX": "drift_",
                "OUTPUT": "memory:",
            },
        )["OUTPUT"]
    except Exception as e:
        raise Exception(f"Klarte ikkje a koyre intersection: {e}")

    filter_periodar_set = set(filter_periodar) if filter_periodar else None
    filter_metodar_set = set(filter_metodar) if filter_metodar else None

    deldata_per_gruppe = {}
    driftm_namn = f"drift_{felt_driftm}"

    for feat in inter_layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue

        periode = lag_periode(feat[felt_hogstaar])
        if not periode:
            continue

        if driftm_namn in feat.fields().names():
            driftsmetode = feat[driftm_namn]
        else:
            driftsmetode = feat[felt_driftm]

        if driftsmetode is None or str(driftsmetode).strip() == "":
            driftsmetode = "Ukjend"
        driftsmetode = str(driftsmetode)

        if filter_periodar_set is not None and periode not in filter_periodar_set:
            continue
        if filter_metodar_set is not None and driftsmetode not in filter_metodar_set:
            continue

        gran = to_float(feat[felt_gran])
        furu = to_float(feat[felt_furu])
        lauv = to_float(feat[felt_lauv])
        hogstmoden_total = to_float(feat[felt_total_hogstmoden])

        if arealveg:
            areal_original = to_float(feat["ORIG_AREA"])
            areal_del = geom.area()
            if areal_original > 0:
                vekt = areal_del / areal_original
                gran *= vekt
                furu *= vekt
                lauv *= vekt
                hogstmoden_total *= vekt

        nokkel = (periode, driftsmetode)
        if nokkel not in deldata_per_gruppe:
            deldata_per_gruppe[nokkel] = []

        deldata_per_gruppe[nokkel].append(
            {
                "geom": QgsGeometry(geom),
                "gran_2025": gran,
                "furu_2025": furu,
                "lauv_2025": lauv,
                "sum_2025": gran + furu + lauv,
                "hogstmoden": hogstmoden_total,
                "merk": feat[felt_merk] if felt_merk else None,
                "merknad": feat[felt_merknad] if felt_merknad else None,
            }
        )

    sluttrader = []
    drift_nr = 1

    for (periode, driftsmetode), deler in sorted(
        deldata_per_gruppe.items(), key=lambda x: (x[0][0], x[0][1])
    ):
        geometriar = [d["geom"] for d in deler if d["geom"] and not d["geom"].isEmpty()]
        if not geometriar:
            continue

        klynger = _lag_bufferklynger(geometriar, samleavstand_meter)
        if not klynger:
            continue

        brukte_indeksar = set()

        for klynge in klynger:
            geometriar_i_klynge = []
            gran_sum = 0.0
            furu_sum = 0.0
            lauv_sum = 0.0
            sum_2025 = 0.0
            hogstmoden_sum = 0.0
            merk_liste = []
            merknad_liste = []

            for idx, delrad in enumerate(deler):
                if idx in brukte_indeksar:
                    continue

                geom = delrad["geom"]
                if geom is None or geom.isEmpty():
                    continue

                if geom.intersects(klynge):
                    brukte_indeksar.add(idx)
                    geometriar_i_klynge.append(geom)
                    gran_sum += delrad["gran_2025"]
                    furu_sum += delrad["furu_2025"]
                    lauv_sum += delrad["lauv_2025"]
                    sum_2025 += delrad["sum_2025"]
                    hogstmoden_sum += delrad["hogstmoden"]
                    merk_liste.append(delrad["merk"])
                    merknad_liste.append(delrad["merknad"])

            if not geometriar_i_klynge:
                continue

            sluttgeom = QgsGeometry.unaryUnion(geometriar_i_klynge)
            if sluttgeom is None or sluttgeom.isEmpty():
                continue

            sluttrader.append(
                {
                    "drift_nr": drift_nr,
                    "periode": periode,
                    "driftm": driftsmetode,
                    "gran_2025": round(gran_sum, 2),
                    "furu_2025": round(furu_sum, 2),
                    "lauv_2025": round(lauv_sum, 2),
                    "sum_2025": round(sum_2025, 2),
                    "hogstmoden": round(hogstmoden_sum, 2),
                    "merk": merge_tekstar(merk_liste)[:255],
                    "merknad": merge_tekstar(merknad_liste)[:255],
                    "geom": sluttgeom,
                }
            )
            drift_nr += 1

    polygonlag_namn = None
    kart_pdf_fil = None
    resultatlag = None

    if lag_polygon or lag_kart_pdf:
        resultatlag = QgsVectorLayer(
            f"MultiPolygon?crs={opprinneleg_takstlag.crs().authid()}",
            resultat_namn,
            "memory",
        )
        provider = resultatlag.dataProvider()
        provider.addAttributes(
            [
                QgsField("drift_nr", QVariant.Int),
                QgsField("periode", QVariant.String, len=20),
                QgsField("driftm", QVariant.String, len=50),
                QgsField("gran_2025", QVariant.Double, len=20, prec=2),
                QgsField("furu_2025", QVariant.Double, len=20, prec=2),
                QgsField("lauv_2025", QVariant.Double, len=20, prec=2),
                QgsField("sum_2025", QVariant.Double, len=20, prec=2),
                QgsField("hogstmoden", QVariant.Double, len=20, prec=2),
                QgsField("merk", QVariant.String, len=255),
                QgsField("merknad", QVariant.String, len=255),
            ]
        )
        resultatlag.updateFields()

        feats = []
        for rad in sluttrader:
            feat = QgsFeature(resultatlag.fields())
            feat.setGeometry(rad["geom"])
            feat["drift_nr"] = rad["drift_nr"]
            feat["periode"] = rad["periode"]
            feat["driftm"] = rad["driftm"]
            feat["gran_2025"] = rad["gran_2025"]
            feat["furu_2025"] = rad["furu_2025"]
            feat["lauv_2025"] = rad["lauv_2025"]
            feat["sum_2025"] = rad["sum_2025"]
            feat["hogstmoden"] = rad["hogstmoden"]
            feat["merk"] = rad["merk"]
            feat["merknad"] = rad["merknad"]
            feats.append(feat)

        provider.addFeatures(feats)
        resultatlag.updateExtents()
        stilsett_resultatlag(resultatlag)
        set_labels(resultatlag)

        if lag_polygon:
            QgsProject.instance().addMapLayer(resultatlag)
            polygonlag_namn = resultatlag.name()

    rader_utan_geom = []
    for rad in sluttrader:
        rader_utan_geom.append(
            {
                "drift_nr": rad["drift_nr"],
                "periode": rad["periode"],
                "driftm": rad["driftm"],
                "gran_2025": rad["gran_2025"],
                "furu_2025": rad["furu_2025"],
                "lauv_2025": rad["lauv_2025"],
                "sum_2025": rad["sum_2025"],
                "hogstmoden": rad["hogstmoden"],
                "merk": rad["merk"],
                "merknad": rad["merknad"],
            }
        )

    csv_fil = None
    pdf_fil = None

    if lag_csv:
        csv_fil = skriv_csv_robust(eksportmappe, resultat_namn, rader_utan_geom)

    if lag_pdf:
        html_txt = bygg_html_rapport(
            rader_utan_geom,
            opprinneleg_takstlag.name(),
            opprinneleg_driftslag.name(),
            filter_periodar,
            filter_metodar,
        )
        pdf_fil = skriv_pdf_robust(eksportmappe, resultat_namn, html_txt)

    if lag_kart_pdf:
        if resultatlag is None:
            raise Exception("Kart-PDF krev at resultatlag kan byggjast.")

        kart_pdf_fil = skriv_kart_pdf_robust(
            eksportmappe,
            resultat_namn,
            resultatlag,
            opprinneleg_takstlag.name(),
            opprinneleg_driftslag.name(),
            filter_periodar,
            filter_metodar,
            params.get("iface"),
        )

    return {
        "polygonlag_namn": polygonlag_namn,
        "csv_fil": csv_fil,
        "pdf_fil": pdf_fil,
        "kart_pdf_fil": kart_pdf_fil,
        "tal_omrader": len(rader_utan_geom),
    }
