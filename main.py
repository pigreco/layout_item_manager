# -*- coding: utf-8 -*-
"""Modulo principale del plugin Layout Item Manager."""

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication
import os


class LayoutItemManager:
    """Classe principale del plugin."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = '&Layout Item Manager'
        self.dialog = None

    def tr(self, message):
        return QCoreApplication.translate('LayoutItemManager', message)

    def add_action(self, icon_path, text, callback, parent=None):
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        action = QAction(icon, text, parent or self.iface.mainWindow())
        action.triggered.connect(callback)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr('Gestisci Oggetti Layout'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)

    def run(self):
        from .dialogs import LayoutManagerDialog
        if self.dialog is None:
            self.dialog = LayoutManagerDialog(self.iface)
        self.dialog.refresh_layouts()
        self.dialog._aggiorna_combo_gruppi()
        self.dialog.show()
        self.dialog.raise_()
