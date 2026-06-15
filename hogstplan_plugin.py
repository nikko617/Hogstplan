import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .hogstplan_dialog import HogstplanDialog


class HogstplanPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None
        self.menu_namn = "Hogstplan"

    def initGui(self):
        icon_sti = os.path.join(os.path.dirname(__file__), "icon.png")
        icon = QIcon(icon_sti) if os.path.exists(icon_sti) else QIcon()

        self.action = QAction(icon, "Hogstplan", self.iface.mainWindow())
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu_namn, self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu(self.menu_namn, self.action)
            self.action = None

        self.dialog = None

    def run(self):
        self.dialog = HogstplanDialog(self.iface)
        self.dialog.exec_()
