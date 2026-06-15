import traceback

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QCheckBox,
    QMessageBox,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QDoubleSpinBox,
)

from qgis.core import QgsProject, QgsVectorLayer

from .hogstplan_core import koyr_hogstplan
from .hogstplan_utils import hent_unike_verdiar


class HogstplanDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Hogstplan")
        self.resize(760, 800)

        self._bygg_ui()
        self._fyll_lag()
        self._kople_signal()
        self._set_standardverdiar()
        self._oppdater_filterlister()

    def _bygg_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Lag driftsomrade fra takstdata og driftsmetode.\n"
            "Pluginen lagar polygonlag, CSV, tabell-PDF og kart-PDF.\n"
            "Du kan valfritt filtrere pa periodar og driftsmetodar."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()

        self.cmb_takstlag = QComboBox()
        self.cmb_driftslag = QComboBox()
        form.addRow("Takstlag:", self.cmb_takstlag)
        form.addRow("Driftsmetodelag:", self.cmb_driftslag)

        self.cmb_hogstaar = QComboBox()
        self.cmb_gran = QComboBox()
        self.cmb_furu = QComboBox()
        self.cmb_lauv = QComboBox()
        self.cmb_total_hogstmoden = QComboBox()
        self.cmb_merk = QComboBox()
        self.cmb_merknad = QComboBox()
        self.cmb_bestand_id = QComboBox()
        self.cmb_driftm = QComboBox()

        form.addRow("Felt for hogstmodent ar:", self.cmb_hogstaar)
        form.addRow("Felt for volum gran i 2025:", self.cmb_gran)
        form.addRow("Felt for volum furu i 2025:", self.cmb_furu)
        form.addRow("Felt for volum lauv i 2025:", self.cmb_lauv)
        form.addRow("Felt for berekna totalvolum ved hogstmodenheit:", self.cmb_total_hogstmoden)
        form.addRow("Felt for MERK:", self.cmb_merk)
        form.addRow("Felt for MERKNAD:", self.cmb_merknad)
        form.addRow("Felt for bestand-ID:", self.cmb_bestand_id)
        form.addRow("Felt for driftsmetode:", self.cmb_driftm)

        self.txt_resultatlag = QLineEdit()
        self.txt_resultatlag.setText("hogstomrader")
        form.addRow("Namn pa resultatlag:", self.txt_resultatlag)

        self.spn_samleavstand = QDoubleSpinBox()
        self.spn_samleavstand.setDecimals(1)
        self.spn_samleavstand.setRange(0.0, 100000.0)
        self.spn_samleavstand.setSingleStep(10.0)
        self.spn_samleavstand.setValue(20.0)
        self.spn_samleavstand.setSuffix(" m")
        form.addRow("Samleavstand:", self.spn_samleavstand)

        layout.addLayout(form)

        filter_layout = QHBoxLayout()

        self.grp_periodar = QGroupBox("Filtrer pa periodar (tomt val = alle)")
        period_layout = QVBoxLayout()
        self.lst_periodar = QListWidget()
        period_layout.addWidget(self.lst_periodar)
        self.btn_periodar_alle = QPushButton("Vel alle periodar")
        self.btn_periodar_ingen = QPushButton("Fjern val")
        period_btns = QHBoxLayout()
        period_btns.addWidget(self.btn_periodar_alle)
        period_btns.addWidget(self.btn_periodar_ingen)
        period_layout.addLayout(period_btns)
        self.grp_periodar.setLayout(period_layout)

        self.grp_metodar = QGroupBox("Filtrer pa driftsmetodar (tomt val = alle)")
        metode_layout = QVBoxLayout()
        self.lst_metodar = QListWidget()
        metode_layout.addWidget(self.lst_metodar)
        self.btn_metodar_alle = QPushButton("Vel alle metodar")
        self.btn_metodar_ingen = QPushButton("Fjern val")
        metode_btns = QHBoxLayout()
        metode_btns.addWidget(self.btn_metodar_alle)
        metode_btns.addWidget(self.btn_metodar_ingen)
        metode_layout.addLayout(metode_btns)
        self.grp_metodar.setLayout(metode_layout)

        filter_layout.addWidget(self.grp_periodar)
        filter_layout.addWidget(self.grp_metodar)
        layout.addLayout(filter_layout)

        self.chk_arealveg = QCheckBox("Arealveg volum ved splitting")
        self.chk_arealveg.setChecked(True)

        self.chk_lag_polygon = QCheckBox("Lag polygonlag i prosjektet")
        self.chk_lag_polygon.setChecked(True)

        self.chk_lag_csv = QCheckBox("Lag CSV-rapport")
        self.chk_lag_csv.setChecked(True)

        self.chk_lag_pdf = QCheckBox("Lag tabell-PDF")
        self.chk_lag_pdf.setChecked(True)

        self.chk_lag_kart_pdf = QCheckBox("Lag kart-PDF")
        self.chk_lag_kart_pdf.setChecked(True)

        layout.addWidget(self.chk_arealveg)
        layout.addWidget(self.chk_lag_polygon)
        layout.addWidget(self.chk_lag_csv)
        layout.addWidget(self.chk_lag_pdf)
        layout.addWidget(self.chk_lag_kart_pdf)

        export_layout = QHBoxLayout()
        self.txt_exportmappe = QLineEdit()
        self.btn_exportmappe = QPushButton("Vel mappe ...")
        export_layout.addWidget(self.txt_exportmappe)
        export_layout.addWidget(self.btn_exportmappe)

        layout.addWidget(QLabel("Eksportmappe for CSV og PDF:"))
        layout.addLayout(export_layout)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Koyr")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Avbryt")
        layout.addWidget(self.buttons)

    def _kople_signal(self):
        self.cmb_takstlag.currentIndexChanged.connect(self._oppdater_takstfelt)
        self.cmb_driftslag.currentIndexChanged.connect(self._oppdater_driftsfelt)
        self.cmb_hogstaar.currentIndexChanged.connect(self._oppdater_filterlister)
        self.cmb_driftm.currentIndexChanged.connect(self._oppdater_filterlister)

        self.btn_exportmappe.clicked.connect(self._vel_exportmappe)

        self.btn_periodar_alle.clicked.connect(
            lambda: self._set_all_checked(self.lst_periodar, True)
        )
        self.btn_periodar_ingen.clicked.connect(
            lambda: self._set_all_checked(self.lst_periodar, False)
        )
        self.btn_metodar_alle.clicked.connect(
            lambda: self._set_all_checked(self.lst_metodar, True)
        )
        self.btn_metodar_ingen.clicked.connect(
            lambda: self._set_all_checked(self.lst_metodar, False)
        )

        self.buttons.accepted.connect(self._koyr)
        self.buttons.rejected.connect(self.reject)

    def _fyll_lag(self):
        self.cmb_takstlag.clear()
        self.cmb_driftslag.clear()

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                self.cmb_takstlag.addItem(layer.name(), layer.id())
                self.cmb_driftslag.addItem(layer.name(), layer.id())

        self._foreslaa_lag()
        self._oppdater_takstfelt()
        self._oppdater_driftsfelt()

    def _foreslaa_lag(self):
        takst_namn = "takstdata.gdb/a0000000e.gdbtable"
        drift_namn = "HAF driftsomrader Kvammen"

        for i in range(self.cmb_takstlag.count()):
            if self.cmb_takstlag.itemText(i) == takst_namn:
                self.cmb_takstlag.setCurrentIndex(i)
                break

        for i in range(self.cmb_driftslag.count()):
            if self.cmb_driftslag.itemText(i) == drift_namn:
                self.cmb_driftslag.setCurrentIndex(i)
                break

    def _lag_feltliste(self, combo, layer, tillat_tomt=False):
        combo.clear()
        if tillat_tomt:
            combo.addItem("")
        if layer is None:
            return
        for field in layer.fields():
            combo.addItem(field.name())

    def _get_layer_by_combo(self, combo):
        layer_id = combo.currentData()
        if not layer_id:
            return None
        return QgsProject.instance().mapLayer(layer_id)

    def _oppdater_takstfelt(self):
        layer = self._get_layer_by_combo(self.cmb_takstlag)
        self._lag_feltliste(self.cmb_hogstaar, layer)
        self._lag_feltliste(self.cmb_gran, layer)
        self._lag_feltliste(self.cmb_furu, layer)
        self._lag_feltliste(self.cmb_lauv, layer)
        self._lag_feltliste(self.cmb_total_hogstmoden, layer)
        self._lag_feltliste(self.cmb_merk, layer, tillat_tomt=True)
        self._lag_feltliste(self.cmb_merknad, layer, tillat_tomt=True)
        self._lag_feltliste(self.cmb_bestand_id, layer)
        self._set_standardverdiar()
        self._oppdater_filterlister()

    def _oppdater_driftsfelt(self):
        layer = self._get_layer_by_combo(self.cmb_driftslag)
        self._lag_feltliste(self.cmb_driftm, layer)
        self._set_standardverdiar()
        self._oppdater_filterlister()

    def _set_combo_text_if_exists(self, combo, text):
        if not text:
            return
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _set_standardverdiar(self):
        self._set_combo_text_if_exists(self.cmb_hogstaar, "HOGSTMODENT_AAR")
        self._set_combo_text_if_exists(self.cmb_gran, "VOLUM_GRAN")
        self._set_combo_text_if_exists(self.cmb_furu, "VOLUM_FURU")
        self._set_combo_text_if_exists(self.cmb_lauv, "VOLUM_LAUV")
        self._set_combo_text_if_exists(self.cmb_total_hogstmoden, "BER_VOLUMTOT")
        self._set_combo_text_if_exists(self.cmb_merk, "MERK")
        self._set_combo_text_if_exists(self.cmb_merknad, "MERKNAD")
        self._set_combo_text_if_exists(self.cmb_bestand_id, "BESTAND_ID")
        self._set_combo_text_if_exists(self.cmb_driftm, "Driftm")

    def _vel_exportmappe(self):
        path = QFileDialog.getExistingDirectory(self, "Vel eksportmappe")
        if path:
            self.txt_exportmappe.setText(path)

    def _fyll_checkliste(self, listewidget, verdiar, valde):
        listewidget.clear()
        valde_set = set(valde or [])
        for verdi in verdiar:
            item = QListWidgetItem(str(verdi))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if str(verdi) in valde_set else Qt.Unchecked)
            listewidget.addItem(item)

    def _set_all_checked(self, listewidget, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(listewidget.count()):
            listewidget.item(i).setCheckState(state)

    def _get_checked_values(self, listewidget):
        verdiar = []
        for i in range(listewidget.count()):
            item = listewidget.item(i)
            if item.checkState() == Qt.Checked:
                verdiar.append(item.text())
        return verdiar

    def _oppdater_filterlister(self):
        valde_periodar = self._get_checked_values(self.lst_periodar)
        valde_metodar = self._get_checked_values(self.lst_metodar)

        takstlag = self._get_layer_by_combo(self.cmb_takstlag)
        driftslag = self._get_layer_by_combo(self.cmb_driftslag)

        felt_hogstaar = self.cmb_hogstaar.currentText().strip()
        felt_driftm = self.cmb_driftm.currentText().strip()

        periodar = []
        metodar = []

        try:
            if takstlag and felt_hogstaar:
                periodar = hent_unike_verdiar(takstlag, felt_hogstaar, som_periodar=True)
        except Exception:
            periodar = []

        try:
            if driftslag and felt_driftm:
                metodar = hent_unike_verdiar(driftslag, felt_driftm, som_periodar=False)
        except Exception:
            metodar = []

        self._fyll_checkliste(self.lst_periodar, periodar, valde_periodar)
        self._fyll_checkliste(self.lst_metodar, metodar, valde_metodar)

    def _valider_obligatoriske_felt(self):
        obligatoriske = [
            ("Felt for hogstmodent ar", self.cmb_hogstaar.currentText().strip()),
            ("Felt for volum gran i 2025", self.cmb_gran.currentText().strip()),
            ("Felt for volum furu i 2025", self.cmb_furu.currentText().strip()),
            ("Felt for volum lauv i 2025", self.cmb_lauv.currentText().strip()),
            (
                "Felt for berekna totalvolum ved hogstmodenheit",
                self.cmb_total_hogstmoden.currentText().strip(),
            ),
            ("Felt for bestand-ID", self.cmb_bestand_id.currentText().strip()),
            ("Felt for driftsmetode", self.cmb_driftm.currentText().strip()),
        ]

        manglar = [namn for namn, verdi in obligatoriske if not verdi]
        if manglar:
            raise Exception("Manglar obligatoriske felt: " + ", ".join(manglar))

    def _koyr(self):
        takstlag = self._get_layer_by_combo(self.cmb_takstlag)
        driftslag = self._get_layer_by_combo(self.cmb_driftslag)

        if takstlag is None or driftslag is None:
            QMessageBox.warning(
                self,
                "Manglar lag",
                "Du ma velje bade takstlag og driftsmetodelag.",
            )
            return

        try:
            self._valider_obligatoriske_felt()
        except Exception as e:
            QMessageBox.warning(self, "Manglar felt", str(e))
            return

        if not (
            self.chk_lag_polygon.isChecked()
            or self.chk_lag_csv.isChecked()
            or self.chk_lag_pdf.isChecked()
            or self.chk_lag_kart_pdf.isChecked()
        ):
            QMessageBox.warning(
                self,
                "Manglar output",
                "Vel minst eitt output: polygonlag, CSV, tabell-PDF eller kart-PDF.",
            )
            return

        treng_eksportmappe = (
            self.chk_lag_csv.isChecked()
            or self.chk_lag_pdf.isChecked()
            or self.chk_lag_kart_pdf.isChecked()
        )

        if treng_eksportmappe and not self.txt_exportmappe.text().strip():
            QMessageBox.warning(
                self,
                "Manglar eksportmappe",
                "Du ma velje eksportmappe for CSV/PDF.",
            )
            return

        valde_periodar = self._get_checked_values(self.lst_periodar)
        valde_metodar = self._get_checked_values(self.lst_metodar)

        params = {
            "takstlag": takstlag,
            "driftslag": driftslag,
            "felt_hogstaar": self.cmb_hogstaar.currentText(),
            "felt_gran": self.cmb_gran.currentText(),
            "felt_furu": self.cmb_furu.currentText(),
            "felt_lauv": self.cmb_lauv.currentText(),
            "felt_total_hogstmoden": self.cmb_total_hogstmoden.currentText(),
            "felt_merk": self.cmb_merk.currentText().strip(),
            "felt_merknad": self.cmb_merknad.currentText().strip(),
            "felt_bestand_id": self.cmb_bestand_id.currentText(),
            "felt_driftm": self.cmb_driftm.currentText(),
            "resultat_namn": self.txt_resultatlag.text().strip() or "hogstomrader",
            "samleavstand_meter": self.spn_samleavstand.value(),
            "arealveg": self.chk_arealveg.isChecked(),
            "lag_polygon": self.chk_lag_polygon.isChecked(),
            "lag_csv": self.chk_lag_csv.isChecked(),
            "lag_pdf": self.chk_lag_pdf.isChecked(),
            "lag_kart_pdf": self.chk_lag_kart_pdf.isChecked(),
            "eksportmappe": self.txt_exportmappe.text().strip(),
            "filter_periodar": valde_periodar,
            "filter_metodar": valde_metodar,
            "iface": self.iface,
        }

        try:
            output = koyr_hogstplan(params)

            msg = "Hogstplan ferdig.\n"
            if output.get("polygonlag_namn"):
                msg += f"\nPolygonlag: {output['polygonlag_namn']}"
            if output.get("csv_fil"):
                msg += f"\nCSV: {output['csv_fil']}"
            if output.get("pdf_fil"):
                msg += f"\nTabell-PDF: {output['pdf_fil']}"
            if output.get("kart_pdf_fil"):
                msg += f"\nKart-PDF: {output['kart_pdf_fil']}"
            msg += f"\nTal omrade: {output.get('tal_omrader', 0)}"

            QMessageBox.information(self, "Ferdig", msg)
            self.accept()

        except Exception as e:
            traceback_txt = traceback.format_exc()
            QMessageBox.critical(
                self,
                "Feil ved koyring",
                f"Det oppstod ein feil:\n\n{str(e)}\n\nDetaljar:\n{traceback_txt}",
            )
