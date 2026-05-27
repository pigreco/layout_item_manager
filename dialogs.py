# -*- coding: utf-8 -*-
"""Dialogo principale del plugin Layout Item Manager."""

import re
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QLineEdit,
    QTextEdit, QGroupBox, QListWidget, QListWidgetItem,
    QMessageBox, QRadioButton, QButtonGroup, QFrame, QAbstractItemView
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import QgsProject, QgsLayoutItem

from . import groups_manager


class LayoutManagerDialog(QDialog):
    """Dialogo principale per la gestione degli oggetti del layout."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle('Layout Item Manager')
        self.setMinimumSize(620, 680)
        self.resize(680, 720)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._tutti_gli_item = []   # lista di (id, oggetto)
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # --- Selezione layout ---
        box_layout = QGroupBox('Layout di stampa')
        hl = QHBoxLayout(box_layout)
        self.combo_layout = QComboBox()
        self.combo_layout.currentIndexChanged.connect(self._on_layout_changed)
        btn_refresh = QPushButton('↻')
        btn_refresh.setFixedWidth(30)
        btn_refresh.setToolTip('Aggiorna lista layout')
        btn_refresh.clicked.connect(self.refresh_layouts)
        hl.addWidget(self.combo_layout)
        hl.addWidget(btn_refresh)
        root.addWidget(box_layout)

        # --- Avviso ---
        lbl_avviso = QLabel(
            '⚠️  <b>Tutti gli oggetti del layout devono avere un nome definito dall\'utente</b><br>'
            '<span style="font-size:9pt;color:#666;">Proprietà oggetto → ID oggetto nel pannello Oggetti del layout</span>'
        )
        lbl_avviso.setTextFormat(Qt.TextFormat.RichText)
        lbl_avviso.setWordWrap(True)
        lbl_avviso.setStyleSheet(
            'background-color: #fff8e1;'
            'color: #333333;'
            'border: 1px solid #f0c040;'
            'border-radius: 4px;'
            'padding: 6px 10px;'
        )
        root.addWidget(lbl_avviso)

        # --- Modalità selezione ---
        box_mode = QGroupBox('Modalità di selezione')
        gl = QGridLayout(box_mode)

        self.rb_lista = QRadioButton('Lista di nomi (uno per riga)')
        self.rb_regex = QRadioButton('Espressione regolare (regex)')
        self.rb_gruppo = QRadioButton('Gruppo salvato')
        self.rb_lista.setChecked(True)

        self.bg = QButtonGroup(self)
        self.bg.addButton(self.rb_lista, 0)
        self.bg.addButton(self.rb_regex, 1)
        self.bg.addButton(self.rb_gruppo, 2)
        self.bg.buttonClicked.connect(self._on_mode_changed)

        gl.addWidget(self.rb_lista, 0, 0)
        gl.addWidget(self.rb_regex, 0, 1)
        gl.addWidget(self.rb_gruppo, 0, 2)

        # widget per lista
        self.txt_lista = QTextEdit()
        self.txt_lista.setPlaceholderText('panoramica\nmappa principale\nscala_1')
        self.txt_lista.setMaximumHeight(90)

        # widget per regex
        self.txt_regex = QLineEdit()
        self.txt_regex.setPlaceholderText('es: mappa.*  oppure  (scala|legenda)_\\d+')
        self.txt_regex.setVisible(False)

        # widget per gruppo
        frm_gruppo = QFrame()
        hl_g = QHBoxLayout(frm_gruppo)
        hl_g.setContentsMargins(0, 0, 0, 0)
        self.combo_gruppo = QComboBox()
        btn_del_gruppo = QPushButton('🗑')
        btn_del_gruppo.setFixedWidth(30)
        btn_del_gruppo.setToolTip('Elimina gruppo selezionato')
        btn_del_gruppo.clicked.connect(self._elimina_gruppo)
        hl_g.addWidget(self.combo_gruppo)
        hl_g.addWidget(btn_del_gruppo)
        frm_gruppo.setVisible(False)

        self._frm_gruppo = frm_gruppo

        gl.addWidget(self.txt_lista, 1, 0, 1, 3)
        gl.addWidget(self.txt_regex, 1, 0, 1, 3)
        gl.addWidget(frm_gruppo, 1, 0, 1, 3)

        # pulsante anteprima
        btn_preview = QPushButton('🔍  Mostra oggetti corrispondenti')
        btn_preview.clicked.connect(self._aggiorna_preview)
        gl.addWidget(btn_preview, 2, 0, 1, 3)

        root.addWidget(box_mode)

        # --- Anteprima oggetti trovati ---
        box_prev = QGroupBox('Oggetti trovati')
        vl_p = QVBoxLayout(box_prev)

        hl_prev = QHBoxLayout()
        self.lbl_count = QLabel('Nessuna ricerca effettuata')
        self.lbl_count.setStyleSheet('color: gray; font-style: italic;')
        btn_pulisci = QPushButton('✖  Pulisci')
        btn_pulisci.setFixedWidth(90)
        btn_pulisci.setToolTip('Svuota la lista degli oggetti trovati')
        btn_pulisci.clicked.connect(self._pulisci_preview)
        hl_prev.addWidget(self.lbl_count)
        hl_prev.addStretch()
        hl_prev.addWidget(btn_pulisci)

        self.list_preview = QListWidget()
        self.list_preview.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_preview.setMaximumHeight(160)

        vl_p.addLayout(hl_prev)
        vl_p.addWidget(self.list_preview)
        root.addWidget(box_prev)

        # --- Azioni ---
        box_azioni = QGroupBox('Azioni sugli oggetti trovati')
        gl2 = QGridLayout(box_azioni)

        # Visibilità
        lbl_vis = QLabel('Visibilità:')
        lbl_vis.setFont(QFont('', -1, QFont.Weight.Bold))
        btn_mostra = QPushButton('👁  Mostra')
        btn_nascondi = QPushButton('🚫  Nascondi')
        btn_toggle_vis = QPushButton('⇄  Inverti')
        btn_mostra.clicked.connect(lambda: self._applica_visibilita(True))
        btn_nascondi.clicked.connect(lambda: self._applica_visibilita(False))
        btn_toggle_vis.clicked.connect(lambda: self._applica_visibilita(None))

        gl2.addWidget(lbl_vis, 0, 0)
        gl2.addWidget(btn_mostra, 0, 1)
        gl2.addWidget(btn_nascondi, 0, 2)
        gl2.addWidget(btn_toggle_vis, 0, 3)

        # Separatore
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        gl2.addWidget(sep, 1, 0, 1, 4)

        # Blocco
        lbl_lock = QLabel('Blocco:')
        lbl_lock.setFont(QFont('', -1, QFont.Bold))
        btn_blocca = QPushButton('🔒  Blocca')
        btn_sblocca = QPushButton('🔓  Sblocca')
        btn_toggle_lock = QPushButton('⇄  Inverti')
        btn_blocca.clicked.connect(lambda: self._applica_blocco(True))
        btn_sblocca.clicked.connect(lambda: self._applica_blocco(False))
        btn_toggle_lock.clicked.connect(lambda: self._applica_blocco(None))

        gl2.addWidget(lbl_lock, 2, 0)
        gl2.addWidget(btn_blocca, 2, 1)
        gl2.addWidget(btn_sblocca, 2, 2)
        gl2.addWidget(btn_toggle_lock, 2, 3)

        root.addWidget(box_azioni)

        # --- Salva come gruppo ---
        box_salva = QGroupBox('Salva selezione come gruppo')
        hl_s = QHBoxLayout(box_salva)
        self.txt_nome_gruppo = QLineEdit()
        self.txt_nome_gruppo.setPlaceholderText('Nome del gruppo...')
        btn_salva = QPushButton('💾  Salva gruppo')
        btn_salva.clicked.connect(self._salva_gruppo)
        hl_s.addWidget(self.txt_nome_gruppo)
        hl_s.addWidget(btn_salva)
        root.addWidget(box_salva)

        # --- Tutti gli oggetti ---
        box_tutti = QGroupBox('Tutti gli oggetti del layout (doppio clic → copia nome)')
        vl_t = QVBoxLayout(box_tutti)
        self.list_tutti = QListWidget()
        self.list_tutti.setMaximumHeight(130)
        self.list_tutti.itemDoubleClicked.connect(self._copia_nome)
        vl_t.addWidget(self.list_tutti)
        root.addWidget(box_tutti)

        # --- Chiudi ---
        hl_close = QHBoxLayout()
        hl_close.addStretch()
        btn_close = QPushButton('Chiudi')
        btn_close.clicked.connect(self.hide)
        hl_close.addWidget(btn_close)
        root.addLayout(hl_close)

    # ------------------------------------------------------------------
    # Logica
    # ------------------------------------------------------------------
    def refresh_layouts(self):
        """Aggiorna la lista dei layout disponibili."""
        self.combo_layout.blockSignals(True)
        current = self.combo_layout.currentText()
        self.combo_layout.clear()
        manager = QgsProject.instance().layoutManager()
        for layout in manager.layouts():
            self.combo_layout.addItem(layout.name())
        idx = self.combo_layout.findText(current)
        if idx >= 0:
            self.combo_layout.setCurrentIndex(idx)
        self.combo_layout.blockSignals(False)
        self._on_layout_changed()
        self._aggiorna_combo_gruppi()

    def _get_layout(self):
        name = self.combo_layout.currentText()
        if not name:
            return None
        return QgsProject.instance().layoutManager().layoutByName(name)

    def _get_items(self, layout):
        """Restituisce lista di (id, item) per tutti gli item QgsLayoutItem."""
        result = []
        for item in layout.items():
            if isinstance(item, QgsLayoutItem):
                result.append((item.id(), item))
        return result

    def _on_layout_changed(self):
        layout = self._get_layout()
        self.list_tutti.clear()
        self._tutti_gli_item = []
        if not layout:
            return
        items = self._get_items(layout)
        self._tutti_gli_item = items
        for item_id, _ in items:
            display = item_id if item_id else '<senza nome>'
            self.list_tutti.addItem(display)

    def _on_mode_changed(self):
        mode = self.bg.checkedId()
        self.txt_lista.setVisible(mode == 0)
        self.txt_regex.setVisible(mode == 1)
        self._frm_gruppo.setVisible(mode == 2)

    def _match_items(self):
        """Restituisce gli item che corrispondono alla selezione corrente."""
        layout = self._get_layout()
        if not layout:
            QMessageBox.warning(self, 'Attenzione', 'Nessun layout selezionato.')
            return []

        items = self._get_items(layout)
        mode = self.bg.checkedId()

        if mode == 0:  # lista
            nomi = [n.strip() for n in self.txt_lista.toPlainText().splitlines() if n.strip()]
            return [(iid, obj) for iid, obj in items if iid in nomi]

        elif mode == 1:  # regex
            pattern = self.txt_regex.text().strip()
            if not pattern:
                QMessageBox.warning(self, 'Attenzione', 'Inserisci un\'espressione regolare.')
                return []
            try:
                rx = re.compile(pattern)
            except re.error as e:
                QMessageBox.critical(self, 'Regex non valida', str(e))
                return []
            return [(iid, obj) for iid, obj in items if iid and rx.search(iid)]

        elif mode == 2:  # gruppo
            nome_gruppo = self.combo_gruppo.currentText()
            if not nome_gruppo:
                QMessageBox.warning(self, 'Attenzione', 'Nessun gruppo selezionato.')
                return []
            gruppi = groups_manager.carica_gruppi()
            nomi = gruppi.get(nome_gruppo, [])
            return [(iid, obj) for iid, obj in items if iid in nomi]

        return []

    def _pulisci_preview(self):
        self.list_preview.clear()
        self.lbl_count.setText('Nessuna ricerca effettuata')
        self.lbl_count.setStyleSheet('color: gray; font-style: italic;')

    def _aggiorna_preview(self):
        matched = self._match_items()
        self.list_preview.clear()
        if not matched:
            self.lbl_count.setText('Nessun oggetto trovato.')
            self.lbl_count.setStyleSheet('color: red; font-style: italic;')
            return
        self.lbl_count.setText(f'{len(matched)} oggetto/i trovato/i:')
        self.lbl_count.setStyleSheet('color: green; font-weight: bold;')
        for iid, obj in matched:
            vis = obj.isVisible()
            blk = obj.isLocked()
            icona_vis = '👁' if vis else '🚫'
            icona_blk = '🔒' if blk else '🔓'
            item = QListWidgetItem(f'{icona_vis} {icona_blk}  {iid}')
            item.setForeground(QColor('#1a1a1a') if vis else QColor('#999999'))
            self.list_preview.addItem(item)

    def _applica_visibilita(self, visibile):
        """visibile=True/False/None (None=toggle)."""
        matched = self._match_items()
        if not matched:
            QMessageBox.information(self, 'Info', 'Nessun oggetto trovato con i criteri indicati.')
            return
        layout = self._get_layout()
        for iid, obj in matched:
            val = (not obj.isVisible()) if visibile is None else visibile
            obj.setVisibility(val)
        layout.refresh()
        self._aggiorna_preview()

    def _applica_blocco(self, bloccato):
        """bloccato=True/False/None (None=toggle)."""
        matched = self._match_items()
        if not matched:
            QMessageBox.information(self, 'Info', 'Nessun oggetto trovato con i criteri indicati.')
            return
        for iid, obj in matched:
            val = (not obj.isLocked()) if bloccato is None else bloccato
            obj.setLocked(val)
        self._aggiorna_preview()

    def _salva_gruppo(self):
        nome = self.txt_nome_gruppo.text().strip()
        if not nome:
            QMessageBox.warning(self, 'Attenzione', 'Inserisci un nome per il gruppo.')
            return
        matched = self._match_items()
        if not matched:
            QMessageBox.warning(self, 'Attenzione', 'Nessun oggetto trovato da salvare.')
            return
        nomi = [iid for iid, _ in matched if iid]
        groups_manager.aggiungi_gruppo(nome, nomi)
        self._aggiorna_combo_gruppi()
        QMessageBox.information(self, 'Salvato', f'Gruppo "{nome}" salvato con {len(nomi)} oggetti.')

    def _aggiorna_combo_gruppi(self):
        self.combo_gruppo.clear()
        for nome in groups_manager.carica_gruppi().keys():
            self.combo_gruppo.addItem(nome)

    def _elimina_gruppo(self):
        nome = self.combo_gruppo.currentText()
        if not nome:
            return
        r = QMessageBox.question(self, 'Conferma', f'Eliminare il gruppo "{nome}"?')
        if r == QMessageBox.StandardButton.Yes:
            groups_manager.rimuovi_gruppo(nome)
            self._aggiorna_combo_gruppi()

    def _copia_nome(self, item):
        """Doppio clic su un nome lo aggiunge alla lista."""
        nome = item.text()
        testo = self.txt_lista.toPlainText().strip()
        nomi_esistenti = [n.strip() for n in testo.splitlines()]
        if nome not in nomi_esistenti:
            nuovo = (testo + '\n' + nome).strip()
            self.txt_lista.setPlainText(nuovo)
            # switcha automaticamente alla modalità lista
            self.rb_lista.setChecked(True)
            self._on_mode_changed()
