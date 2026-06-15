# Hogstplan

QGIS-plugin for a lage driftsomrade fra takstdata og driftsmetode, med:
- resultatlag i kart
- CSV-rapport
- tabell-PDF
- kart-PDF

## Krav
- QGIS 3.28 eller nyare

## Installer lokalt (Windows)
Kopier heile mappa `Hogstplan` til:

`C:\Users\egil1\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\Hogstplan`

Start QGIS pa nytt, og aktiver pluginen i Plugin Manager.

## Viktige filer
- `metadata.txt`
- `__init__.py`
- `hogstplan_plugin.py`
- `hogstplan_dialog.py`
- `hogstplan_core.py`
- `hogstplan_utils.py`
- `hogstplan_style.py`
- `hogstplan_export.py`
- `hogstplan_layout.py`
- `icon.png`

## Kort testflyt
1. Last inn takstlag (polygon) og driftsmetodelag (polygon).
2. Opne Hogstplan-pluginen.
3. Vel felt og output-typar.
4. Vel eksportmappe om CSV/PDF er aktivt.
5. Koyr og kontroller resultatlag + rapportfiler.