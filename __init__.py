# -*- coding: utf-8 -*-
"""
Layout Item Manager
Gestisci visibilità e blocco degli oggetti del layout per nome, lista o regex.
"""


def classFactory(iface):
    from .main import LayoutItemManager
    return LayoutItemManager(iface)
