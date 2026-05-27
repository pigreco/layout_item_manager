# -*- coding: utf-8 -*-
"""Gestione dei gruppi personalizzati tramite variabili di progetto."""

from qgis.core import QgsProject

PREFIX = 'layout_gruppo_'


def carica_gruppi():
    """Carica i gruppi dalle variabili di progetto.
    Restituisce dict {nome_gruppo: [lista_nomi_oggetti]}
    """
    variabili = QgsProject.instance().customVariables()
    gruppi = {}
    for chiave, valore in variabili.items():
        if chiave.startswith(PREFIX):
            nome = chiave[len(PREFIX):]
            nomi = [n.strip() for n in valore.split(',') if n.strip()]
            gruppi[nome] = nomi
    return gruppi


def salva_gruppi(gruppi):
    """Sovrascrive tutte le variabili di gruppo nel progetto."""
    variabili = QgsProject.instance().customVariables()

    # Rimuovi tutte le variabili gruppo esistenti
    for chiave in list(variabili.keys()):
        if chiave.startswith(PREFIX):
            del variabili[chiave]

    # Riscrivi con i nuovi valori
    for nome, nomi_oggetti in gruppi.items():
        variabili[PREFIX + nome] = ','.join(nomi_oggetti)

    QgsProject.instance().setCustomVariables(variabili)


def aggiungi_gruppo(nome, nomi_oggetti):
    """Aggiunge o sovrascrive un gruppo."""
    gruppi = carica_gruppi()
    gruppi[nome] = nomi_oggetti
    salva_gruppi(gruppi)


def rimuovi_gruppo(nome):
    """Rimuove un gruppo."""
    gruppi = carica_gruppi()
    if nome in gruppi:
        del gruppi[nome]
        salva_gruppi(gruppi)
