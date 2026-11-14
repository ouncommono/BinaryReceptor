"""World-class bilingual (Persian RTL & English LTR) dashboard for BinaryReceptor v3.3.0."""
from __future__ import annotations

import csv
import io
import os
import queue
import re
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal, QObject, Slot
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QGroupBox,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QMessageBox,
    QFileDialog,
    QFrame,
    QScrollArea,
    QSizePolicy,
)

from src.config import (
    AppConfig,
    ConfigManager,
    canonicalize_token,
    parse_tokens,
    render_keystroke_output,
)
from src.core.bt_server import BluetoothServerController, get_local_bt_address
from src.core.deduplicator import ScanDeduplicator
from src.core.http_server import HttpServerController, ScanPayload
from src.core.key_injector import KeyInjector, win32_set_clipboard_text
from src.core.qr_helper import (
    BINARYEYE_FORMATS,
    build_forwarding_url,
    generate_qr_png_bytes,
    get_active_lan_ips,
    get_primary_lan_ip,
)
from src.core.sound import play_scanner_beep
from src.core.bt_radio import BluetoothRadioController, bt_radio_controller
from src.core.keyboard_hook import LowLevelKeyboardHook
from src.ui.i18n import tr
from src.ui.icon_gen import ensure_icons_exist
from src.ui.styles import DARK_STYLESHEET, LIGHT_STYLESHEET
from src.ui.tray import SystemTrayController
from src.version import __version__, APP_NAME

try:
    import winreg
except ImportError:
    winreg = None


def set_autostart_registry(enabled: bool) -> bool:
    """Configure Windows Run key for autostart."""
    if not winreg or os.name != "nt":
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        if getattr(sys, "frozen", False):
            cmd = f'"{sys.executable}"'
        else:
            entry = Path(__file__).resolve().parent.parent / "main.py"
            cmd = f'"{sys.executable}" "{entry}"'

        if enabled:
            winreg.SetValueEx(key, "BinaryReceptor", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "BinaryReceptor")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


class MainWindowSignals(QObject):
    scan_received = Signal(object, str, str)  # payload, processed_status, detail
    bt_status_changed = Signal(str)
    stats_updated = Signal()
    config_reloaded = Signal(object)


class MainWindow(QMainWindow):
    """Bilingual desktop companion server GUI for BinaryEye v3.1.0."""

    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__()
        self.config_manager = config_manager
        self.config = self.config_manager.current

        self.signals = MainWindowSignals()
        self.signals.scan_received.connect(self._on_scan_received_ui)
        self.signals.bt_status_changed.connect(self._on_bt_status_changed_ui)
        self.signals.stats_updated.connect(self._update_kpi_cards)
        self.signals.config_reloaded.connect(self._on_config_reloaded_from_disk)

        # Unified Single Deduplicator & Key Injector
        self.dedup = ScanDeduplicator(
            window_ms=self.config.deduplication_window_ms,
            enabled=self.config.deduplication_enabled,
        )
        self.injector = KeyInjector()

        # Thread-safe Time-Interval Cooldown Gate (Specification 2)
        self._scan_lock = threading.Lock()
        self._last_scan_timestamp: float = 0.0
        self._last_scan_text: str = ""
        self._last_scan_source: str = ""

        # Metrics Counters
        self.cnt_total = 0
        self.cnt_bt = 0
        self.cnt_http = 0
        self.cnt_dedup = 0

        # Scan worker queue (Unified central pipeline)
        self.scan_queue: queue.Queue[ScanPayload] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._worker_stop = threading.Event()

        # Server Controllers
        self.http_server: HttpServerController | None = None
        self.bt_server: BluetoothServerController | None = None
        self.is_server_active = False

        # Tier 1 & Tier 2: Low-Level Keyboard Hook & Bluetooth Radio Controller
        self.bt_radio = bt_radio_controller
        self.keyboard_hook = LowLevelKeyboardHook(
            on_barcode_captured=self._on_hook_barcode_captured,
            mode_getter=lambda: self.config.mode,
        )

        # Staged UI Settings state (for deferred save)
        self.has_unsaved_changes = False
        self._is_loading_settings_form = False

        # Set Window Properties
        self.setWindowTitle(f"BinaryReceptor v{__version__}")
        self.resize(1020, 740)
        self.setMinimumSize(880, 620)

        # Multi-resolution Icon
        assets_ico, res_ico = ensure_icons_exist()
        if assets_ico.exists():
            self.setWindowIcon(QIcon(str(assets_ico)))

        # Build UI Components
        self._init_ui()

        # System Tray Integration (Two-Way Sync)
        self.tray = SystemTrayController(self)
        self.tray.request_show_window.connect(self.show_and_activate)
        self.tray.request_show_qr.connect(self._show_qr_tab)
        self.tray.request_toggle_server.connect(self.toggle_server)
        self.tray.request_set_mode.connect(self.set_mode)
        self.tray.request_toggle_language.connect(self.toggle_language)
        self.tray.request_exit.connect(self.exit_application)

        # Apply Initial Language and Theme
        self.apply_language(self.config.language)
        self.apply_theme(self.config.theme)

        # Start Unified Background Queue Worker
        self._start_worker_thread()

        # Listen for hot-reloads from disk
        self.config_manager.add_listener(lambda cfg: self.signals.config_reloaded.emit(cfg))

        # Auto-start server if enabled
        if self.config.auto_start:
            QTimer.singleShot(400, self.start_server)

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # 1. Header Card (Title, Master Power Button, Theme/Lang Switchers)
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(14, 10, 14, 10)

        title_box = QVBoxLayout()
        self.lbl_app_title = QLabel(f"BinaryReceptor v{__version__}")
        self.lbl_app_title.setObjectName("AppTitle")
        self.lbl_app_subtitle = QLabel(tr("app_subtitle", self.config.language))
        self.lbl_app_subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(self.lbl_app_title)
        title_box.addWidget(self.lbl_app_subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Master Power Button (Requirement 5: explicit sizing & initial sync to eliminate size glitch)
        self.btn_master_power = QPushButton()
        self.btn_master_power.setObjectName("MasterPowerBtnStopped")
        self.btn_master_power.setMinimumWidth(140)
        self.btn_master_power.setMinimumHeight(38)
        self.btn_master_power.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_master_power.clicked.connect(self.toggle_server)
        self._update_power_button()
        self.btn_master_power.updateGeometry()
        header_layout.addWidget(self.btn_master_power)

        # Theme Switcher Button
        self.btn_theme_toggle = QPushButton()
        self.btn_theme_toggle.setObjectName("SecondaryBtn")
        self.btn_theme_toggle.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.btn_theme_toggle)

        # Language Switcher Button
        self.btn_lang_toggle = QPushButton()
        self.btn_lang_toggle.setObjectName("SecondaryBtn")
        self.btn_lang_toggle.clicked.connect(self.toggle_language)
        header_layout.addWidget(self.btn_lang_toggle)

        main_layout.addWidget(header_card)

        # 2. Sleek Compact Single-Row Horizontal Status Bar (Requirement 6)
        self.compact_status_bar = QFrame()
        self.compact_status_bar.setObjectName("CompactStatusBar")
        cs_layout = QHBoxLayout(self.compact_status_bar)
        cs_layout.setContentsMargins(12, 4, 12, 4)
        cs_layout.setSpacing(14)

        # Item 1: Master Server Status Pill
        row_server = QHBoxLayout()
        row_server.setSpacing(6)
        self.lbl_strip_server = QLabel(tr("strip_server", self.config.language))
        self.lbl_strip_server.setProperty("class", "StatusStripLabel")
        self.pill_server = QLabel(tr("status_stopped", self.config.language))
        self.pill_server.setProperty("class", "StatusPillStopped")
        row_server.addWidget(self.lbl_strip_server)
        row_server.addWidget(self.pill_server)
        cs_layout.addLayout(row_server)

        # Item 2: Mode Pill
        row_mode = QHBoxLayout()
        row_mode.setSpacing(6)
        self.lbl_strip_mode = QLabel(tr("strip_mode", self.config.language))
        self.lbl_strip_mode.setProperty("class", "StatusStripLabel")
        self.pill_mode = QLabel(tr("opt_mode_both", self.config.language))
        self.pill_mode.setProperty("class", "StatusPillInactive")
        row_mode.addWidget(self.lbl_strip_mode)
        row_mode.addWidget(self.pill_mode)
        cs_layout.addLayout(row_mode)

        # Item 3: Bluetooth Status Pill
        row_bt = QHBoxLayout()
        row_bt.setSpacing(6)
        self.lbl_strip_bt = QLabel(tr("strip_bt", self.config.language))
        self.lbl_strip_bt.setProperty("class", "StatusStripLabel")
        self.pill_bt = QLabel(tr("status_standby", self.config.language))
        self.pill_bt.setProperty("class", "StatusPillInactive")
        row_bt.addWidget(self.lbl_strip_bt)
        row_bt.addWidget(self.pill_bt)
        cs_layout.addLayout(row_bt)

        # Item 4: HTTP Status Pill
        row_http = QHBoxLayout()
        row_http.setSpacing(6)
        self.lbl_strip_http = QLabel(tr("strip_http", self.config.language))
        self.lbl_strip_http.setProperty("class", "StatusStripLabel")
        self.pill_http = QLabel(tr("status_standby", self.config.language))
        self.pill_http.setProperty("class", "StatusPillInactive")
        row_http.addWidget(self.lbl_strip_http)
        row_http.addWidget(self.pill_http)
        cs_layout.addLayout(row_http)

        cs_layout.addStretch()
        main_layout.addWidget(self.compact_status_bar)

        # Backward-compatible references for internal slots / tests
        self.card_server = self.pill_server
        self.card_bt = self.pill_bt
        self.card_http = self.pill_http
        self.card_mode = self.pill_mode
        self.lbl_card_server_title = self.lbl_strip_server
        self.lbl_card_bt_title = self.lbl_strip_bt
        self.lbl_card_http_title = self.lbl_strip_http
        self.lbl_card_mode_title = self.lbl_strip_mode
        self.lbl_card_server_val = self.pill_server
        self.lbl_card_bt_val = self.pill_bt
        self.lbl_card_http_val = self.pill_http
        self.lbl_card_mode_val = self.pill_mode

        # 4. Main Tabs Navigation
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, stretch=1)

        self._build_dashboard_tab()
        self._build_wedge_tab()
        self._build_connection_tab()
        self._build_settings_tab()

        self.kpi_cards = {
            "kpi_total_scans": (self.lbl_kpi_total_desc, self.lbl_kpi_total),
            "kpi_bt_scans": (self.lbl_kpi_bt_desc, self.lbl_kpi_bt),
            "kpi_http_scans": (self.lbl_kpi_http_desc, self.lbl_kpi_http),
            "kpi_dedup_blocked": (self.lbl_kpi_dedup_desc, self.lbl_kpi_dedup),
        }

    # ==========================================================================
    # TAB 1: Live Activity Log & History
    # ==========================================================================
    def _build_dashboard_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Scans Statistics Summary Header Card (Specification 5)
        self.stats_summary_card = QFrame()
        self.stats_summary_card.setObjectName("StatsSummaryCard")
        stats_layout = QHBoxLayout(self.stats_summary_card)
        stats_layout.setContentsMargins(12, 8, 12, 8)
        stats_layout.setSpacing(12)

        # Total Scans Card
        card_total = QFrame()
        card_total.setProperty("class", "MiniKpiCard")
        tl = QVBoxLayout(card_total)
        tl.setContentsMargins(8, 4, 8, 4)
        tl.setSpacing(2)
        self.lbl_kpi_total_desc = QLabel(tr("kpi_total_scans", self.config.language))
        self.lbl_kpi_total_desc.setProperty("class", "MiniKpiTitle")
        self.lbl_kpi_total = QLabel("0")
        self.lbl_kpi_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        tl.addWidget(self.lbl_kpi_total_desc)
        tl.addWidget(self.lbl_kpi_total)
        stats_layout.addWidget(card_total)

        # Bluetooth Scans Card
        card_bt = QFrame()
        card_bt.setProperty("class", "MiniKpiCard")
        bl = QVBoxLayout(card_bt)
        bl.setContentsMargins(8, 4, 8, 4)
        bl.setSpacing(2)
        self.lbl_kpi_bt_desc = QLabel(tr("kpi_bt_scans", self.config.language))
        self.lbl_kpi_bt_desc.setProperty("class", "MiniKpiTitle")
        self.lbl_kpi_bt = QLabel("0")
        self.lbl_kpi_bt.setStyleSheet("font-size: 18px; font-weight: bold; color: #a78bfa;")
        bl.addWidget(self.lbl_kpi_bt_desc)
        bl.addWidget(self.lbl_kpi_bt)
        stats_layout.addWidget(card_bt)

        # HTTP Scans Card
        card_http = QFrame()
        card_http.setProperty("class", "MiniKpiCard")
        hl = QVBoxLayout(card_http)
        hl.setContentsMargins(8, 4, 8, 4)
        hl.setSpacing(2)
        self.lbl_kpi_http_desc = QLabel(tr("kpi_http_scans", self.config.language))
        self.lbl_kpi_http_desc.setProperty("class", "MiniKpiTitle")
        self.lbl_kpi_http = QLabel("0")
        self.lbl_kpi_http.setStyleSheet("font-size: 18px; font-weight: bold; color: #34d399;")
        hl.addWidget(self.lbl_kpi_http_desc)
        hl.addWidget(self.lbl_kpi_http)
        stats_layout.addWidget(card_http)

        # Duplicates Blocked Card
        card_dedup = QFrame()
        card_dedup.setProperty("class", "MiniKpiCard")
        dl = QVBoxLayout(card_dedup)
        dl.setContentsMargins(8, 4, 8, 4)
        dl.setSpacing(2)
        self.lbl_kpi_dedup_desc = QLabel(tr("kpi_dedup_blocked", self.config.language))
        self.lbl_kpi_dedup_desc.setProperty("class", "MiniKpiTitle")
        self.lbl_kpi_dedup = QLabel("0")
        self.lbl_kpi_dedup.setStyleSheet("font-size: 18px; font-weight: bold; color: #f59e0b;")
        dl.addWidget(self.lbl_kpi_dedup_desc)
        dl.addWidget(self.lbl_kpi_dedup)
        stats_layout.addWidget(card_dedup)

        layout.addWidget(self.stats_summary_card)

        self.table_history = QTableWidget(0, 5)
        self.table_history.setHorizontalHeaderLabels([
            tr("col_time", self.config.language),
            tr("col_channel", self.config.language),
            tr("col_format", self.config.language),
            tr("col_content", self.config.language),
            tr("col_status", self.config.language),
        ])
        header = self.table_history.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table_history)

        btn_bar = QHBoxLayout()
        self.btn_retype = QPushButton(tr("btn_retype", self.config.language))
        self.btn_retype.clicked.connect(self._retype_selected_scan)
        btn_bar.addWidget(self.btn_retype)

        self.btn_copy_content = QPushButton(tr("btn_copy", self.config.language))
        self.btn_copy_content.setObjectName("SecondaryBtn")
        self.btn_copy_content.clicked.connect(self._copy_selected_scan)
        btn_bar.addWidget(self.btn_copy_content)

        btn_bar.addStretch()

        self.btn_export_csv = QPushButton(tr("btn_export_csv", self.config.language))
        self.btn_export_csv.setObjectName("SecondaryBtn")
        self.btn_export_csv.clicked.connect(self._export_csv)
        btn_bar.addWidget(self.btn_export_csv)

        self.btn_clear_log = QPushButton(tr("btn_clear_log", self.config.language))
        self.btn_clear_log.setObjectName("SecondaryBtn")
        self.btn_clear_log.clicked.connect(self._clear_history_log)
        btn_bar.addWidget(self.btn_clear_log)

        layout.addLayout(btn_bar)
        self.tabs.addTab(tab, tr("tab_dashboard", self.config.language))

    # ==========================================================================
    # TAB 2: Visual Prefix & Suffix Builder
    # ==========================================================================
    def _build_wedge_tab(self) -> None:
        tab = QWidget()
        tab_outer = QVBoxLayout(tab)
        tab_outer.setContentsMargins(0, 0, 0, 0)

        # Requirement 2: Wrap entire Prefix/Suffix content in a smooth scroll container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        self.lbl_wedge_title = QLabel(tr("wedge_title", self.config.language))
        self.lbl_wedge_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        layout.addWidget(self.lbl_wedge_title)

        self.lbl_wedge_desc = QLabel(tr("wedge_desc", self.config.language))
        self.lbl_wedge_desc.setWordWrap(True)
        self.lbl_wedge_desc.setStyleSheet("color: #94a3b8; margin-bottom: 4px;")
        layout.addWidget(self.lbl_wedge_desc)

        # Prefix Builder Card
        self.grp_prefix = QGroupBox(tr("lbl_prefix", self.config.language))
        pl = QVBoxLayout(self.grp_prefix)
        pl.setSpacing(10)

        p_row1 = QHBoxLayout()
        self.combo_prefix_preset = QComboBox()
        self.combo_prefix_preset.setMinimumHeight(30)
        self.combo_prefix_preset.currentIndexChanged.connect(self._on_prefix_preset_changed)
        p_row1.addWidget(self.combo_prefix_preset)

        self.txt_prefix = QLineEdit(self.config.prefix)
        self.txt_prefix.setMinimumHeight(30)
        self.txt_prefix.textChanged.connect(self._on_wedge_text_changed)
        p_row1.addWidget(self.txt_prefix, stretch=1)

        self.btn_clear_p = QPushButton(tr("btn_clear_field", self.config.language))
        self.btn_clear_p.setObjectName("SecondaryBtn")
        self.btn_clear_p.setMinimumHeight(30)
        self.btn_clear_p.clicked.connect(lambda: self.txt_prefix.clear())
        p_row1.addWidget(self.btn_clear_p)
        pl.addLayout(p_row1)

        # Interactive Token Chips for Prefix in a clean 4-column responsive grid
        p_chips_grid = QGridLayout()
        p_chips_grid.setSpacing(6)
        self.prefix_chip_buttons: list[tuple[QPushButton, str]] = []
        chip_specs = [
            ("{ENTER}", "btn_add_enter", 0, 0),
            ("{TAB}", "btn_add_tab", 0, 1),
            ("{SPACE}", "btn_add_space", 0, 2),
            ("{BACKSPACE}", "btn_add_backspace", 0, 3),
            ("{ESC}", "btn_add_esc", 1, 0),
            ("{DOWN}", "btn_add_down", 1, 1),
            ("{DATE}", "btn_add_date", 1, 2),
            ("{TIME}", "btn_add_time", 1, 3),
        ]
        for token, key, r, c in chip_specs:
            btn = QPushButton(tr(key, self.config.language))
            btn.setObjectName("ChipBtn")
            btn.setMinimumHeight(28)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked=False, t=token: self._append_token(self.txt_prefix, t))
            p_chips_grid.addWidget(btn, r, c)
            self.prefix_chip_buttons.append((btn, key))
        pl.addLayout(p_chips_grid)
        layout.addWidget(self.grp_prefix)

        # Suffix Builder Card
        self.grp_suffix = QGroupBox(tr("lbl_suffix", self.config.language))
        sl = QVBoxLayout(self.grp_suffix)
        sl.setSpacing(10)

        s_row1 = QHBoxLayout()
        self.combo_suffix_preset = QComboBox()
        self.combo_suffix_preset.setMinimumHeight(30)
        self.combo_suffix_preset.currentIndexChanged.connect(self._on_suffix_preset_changed)
        s_row1.addWidget(self.combo_suffix_preset)

        self.txt_suffix = QLineEdit(self.config.suffix)
        self.txt_suffix.setMinimumHeight(30)
        self.txt_suffix.textChanged.connect(self._on_wedge_text_changed)
        s_row1.addWidget(self.txt_suffix, stretch=1)

        self.btn_clear_s = QPushButton(tr("btn_clear_field", self.config.language))
        self.btn_clear_s.setObjectName("SecondaryBtn")
        self.btn_clear_s.setMinimumHeight(30)
        self.btn_clear_s.clicked.connect(lambda: self.txt_suffix.clear())
        s_row1.addWidget(self.btn_clear_s)
        sl.addLayout(s_row1)

        # Interactive Token Chips for Suffix in a clean 4-column responsive grid
        s_chips_grid = QGridLayout()
        s_chips_grid.setSpacing(6)
        self.suffix_chip_buttons: list[tuple[QPushButton, str]] = []
        for token, key, r, c in chip_specs:
            btn = QPushButton(tr(key, self.config.language))
            btn.setObjectName("ChipBtn")
            btn.setMinimumHeight(28)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked=False, t=token: self._append_token(self.txt_suffix, t))
            s_chips_grid.addWidget(btn, r, c)
            self.suffix_chip_buttons.append((btn, key))
        sl.addLayout(s_chips_grid)
        layout.addWidget(self.grp_suffix)

        # Live Keystroke Preview Box (Renders TRUE output without {ENTER} syntax)
        self.grp_preview = QGroupBox(tr("lbl_preview", self.config.language))
        pr_layout = QVBoxLayout(self.grp_preview)
        self.lbl_preview_text = QLabel()
        self.lbl_preview_text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 14px; color: #38bdf8; background: #0b1120; border: 1px solid #1e293b; border-radius: 6px; padding: 12px; min-height: 48px;"
        )
        self.lbl_preview_text.setWordWrap(True)
        pr_layout.addWidget(self.lbl_preview_text)
        layout.addWidget(self.grp_preview)

        layout.addStretch()
        scroll.setWidget(content)
        tab_outer.addWidget(scroll)

        self._populate_token_presets(self.combo_prefix_preset)
        self._populate_token_presets(self.combo_suffix_preset)
        self._update_wedge_preview()
        self.tabs.addTab(tab, tr("tab_wedge", self.config.language))

    def _populate_token_presets(self, combo: QComboBox) -> None:
        combo.clear()
        combo.addItem(tr("preset_custom", self.config.language), "CUSTOM")
        combo.addItem(tr("preset_none", self.config.language), "")
        combo.addItem(tr("preset_enter", self.config.language), "{ENTER}")
        combo.addItem(tr("preset_tab", self.config.language), "{TAB}")
        combo.addItem(tr("preset_space", self.config.language), "{SPACE}")
        combo.addItem(tr("preset_double_enter", self.config.language), "{ENTER}{ENTER}")
        combo.addItem(tr("preset_tab_enter", self.config.language), "{TAB}{ENTER}")
        combo.addItem(tr("preset_backspace", self.config.language), "{BACKSPACE}")
        combo.addItem(tr("preset_esc", self.config.language), "{ESC}")
        combo.addItem(tr("preset_down", self.config.language), "{DOWN}")

    def _append_token(self, line_edit: QLineEdit, token: str) -> None:
        line_edit.setText(line_edit.text() + token)

    def _on_prefix_preset_changed(self, idx: int) -> None:
        val = self.combo_prefix_preset.currentData()
        if val != "CUSTOM":
            self.txt_prefix.setText(val)

    def _on_suffix_preset_changed(self, idx: int) -> None:
        val = self.combo_suffix_preset.currentData()
        if val != "CUSTOM":
            self.txt_suffix.setText(val)

    def _on_wedge_text_changed(self) -> None:
        self._update_wedge_preview()
        # Direct live typing updates active wedge prefix/suffix and config
        self.config_manager.save(
            prefix=self.txt_prefix.text(),
            suffix=self.txt_suffix.text(),
        )

    def _update_wedge_preview(self) -> None:
        sample = "987654321012"
        p = self.txt_prefix.text()
        s = self.txt_suffix.text()
        # Requirement 11: Render true simulated output (actual \n, \t, etc.), never raw {ENTER}
        rendered = render_keystroke_output(p, sample, s)
        # Format display with visible whitespace indicators for clarity
        display_lines = rendered.split("\n")
        escaped_preview = " ↵\n".join(display_lines)
        escaped_preview = escaped_preview.replace("\t", "    ⇥ ")
        self.lbl_preview_text.setText(escaped_preview if rendered else "(empty)")

    # ==========================================================================
    # TAB 3: Connection Assistant & Clean QR Generator (Requirement 3 & 4)
    # ==========================================================================
    def _build_connection_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)

        # Top Network Interface Bar
        top_bar = QHBoxLayout()
        self.lbl_lan_ip_header = QLabel(tr("lbl_lan_ip", self.config.language))
        top_bar.addWidget(self.lbl_lan_ip_header)

        self.combo_interfaces = QComboBox()
        self.detected_ips = get_active_lan_ips()
        for iface in self.detected_ips:
            label = f"{iface['ip']} ({iface['interface']})"
            self.combo_interfaces.addItem(label, iface["ip"])
        self.combo_interfaces.currentIndexChanged.connect(self._on_lan_interface_changed)
        top_bar.addWidget(self.combo_interfaces, stretch=1)

        self.btn_refresh_net = QPushButton("⟳")
        self.btn_refresh_net.setObjectName("SecondaryBtn")
        self.btn_refresh_net.clicked.connect(self._refresh_network_interfaces)
        top_bar.addWidget(self.btn_refresh_net)

        self.btn_copy_active_url = QPushButton(tr("btn_copy_url", self.config.language))
        self.btn_copy_active_url.clicked.connect(self._copy_http_forwarding_url)
        top_bar.addWidget(self.btn_copy_active_url)

        layout.addLayout(top_bar)

        # Sub-tabs for Connection Modes
        self.qr_subtabs = QTabWidget()
        layout.addWidget(self.qr_subtabs, stretch=1)

        # Subtab 1: Standard Forwarding URL with 4 BinaryEye Request Types
        sub1 = QWidget()
        l1 = QHBoxLayout(sub1)
        self.lbl_qr_url_img = QLabel()
        self.lbl_qr_url_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l1.addWidget(self.lbl_qr_url_img)

        info1 = QVBoxLayout()
        self.lbl_req_type_hdr = QLabel(tr("lbl_binaryeye_req_type", self.config.language))
        self.lbl_req_type_hdr.setStyleSheet("font-weight: bold; margin-top: 4px;")
        info1.addWidget(self.lbl_req_type_hdr)

        self.combo_req_type = QComboBox()
        self.combo_req_type.addItem(tr("opt_req_post_json", self.config.language), "post_json")
        self.combo_req_type.addItem(tr("opt_req_post_form", self.config.language), "post_form")
        self.combo_req_type.addItem(tr("opt_req_get_query", self.config.language), "get_query")
        self.combo_req_type.addItem(tr("opt_req_get_append", self.config.language), "get_append")
        self.combo_req_type.addItem(tr("opt_req_get_template", self.config.language), "get_template")
        self.combo_req_type.currentIndexChanged.connect(self._refresh_all_qrs)
        info1.addWidget(self.combo_req_type)

        self.lbl_desc_qr_url = QLabel(tr("desc_req_post_json", self.config.language))
        self.lbl_desc_qr_url.setWordWrap(True)
        self.lbl_desc_qr_url.setStyleSheet("color: #94a3b8; margin-top: 6px; margin-bottom: 6px;")
        info1.addWidget(self.lbl_desc_qr_url)

        self.lbl_url_field_hdr = QLabel(tr("lbl_http_url", self.config.language))
        info1.addWidget(self.lbl_url_field_hdr)

        url_row = QHBoxLayout()
        self.txt_url_display = QLineEdit()
        self.txt_url_display.setReadOnly(True)
        url_row.addWidget(self.txt_url_display, stretch=1)
        self.btn_copy_url = QPushButton(tr("btn_copy_url", self.config.language))
        self.btn_copy_url.setObjectName("SecondaryBtn")
        self.btn_copy_url.clicked.connect(self._copy_http_forwarding_url)
        url_row.addWidget(self.btn_copy_url)
        info1.addLayout(url_row)
        info1.addStretch()
        l1.addLayout(info1, stretch=1)
        self.qr_subtabs.addTab(sub1, tr("subtab_qr_url", self.config.language))

        # Subtab 2: Barcode Generator (100% Raw Text Verbatim)
        sub2 = QWidget()
        l2 = QHBoxLayout(sub2)
        self.lbl_qr_encode_img = QLabel()
        self.lbl_qr_encode_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l2.addWidget(self.lbl_qr_encode_img)

        form2 = QVBoxLayout()
        self.lbl_desc_qr_encode = QLabel(tr("desc_qr_encode", self.config.language))
        self.lbl_desc_qr_encode.setWordWrap(True)
        form2.addWidget(self.lbl_desc_qr_encode)

        self.lbl_encode_txt_hdr = QLabel(tr("lbl_encode_text", self.config.language))
        form2.addWidget(self.lbl_encode_txt_hdr)
        self.txt_encode_content = QLineEdit("SAMPLE-BARCODE-12345")
        self.txt_encode_content.textChanged.connect(self._render_encode_qr)
        form2.addWidget(self.txt_encode_content)

        self.lbl_encode_fmt_hdr = QLabel(tr("lbl_encode_format", self.config.language))
        form2.addWidget(self.lbl_encode_fmt_hdr)
        self.combo_encode_format = QComboBox()
        self.combo_encode_format.addItems(BINARYEYE_FORMATS)
        self.combo_encode_format.currentIndexChanged.connect(self._render_encode_qr)
        form2.addWidget(self.combo_encode_format)

        form2.addStretch()
        l2.addLayout(form2, stretch=1)
        self.qr_subtabs.addTab(sub2, tr("subtab_qr_encode", self.config.language))

        self.tabs.addTab(tab, tr("tab_connection", self.config.language))
        self._refresh_all_qrs()

    def _on_lan_interface_changed(self) -> None:
        self._refresh_all_qrs()

    def _refresh_network_interfaces(self) -> None:
        self.combo_interfaces.clear()
        self.detected_ips = get_active_lan_ips()
        for iface in self.detected_ips:
            label = f"{iface['ip']} ({iface['interface']})"
            self.combo_interfaces.addItem(label, iface["ip"])
        self._refresh_all_qrs()

    def _get_selected_ip(self) -> str:
        ip = self.combo_interfaces.currentData()
        return str(ip) if ip else get_primary_lan_ip()

    def _refresh_all_qrs(self) -> None:
        ip = self._get_selected_ip()
        port = self.config.http_port
        req_type = self.combo_req_type.currentData() if hasattr(self, "combo_req_type") else "post_json"

        # 1. Clean HTTP Forwarding URL matching selected BinaryEye request type
        url = build_forwarding_url(ip, port, req_type)
        self.txt_url_display.setText(url)

        desc_key = f"desc_req_{req_type}"
        self.lbl_desc_qr_url.setText(tr(desc_key, self.config.language))

        png1 = generate_qr_png_bytes(url, box_size=5, border=1)
        pm1 = QPixmap()
        pm1.loadFromData(png1)
        self.lbl_qr_url_img.setPixmap(pm1.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))

        # 2. Barcode Generator (100% Raw Text Verbatim)
        self._render_encode_qr()

    def _render_encode_qr(self) -> None:
        # Requirement 7: Generate QR containing ONLY raw text verbatim, 0 binaryeye://encode wrapper!
        raw_text = self.txt_encode_content.text() or "BinaryReceptor"
        png = generate_qr_png_bytes(raw_text, box_size=5, border=1)
        pm = QPixmap()
        pm.loadFromData(png)
        self.lbl_qr_encode_img.setPixmap(pm.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))

    def _copy_http_forwarding_url(self) -> None:
        url = self.txt_url_display.text()
        QApplication.clipboard().setText(url)
        QMessageBox.information(self, tr("app_title", self.config.language), tr("url_copied", self.config.language))

    # ==========================================================================
    # TAB 4: Settings & Hardware (Sticky Footer + Staged Deferred Save)
    # ==========================================================================
    def _build_settings_tab(self) -> None:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(8)

        # Scrollable Form Body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(4, 4, 4, 4)

        # 1. General & Operation Mode
        self.grp_gen = QGroupBox(tr("sec_general", self.config.language))
        gl = QGridLayout(self.grp_gen)

        self.lbl_mode_setting = QLabel(tr("lbl_mode", self.config.language))
        gl.addWidget(self.lbl_mode_setting, 0, 0)
        self.combo_mode = QComboBox()
        self.combo_mode.addItem(tr("opt_mode_both", self.config.language), "both")
        self.combo_mode.addItem(tr("opt_mode_http", self.config.language), "http")
        self.combo_mode.addItem(tr("opt_mode_bt", self.config.language), "bluetooth")
        gl.addWidget(self.combo_mode, 0, 1)

        self.chk_auto_start_srv = QCheckBox(tr("chk_auto_start", self.config.language))
        gl.addWidget(self.chk_auto_start_srv, 1, 0, 1, 2)

        self.chk_start_windows = QCheckBox(tr("chk_start_windows", self.config.language))
        gl.addWidget(self.chk_start_windows, 2, 0, 1, 2)

        self.chk_min_tray = QCheckBox(tr("chk_min_tray", self.config.language))
        gl.addWidget(self.chk_min_tray, 3, 0, 1, 2)

        # Sound Beep + Test Sound Button
        sound_row = QHBoxLayout()
        self.chk_beep = QCheckBox(tr("chk_beep", self.config.language))
        sound_row.addWidget(self.chk_beep)
        self.btn_test_sound = QPushButton(tr("btn_test_sound", self.config.language))
        self.btn_test_sound.setObjectName("SecondaryBtn")
        self.btn_test_sound.clicked.connect(lambda: play_scanner_beep())
        sound_row.addWidget(self.btn_test_sound)
        sound_row.addStretch()
        gl.addLayout(sound_row, 4, 0, 1, 2)

        layout.addWidget(self.grp_gen)

        # 2. Network & HTTP Server
        self.grp_net = QGroupBox(tr("sec_network", self.config.language))
        nl = QGridLayout(self.grp_net)

        self.lbl_host_setting = QLabel(tr("lbl_host", self.config.language))
        nl.addWidget(self.lbl_host_setting, 0, 0)
        self.txt_host = QLineEdit()
        nl.addWidget(self.txt_host, 0, 1)

        self.lbl_port_setting = QLabel(tr("lbl_port", self.config.language))
        nl.addWidget(self.lbl_port_setting, 1, 0)
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        nl.addWidget(self.spin_port, 1, 1)

        layout.addWidget(self.grp_net)

        # 3. Deduplication Engine (Time-Interval Cooldown Gate)
        self.grp_dedup = QGroupBox(tr("sec_dedup", self.config.language))
        dl = QVBoxLayout(self.grp_dedup)
        dl.setSpacing(8)

        self.chk_dedup = QCheckBox(tr("chk_dedup_enabled", self.config.language))
        dl.addWidget(self.chk_dedup)

        row_interval = QHBoxLayout()
        self.lbl_dedup_win = QLabel(tr("lbl_dedup_interval", self.config.language))
        row_interval.addWidget(self.lbl_dedup_win)

        self.spin_dedup_win = QSpinBox()
        self.spin_dedup_win.setRange(100, 10000)
        self.spin_dedup_win.setSingleStep(250)
        self.spin_dedup_win.setSuffix(" ms")
        row_interval.addWidget(self.spin_dedup_win)
        dl.addLayout(row_interval)

        # Preset interval buttons
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        self.lbl_dedup_presets = QLabel(tr("lbl_dedup_presets", self.config.language))
        preset_row.addWidget(self.lbl_dedup_presets)

        for ms_val, label in [(500, "500ms"), (1000, "1s"), (1500, "1.5s"), (2000, "2s"), (3000, "3s")]:
            btn = QPushButton(label)
            btn.setObjectName("PresetIntervalBtn")
            btn.setMinimumHeight(28)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked=False, v=ms_val: self.spin_dedup_win.setValue(v))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        dl.addLayout(preset_row)

        self.lbl_dedup_hint = QLabel(tr("desc_dedup_cooldown", self.config.language))
        self.lbl_dedup_hint.setWordWrap(True)
        self.lbl_dedup_hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        dl.addWidget(self.lbl_dedup_hint)

        layout.addWidget(self.grp_dedup)

        # 4. Keystroke Output & Wedging
        self.grp_wedge = QGroupBox(tr("sec_wedge", self.config.language))
        wl = QGridLayout(self.grp_wedge)

        self.lbl_out_mode = QLabel(tr("lbl_out_mode", self.config.language))
        wl.addWidget(self.lbl_out_mode, 0, 0)
        self.combo_out_mode = QComboBox()
        self.combo_out_mode.addItem(tr("opt_out_type", self.config.language), "type")
        self.combo_out_mode.addItem(tr("opt_out_paste", self.config.language), "paste")
        self.combo_out_mode.addItem(tr("opt_out_copy", self.config.language), "copy_only")
        self.combo_out_mode.addItem(tr("opt_out_log", self.config.language), "log_only")
        wl.addWidget(self.combo_out_mode, 0, 1)

        self.lbl_inter_key = QLabel(tr("lbl_inter_key", self.config.language))
        wl.addWidget(self.lbl_inter_key, 1, 0)
        self.spin_inter_key = QSpinBox()
        self.spin_inter_key.setRange(0, 100)
        wl.addWidget(self.spin_inter_key, 1, 1)

        self.lbl_pre_delay = QLabel(tr("lbl_pre_delay", self.config.language))
        wl.addWidget(self.lbl_pre_delay, 2, 0)
        self.spin_pre_delay = QSpinBox()
        self.spin_pre_delay.setRange(0, 5000)
        self.spin_pre_delay.setSingleStep(100)
        wl.addWidget(self.spin_pre_delay, 2, 1)

        self.chk_restore_clip = QCheckBox(tr("chk_restore_clip", self.config.language))
        wl.addWidget(self.chk_restore_clip, 3, 0, 1, 2)

        layout.addWidget(self.grp_wedge)

        # 5. Filters & Transforms
        self.grp_filt = QGroupBox(tr("sec_filters", self.config.language))
        fl = QGridLayout(self.grp_filt)

        self.chk_trim_space = QCheckBox(tr("chk_trim_space", self.config.language))
        fl.addWidget(self.chk_trim_space, 0, 0, 1, 2)

        self.lbl_replace_nl = QLabel(tr("lbl_replace_newlines", self.config.language))
        fl.addWidget(self.lbl_replace_nl, 1, 0)
        self.combo_nl = QComboBox()
        self.combo_nl.addItem(tr("opt_nl_none", self.config.language), "none")
        self.combo_nl.addItem(tr("opt_nl_tab", self.config.language), "tab")
        self.combo_nl.addItem(tr("opt_nl_space", self.config.language), "space")
        fl.addWidget(self.combo_nl, 1, 1)

        self.lbl_regex_pat = QLabel(tr("lbl_regex_pat", self.config.language))
        fl.addWidget(self.lbl_regex_pat, 2, 0)
        self.txt_regex_pat = QLineEdit()
        fl.addWidget(self.txt_regex_pat, 2, 1)

        self.lbl_regex_rep = QLabel(tr("lbl_regex_rep", self.config.language))
        fl.addWidget(self.lbl_regex_rep, 3, 0)
        self.txt_regex_rep = QLineEdit()
        fl.addWidget(self.txt_regex_rep, 3, 1)

        self.chk_auto_url = QCheckBox(tr("chk_auto_url", self.config.language))
        fl.addWidget(self.chk_auto_url, 4, 0, 1, 2)

        self.chk_copy_always = QCheckBox(tr("chk_copy_always", self.config.language))
        fl.addWidget(self.chk_copy_always, 5, 0, 1, 2)

        layout.addWidget(self.grp_filt)

        scroll.setWidget(content)
        tab_layout.addWidget(scroll, stretch=1)

        # 6. Requirement 8: Sticky Settings Footer Bar (Fixed outside scroll area)
        sticky_footer = QFrame()
        sticky_footer.setObjectName("StickyFooter")
        foot_layout = QHBoxLayout(sticky_footer)
        foot_layout.setContentsMargins(12, 8, 12, 8)

        self.lbl_save_status = QLabel(tr("lbl_all_saved", self.config.language))
        self.lbl_save_status.setObjectName("AllSavedLabel")
        foot_layout.addWidget(self.lbl_save_status)

        foot_layout.addStretch()

        self.btn_reset_defaults = QPushButton(tr("btn_reset_defaults", self.config.language))
        self.btn_reset_defaults.setObjectName("BtnResetDefaults")
        self.btn_reset_defaults.clicked.connect(self._reset_settings_to_defaults)
        foot_layout.addWidget(self.btn_reset_defaults)

        self.btn_save_settings = QPushButton(tr("btn_save_settings", self.config.language))
        self.btn_save_settings.setObjectName("BtnSaveSettings")
        self.btn_save_settings.clicked.connect(self._save_settings_from_ui)
        foot_layout.addWidget(self.btn_save_settings)

        tab_layout.addWidget(sticky_footer)

        # Connect change listeners for dirty tracking
        self._connect_settings_dirty_listeners()

        # Populate form with current values
        self._load_settings_into_form(self.config)

        self.tabs.addTab(tab, tr("tab_settings", self.config.language))

    def _connect_settings_dirty_listeners(self) -> None:
        def _mark_dirty():
            if not self._is_loading_settings_form:
                self.has_unsaved_changes = True
                self.lbl_save_status.setText(tr("lbl_unsaved_changes", self.config.language))
                self.lbl_save_status.setObjectName("UnsavedChangesLabel")
                self.lbl_save_status.setStyle(self.lbl_save_status.style())

        self.combo_mode.currentIndexChanged.connect(_mark_dirty)
        self.chk_auto_start_srv.stateChanged.connect(_mark_dirty)
        self.chk_start_windows.stateChanged.connect(_mark_dirty)
        self.chk_min_tray.stateChanged.connect(_mark_dirty)
        self.chk_beep.stateChanged.connect(_mark_dirty)
        self.txt_host.textChanged.connect(_mark_dirty)
        self.spin_port.valueChanged.connect(_mark_dirty)
        self.chk_dedup.stateChanged.connect(_mark_dirty)
        self.spin_dedup_win.valueChanged.connect(_mark_dirty)
        self.combo_out_mode.currentIndexChanged.connect(_mark_dirty)
        self.spin_inter_key.valueChanged.connect(_mark_dirty)
        self.spin_pre_delay.valueChanged.connect(_mark_dirty)
        self.chk_restore_clip.stateChanged.connect(_mark_dirty)
        self.chk_trim_space.stateChanged.connect(_mark_dirty)
        self.combo_nl.currentIndexChanged.connect(_mark_dirty)
        self.txt_regex_pat.textChanged.connect(_mark_dirty)
        self.txt_regex_rep.textChanged.connect(_mark_dirty)
        self.chk_auto_url.stateChanged.connect(_mark_dirty)
        self.chk_copy_always.stateChanged.connect(_mark_dirty)

    def _load_settings_into_form(self, cfg: AppConfig) -> None:
        self._is_loading_settings_form = True
        try:
            idx_m = self.combo_mode.findData(cfg.mode)
            if idx_m >= 0:
                self.combo_mode.setCurrentIndex(idx_m)

            self.chk_auto_start_srv.setChecked(cfg.auto_start)
            self.chk_start_windows.setChecked(cfg.start_with_windows)
            self.chk_min_tray.setChecked(cfg.minimize_to_tray)
            self.chk_beep.setChecked(cfg.audio_feedback)

            self.txt_host.setText(cfg.http_host)
            self.spin_port.setValue(cfg.http_port)

            self.chk_dedup.setChecked(cfg.deduplication_enabled)
            self.spin_dedup_win.setValue(cfg.deduplication_window_ms)

            idx_o = self.combo_out_mode.findData(cfg.output_mode)
            if idx_o >= 0:
                self.combo_out_mode.setCurrentIndex(idx_o)

            self.spin_inter_key.setValue(cfg.inter_key_delay_ms)
            self.spin_pre_delay.setValue(cfg.pre_typing_delay_ms)
            self.chk_restore_clip.setChecked(cfg.restore_clipboard)

            self.chk_trim_space.setChecked(cfg.trim_whitespace)
            idx_nl = self.combo_nl.findData(cfg.replace_newlines)
            if idx_nl >= 0:
                self.combo_nl.setCurrentIndex(idx_nl)

            self.txt_regex_pat.setText(cfg.regex_pattern)
            self.txt_regex_rep.setText(cfg.regex_replacement)
            self.chk_auto_url.setChecked(cfg.auto_open_urls)
            self.chk_copy_always.setChecked(cfg.copy_to_clipboard)

            self.has_unsaved_changes = False
            self.lbl_save_status.setText(tr("lbl_all_saved", self.config.language))
            self.lbl_save_status.setObjectName("AllSavedLabel")
            self.lbl_save_status.setStyle(self.lbl_save_status.style())
        finally:
            self._is_loading_settings_form = False

    def _save_settings_from_ui(self) -> None:
        """Requirement 8: Deferred Save execution on button click."""
        old_mode = self.config.mode
        old_port = self.config.http_port
        old_host = self.config.http_host

        new_mode = self.combo_mode.currentData()
        new_port = self.spin_port.value()
        new_host = self.txt_host.text().strip() or "0.0.0.0"

        if self.chk_start_windows.isChecked() != self.config.start_with_windows:
            set_autostart_registry(self.chk_start_windows.isChecked())

        self.config = self.config_manager.save(
            mode=new_mode,
            http_host=new_host,
            http_port=new_port,
            auto_start=self.chk_auto_start_srv.isChecked(),
            start_with_windows=self.chk_start_windows.isChecked(),
            minimize_to_tray=self.chk_min_tray.isChecked(),
            audio_feedback=self.chk_beep.isChecked(),
            deduplication_enabled=self.chk_dedup.isChecked(),
            deduplication_window_ms=self.spin_dedup_win.value(),
            output_mode=self.combo_out_mode.currentData(),
            inter_key_delay_ms=self.spin_inter_key.value(),
            pre_typing_delay_ms=self.spin_pre_delay.value(),
            restore_clipboard=self.chk_restore_clip.isChecked(),
            trim_whitespace=self.chk_trim_space.isChecked(),
            replace_newlines=self.combo_nl.currentData(),
            regex_pattern=self.txt_regex_pat.text(),
            regex_replacement=self.txt_regex_rep.text(),
            auto_open_urls=self.chk_auto_url.isChecked(),
            copy_to_clipboard=self.chk_copy_always.isChecked(),
        )

        self.dedup.update_settings(
            window_ms=self.config.deduplication_window_ms,
            enabled=self.config.deduplication_enabled,
        )

        # Restart servers if mode/port/host changed while active
        if self.is_server_active and (new_mode != old_mode or new_port != old_port or new_host != old_host):
            self.stop_server()
            self.start_server()

        self._refresh_all_qrs()
        self._update_status_card_styles()
        self.tray.update_state(self.is_server_active, self.config.mode, self.config.language)

        self.has_unsaved_changes = False
        self.lbl_save_status.setText(tr("lbl_all_saved", self.config.language))
        self.lbl_save_status.setObjectName("AllSavedLabel")
        self.lbl_save_status.setStyle(self.lbl_save_status.style())

        QMessageBox.information(
            self,
            tr("app_title", self.config.language),
            tr("settings_saved", self.config.language),
        )

    def _reset_settings_to_defaults(self) -> None:
        """Requirement 8: Reset to factory defaults button with confirmation."""
        res = QMessageBox.question(
            self,
            tr("app_title", self.config.language),
            tr("confirm_reset_defaults", self.config.language),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        defaults = AppConfig()
        self._load_settings_into_form(defaults)
        self._save_settings_from_ui()

        QMessageBox.information(
            self,
            tr("app_title", self.config.language),
            tr("settings_reset", self.config.language),
        )

    # ==========================================================================
    # SERVER LIFECYCLE & STRICT OPERATION MODE ISOLATION (Fix 1)
    # ==========================================================================
    def toggle_server(self) -> None:
        if self.is_server_active:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self) -> None:
        if self.is_server_active:
            return

        mode = self.config.mode.strip().lower()
        bt_ok = False
        http_ok = False

        # Requirement 1 & 2: Strict Operation Mode Isolation & Radio Control
        # If mode is http only, Bluetooth MUST NOT be started and radio is turned OFF programmatically
        if mode in ("both", "bluetooth"):
            threading.Thread(target=self.bt_radio.restore_radio_state, daemon=True).start()
            if not self.bt_server or not self.bt_server.is_running:
                self.bt_server = BluetoothServerController(
                    service_uuid=self.config.service_uuid,
                    service_name=self.config.service_name,
                    on_scan=self.enqueue_scan,
                    on_status_change=lambda s: self.signals.bt_status_changed.emit(s),
                    mode_checker=lambda: self.config.mode,
                )
                bt_ok, bt_msg = self.bt_server.start()
            else:
                bt_ok = True
        else:
            if self.bt_server:
                self.bt_server.stop()
                self.bt_server = None
            threading.Thread(target=self.bt_radio.ensure_radio_off_for_http_mode, daemon=True).start()

        # If mode is bluetooth only, HTTP server MUST NOT be started!
        if mode in ("both", "http"):
            if not self.http_server or not self.http_server.is_running:
                self.http_server = HttpServerController(
                    host=self.config.http_host,
                    port=self.config.http_port,
                    on_scan=self.enqueue_scan,
                    mode_checker=lambda: self.config.mode,
                )
                http_ok, http_msg = self.http_server.start()
                if not http_ok:
                    QMessageBox.warning(self, "HTTP Server", http_msg)
            else:
                http_ok = True
        else:
            if self.http_server:
                self.http_server.stop()
                self.http_server = None

        # Start Tier 1 Low-Level Keyboard Hook for Bluetooth HID burst interception
        self.keyboard_hook.start()

        self.is_server_active = bt_ok or http_ok
        self._update_power_button()
        self._update_status_card_styles()
        self.tray.update_state(self.is_server_active, self.config.mode, self.config.language)

    def stop_server(self) -> None:
        if self.http_server:
            self.http_server.stop()
            self.http_server = None

        if self.bt_server:
            self.bt_server.stop()
            self.bt_server = None

        # Restore Bluetooth radio if we modified it
        threading.Thread(target=self.bt_radio.restore_radio_state, daemon=True).start()
        self.keyboard_hook.stop()

        self.is_server_active = False
        self._update_power_button()
        self._update_status_card_styles()
        self.tray.update_state(False, self.config.mode, self.config.language)

    def set_mode(self, mode: str) -> None:
        """Unified mode setter used by both UI and System Tray menu (Two-Way Sync)."""
        mode = mode.lower()
        if mode not in ("both", "http", "bluetooth"):
            return

        self.config = self.config_manager.save(mode=mode)

        # Update Settings dropdown
        idx = self.combo_mode.findData(mode)
        if idx >= 0:
            self.combo_mode.blockSignals(True)
            self.combo_mode.setCurrentIndex(idx)
            self.combo_mode.blockSignals(False)

        # Immediate isolation enforcement
        if self.is_server_active:
            if mode == "http":
                if self.bt_server:
                    self.bt_server.stop()
                    self.bt_server = None
                threading.Thread(target=self.bt_radio.ensure_radio_off_for_http_mode, daemon=True).start()
            elif mode == "bluetooth":
                if self.http_server:
                    self.http_server.stop()
                    self.http_server = None
                threading.Thread(target=self.bt_radio.restore_radio_state, daemon=True).start()
            elif mode == "both":
                threading.Thread(target=self.bt_radio.restore_radio_state, daemon=True).start()
                if not self.bt_server:
                    self.start_server()
                if not self.http_server:
                    self.start_server()
        else:
            if mode == "http" and self.bt_server:
                self.bt_server.stop()
                self.bt_server = None
            elif mode == "bluetooth" and self.http_server:
                self.http_server.stop()
                self.http_server = None

        self._update_status_card_styles()
        self.tray.update_state(self.is_server_active, self.config.mode, self.config.language)

    def _on_hook_barcode_captured(self, barcode: str, source: str = "Bluetooth") -> None:
        """Receive barcode string captured from OS-level Bluetooth HID by WH_KEYBOARD_LL hook."""
        payload = ScanPayload(
            content=barcode,
            format="BLUETOOTH_HID",
            source=source,
            client_address="Bluetooth-HID",
        )
        self.enqueue_scan(payload)

    def ProcessIncomingBarcode(self, payload: ScanPayload | str, source: str = "Bluetooth") -> None:
        """Central ingestion entry point for external Bluetooth HID or HTTP scans."""
        if isinstance(payload, str):
            p = ScanPayload(content=payload, format="BLUETOOTH_HID", source=source)
        else:
            p = payload
        self.enqueue_scan(p)

    def _update_power_button(self) -> None:
        if self.is_server_active:
            self.btn_master_power.setObjectName("MasterPowerBtnRunning")
            self.btn_master_power.setText(f"● {tr('btn_stop', self.config.language)}")
        else:
            self.btn_master_power.setObjectName("MasterPowerBtnStopped")
            self.btn_master_power.setText(f"▶ {tr('btn_start', self.config.language)}")
        self.btn_master_power.setStyle(self.btn_master_power.style())

    def _update_status_card_styles(self) -> None:
        """Requirement 6 & 9: Dynamically update colors and text of compact top status bar pills."""
        mode = self.config.mode.strip().lower()

        # 1. Master Server Status Pill
        if self.is_server_active:
            self.pill_server.setProperty("class", "StatusPillActive")
            self.pill_server.setText(tr("status_running", self.config.language))
        else:
            self.pill_server.setProperty("class", "StatusPillStopped")
            self.pill_server.setText(tr("status_stopped", self.config.language))

        # 2. Bluetooth Status Pill
        if mode == "http":
            self.pill_bt.setProperty("class", "StatusPillInactive")
            self.pill_bt.setText(tr("status_disabled", self.config.language))
        elif self.is_server_active and self.bt_server and self.bt_server.is_running:
            self.pill_bt.setProperty("class", "StatusPillActive")
            self.pill_bt.setText(self.bt_server.status)
        else:
            self.pill_bt.setProperty("class", "StatusPillInactive")
            self.pill_bt.setText(tr("status_standby", self.config.language))

        # 3. HTTP Server Status Pill
        if mode == "bluetooth":
            self.pill_http.setProperty("class", "StatusPillInactive")
            self.pill_http.setText(tr("status_disabled", self.config.language))
        elif self.is_server_active and self.http_server and self.http_server.is_running:
            self.pill_http.setProperty("class", "StatusPillActive")
            self.pill_http.setText(f":{self.config.http_port} (Active)")
        elif self.is_server_active and self.http_server and self.http_server.last_error:
            self.pill_http.setProperty("class", "StatusPillStopped")
            self.pill_http.setText(tr("status_error", self.config.language))
        else:
            self.pill_http.setProperty("class", "StatusPillInactive")
            self.pill_http.setText(tr("status_standby", self.config.language))

        # 4. Mode Pill
        mode_label = {
            "both": tr("opt_mode_both", self.config.language),
            "http": tr("opt_mode_http", self.config.language),
            "bluetooth": tr("opt_mode_bt", self.config.language),
        }.get(mode, mode)
        self.pill_mode.setText(mode_label)
        self.pill_mode.setProperty("class", "StatusPillActive" if self.is_server_active else "StatusPillInactive")

        # Force style re-polish for immediate visual update
        for pill in [self.pill_server, self.pill_bt, self.pill_http, self.pill_mode]:
            pill.style().unpolish(pill)
            pill.style().polish(pill)
            pill.update()

    @Slot(str)
    def _on_bt_status_changed_ui(self, status: str) -> None:
        self.pill_bt.setText(status)
        if "Connected" in status or "Listening" in status:
            self.pill_bt.setProperty("class", "StatusPillActive")
        elif "Off" in status:
            self.pill_bt.setProperty("class", "StatusPillAmber")
        else:
            self.pill_bt.setProperty("class", "StatusPillInactive")
        self.pill_bt.style().unpolish(self.pill_bt)
        self.pill_bt.style().polish(self.pill_bt)

    # ==========================================================================
    # CENTRAL PIPELINE: DEDUPLICATION, GUARDS, TRANSFORMS & OUTPUT ROUTING
    # ==========================================================================
    def _start_worker_thread(self) -> None:
        def _worker_loop():
            while not self._worker_stop.is_set():
                try:
                    payload = self.scan_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                self._process_scan_payload(payload)
                self.scan_queue.task_done()

        self._worker_thread = threading.Thread(
            target=_worker_loop, name="BinaryReceptor-Worker", daemon=True
        )
        self._worker_thread.start()

    def enqueue_scan(self, payload: ScanPayload) -> None:
        """Thread-safe enqueueing from HTTP or Bluetooth transports with strict mode gating."""
        active_mode = (self.config.mode or "both").strip().lower()
        src_l = (payload.source or "").strip().lower()
        if active_mode == "http" and src_l == "bluetooth":
            return
        if active_mode == "bluetooth" and src_l == "http":
            return
        self.scan_queue.put(payload)

    def _dispatch_output(self, text: str, source: str) -> str:
        """Unified output method reading live output_mode at the moment of the scan.

        Guarantees exact behavior across both Bluetooth and HTTP:
          - copy_only: Copies to clipboard ONLY. NEVER calls SendInput or types characters/prefix/suffix!
          - clipboard_paste: Copies to clipboard and simulates Ctrl+V.
          - simulated_typing (type): Injects keystrokes via SendInput Unicode.
          - log_only: Only records scan in live table without touching clipboard or keyboard.
        """
        out_mode = (self.config.output_mode or "type").strip().lower()

        # 1. Copy to clipboard only (Zero typing, zero SendInput)
        if out_mode in ("copy_only", "copy", "clipboard_only"):
            win32_set_clipboard_text(text)
            try:
                QApplication.clipboard().setText(text)
            except Exception:
                pass
            return tr("status_copied", self.config.language)

        # 2. History / Log only
        if out_mode in ("log_only", "log", "none", "disabled"):
            return tr("status_logged", self.config.language)

        # 3. Clipboard Paste (Ctrl+V)
        if out_mode in ("clipboard_paste", "paste"):
            self.injector.inject_scan(
                content=text,
                prefix_template=self.config.prefix,
                suffix_template=self.config.suffix,
                output_mode="paste",
                inter_key_delay_ms=self.config.inter_key_delay_ms,
                pre_typing_delay_ms=self.config.pre_typing_delay_ms,
                restore_clipboard=self.config.restore_clipboard,
                copy_to_clipboard=self.config.copy_to_clipboard,
            )
            return tr("status_pasted", self.config.language)

        # 4. Simulated Typing (SendInput Unicode)
        self.injector.inject_scan(
            content=text,
            prefix_template=self.config.prefix,
            suffix_template=self.config.suffix,
            output_mode="type",
            inter_key_delay_ms=self.config.inter_key_delay_ms,
            pre_typing_delay_ms=self.config.pre_typing_delay_ms,
            copy_to_clipboard=self.config.copy_to_clipboard,
        )
        return tr("status_typed", self.config.language)

    def _process_scan_payload(self, payload: ScanPayload) -> None:
        """Central Unified Scan Pipeline conforming strictly to Rules 1, 2, 3."""
        # ----------------------------------------------------------------------
        # 1. Strict Mode Isolation Guard (Specification 1)
        # ----------------------------------------------------------------------
        active_mode = (self.config.mode or "both").strip().lower()
        src_l = (payload.source or "").strip().lower()

        if active_mode == "http" and src_l == "bluetooth":
            return
        if active_mode == "bluetooth" and src_l == "http":
            return

        raw_content = payload.content or ""

        # ----------------------------------------------------------------------
        # 2. Canonical Normalization & Time-Interval Cooldown Gate (Specification 2)
        # ----------------------------------------------------------------------
        canonical_content = ScanDeduplicator.normalize_content(raw_content)
        if not canonical_content:
            return

        with self._scan_lock:
            elapsed_ms = (time.monotonic() - self._last_scan_timestamp) * 1000.0
            cooldown_ms = float(self.config.deduplication_window_ms)
            dedup_enabled = self.config.deduplication_enabled
            mode = (self.config.mode or "both").strip().lower()

            is_dup, dup_msg = self.dedup.check_and_record(
                canonical_content,
                source=payload.source,
                scan_id=payload.scan_id,
            )

            # In Hybrid (both) mode (or whenever Duplicate Protection is enabled):
            # if within cooldown or duplicate scanId, suppress immediately
            if (dedup_enabled or mode == "both") and is_dup:
                self.cnt_dedup += 1
                self.signals.stats_updated.emit()
                self.signals.scan_received.emit(
                    payload,
                    tr("status_dedup", self.config.language),
                    dup_msg,
                )
                return

            # Otherwise, update tracker before releasing lock
            self._last_scan_timestamp = time.monotonic()
            self._last_scan_text = canonical_content
            self._last_scan_source = payload.source

        # ----------------------------------------------------------------------
        # 3. Format / Symbology Filter
        # ----------------------------------------------------------------------
        if self.config.allowed_formats.lower() != "all" and payload.format:
            allowed = [f.strip().lower() for f in self.config.allowed_formats.split(",")]
            if payload.format.lower() not in allowed:
                self.signals.scan_received.emit(
                    payload,
                    tr("status_filtered", self.config.language),
                    "Format filtered",
                )
                return

        # ----------------------------------------------------------------------
        # 4. Content Transformations (Trim, Newline replace, Regex)
        # ----------------------------------------------------------------------
        final_text = canonical_content

        if self.config.trim_whitespace:
            final_text = final_text.strip()

        if self.config.replace_newlines == "tab":
            final_text = final_text.replace("\r\n", "\t").replace("\n", "\t")
        elif self.config.replace_newlines == "space":
            final_text = final_text.replace("\r\n", " ").replace("\n", " ")

        if self.config.regex_pattern:
            try:
                final_text = re.sub(self.config.regex_pattern, self.config.regex_replacement, final_text)
            except re.error:
                pass

        payload.content = final_text

        # ----------------------------------------------------------------------
        # 5. Output Mode Routing (Specification 3)
        # ----------------------------------------------------------------------
        try:
            status_text = self._dispatch_output(final_text, payload.source)
        except Exception as e:
            status_text = f"Error: {e}"

        # ----------------------------------------------------------------------
        # 7. Audio Feedback Chime (Requirement 2)
        # ----------------------------------------------------------------------
        if self.config.audio_feedback:
            play_scanner_beep()

        # ----------------------------------------------------------------------
        # 8. Auto-Open URLs
        # ----------------------------------------------------------------------
        if self.config.auto_open_urls and (final_text.startswith("http://") or final_text.startswith("https://")):
            try:
                webbrowser.open(final_text)
            except Exception:
                pass

        # ----------------------------------------------------------------------
        # 9. Update Metrics & Emit UI Signals
        # ----------------------------------------------------------------------
        self.cnt_total += 1
        if payload.source == "Bluetooth":
            self.cnt_bt += 1
        else:
            self.cnt_http += 1

        self.signals.stats_updated.emit()
        self.signals.scan_received.emit(payload, status_text, "Processed successfully")

    @Slot(object, str, str)
    def _on_scan_received_ui(self, payload: ScanPayload, status_text: str, detail: str) -> None:
        """Insert scan event into history table on UI thread."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.table_history.insertRow(0)
        self.table_history.setItem(0, 0, QTableWidgetItem(now_str))
        self.table_history.setItem(0, 1, QTableWidgetItem(payload.source))
        self.table_history.setItem(0, 2, QTableWidgetItem(payload.format or "Auto"))
        self.table_history.setItem(0, 3, QTableWidgetItem(payload.content))
        self.table_history.setItem(0, 4, QTableWidgetItem(status_text))

        if self.config.tray_notifications and not self.isVisible():
            title = tr("toast_scan_title", self.config.language, source=payload.source)
            self.tray.show_notification(title, f"{payload.content[:60]} ({status_text})")

    @Slot()
    def _update_kpi_cards(self) -> None:
        self.lbl_kpi_total.setText(str(self.cnt_total))
        self.lbl_kpi_bt.setText(str(self.cnt_bt))
        self.lbl_kpi_http.setText(str(self.cnt_http))
        self.lbl_kpi_dedup.setText(str(self.cnt_dedup))

    # ==========================================================================
    # HISTORY TABLE ACTIONS
    # ==========================================================================
    def _retype_selected_scan(self) -> None:
        row = self.table_history.currentRow()
        if row >= 0:
            content_item = self.table_history.item(row, 3)
            if content_item:
                content = content_item.text()
                threading.Thread(
                    target=lambda: self.injector.inject_scan(
                        content=content,
                        prefix_template=self.config.prefix,
                        suffix_template=self.config.suffix,
                        output_mode=self.config.output_mode,
                    ),
                    daemon=True,
                ).start()

    def _copy_selected_scan(self) -> None:
        row = self.table_history.currentRow()
        if row >= 0:
            item = self.table_history.item(row, 3)
            if item:
                QApplication.clipboard().setText(item.text())

    def _clear_history_log(self) -> None:
        res = QMessageBox.question(
            self,
            tr("app_title", self.config.language),
            tr("confirm_clear_log", self.config.language),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            self.table_history.setRowCount(0)
            self.cnt_total = 0
            self.cnt_bt = 0
            self.cnt_http = 0
            self.cnt_dedup = 0
            self.dedup.reset_stats()
            self._update_kpi_cards()

    def _export_csv(self) -> None:
        row_count = self.table_history.rowCount()
        if row_count == 0:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("btn_export_csv", self.config.language),
            f"BinaryReceptor_scans_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Channel", "Format", "Content", "Status"])
                for r in range(row_count):
                    writer.writerow([
                        self.table_history.item(r, c).text() if self.table_history.item(r, c) else ""
                        for c in range(5)
                    ])
            QMessageBox.information(
                self,
                tr("app_title", self.config.language),
                tr("export_success", self.config.language, count=row_count, path=file_path),
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    # ==========================================================================
    # LANGUAGE & THEME SWITCHING (Requirement 12)
    # ==========================================================================
    def toggle_language(self) -> None:
        new_lang = "fa" if self.config.language == "en" else "en"
        self.apply_language(new_lang)
        self.config_manager.save(language=new_lang)

    def apply_language(self, lang: str) -> None:
        self.config.language = lang

        # Native Qt Right-to-Left vs Left-to-Right layout direction
        if lang == "fa":
            QApplication.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            QApplication.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        # Header
        self.lbl_app_title.setText(tr("app_title", lang))
        self.lbl_app_subtitle.setText(tr("app_subtitle", lang))
        self.btn_lang_toggle.setText(tr("lang_switch", lang))
        self._update_power_button()

        # Compact Top Status Strip
        self.lbl_strip_server.setText(tr("strip_server", lang))
        self.lbl_strip_mode.setText(tr("strip_mode", lang))
        self.lbl_strip_bt.setText(tr("strip_bt", lang))
        self.lbl_strip_http.setText(tr("strip_http", lang))
        self.lbl_kpi_total_desc.setText(tr("kpi_total_scans", lang))
        self.lbl_kpi_bt_desc.setText(tr("kpi_bt_scans", lang))
        self.lbl_kpi_http_desc.setText(tr("kpi_http_scans", lang))
        self.lbl_kpi_dedup_desc.setText(tr("kpi_dedup_blocked", lang))
        self._update_status_card_styles()

        # Tab titles
        self.tabs.setTabText(0, tr("tab_dashboard", lang))
        self.tabs.setTabText(1, tr("tab_wedge", lang))
        self.tabs.setTabText(2, tr("tab_connection", lang))
        self.tabs.setTabText(3, tr("tab_settings", lang))

        # Dashboard table headers
        self.table_history.setHorizontalHeaderLabels([
            tr("col_time", lang),
            tr("col_channel", lang),
            tr("col_format", lang),
            tr("col_content", lang),
            tr("col_status", lang),
        ])
        self.btn_retype.setText(tr("btn_retype", lang))
        self.btn_copy_content.setText(tr("btn_copy", lang))
        self.btn_export_csv.setText(tr("btn_export_csv", lang))
        self.btn_clear_log.setText(tr("btn_clear_log", lang))

        # Wedge tab
        self.lbl_wedge_title.setText(tr("wedge_title", lang))
        self.lbl_wedge_desc.setText(tr("wedge_desc", lang))
        self.grp_prefix.setTitle(tr("lbl_prefix", lang))
        self.grp_suffix.setTitle(tr("lbl_suffix", lang))
        self.grp_preview.setTitle(tr("lbl_preview", lang))
        self.btn_clear_p.setText(tr("btn_clear_field", lang))
        self.btn_clear_s.setText(tr("btn_clear_field", lang))

        # Connection tab
        self.lbl_lan_ip_header.setText(tr("lbl_lan_ip", lang))
        self.btn_copy_active_url.setText(tr("btn_copy_url", lang))
        if hasattr(self, "btn_copy_url"):
            self.btn_copy_url.setText(tr("btn_copy_url", lang))
        self.qr_subtabs.setTabText(0, tr("subtab_qr_url", lang))
        self.qr_subtabs.setTabText(1, tr("subtab_qr_encode", lang))
        self.lbl_req_type_hdr.setText(tr("lbl_binaryeye_req_type", lang))
        self.lbl_url_field_hdr.setText(tr("lbl_http_url", lang))
        self.lbl_desc_qr_encode.setText(tr("desc_qr_encode", lang))
        self.lbl_encode_txt_hdr.setText(tr("lbl_encode_text", lang))
        self.lbl_encode_fmt_hdr.setText(tr("lbl_encode_format", lang))

        # Settings tab
        self.grp_gen.setTitle(tr("sec_general", lang))
        self.lbl_mode_setting.setText(tr("lbl_mode", lang))
        self.chk_auto_start_srv.setText(tr("chk_auto_start", lang))
        self.chk_start_windows.setText(tr("chk_start_windows", lang))
        self.chk_min_tray.setText(tr("chk_min_tray", lang))
        self.chk_beep.setText(tr("chk_beep", lang))
        self.btn_test_sound.setText(tr("btn_test_sound", lang))

        self.grp_net.setTitle(tr("sec_network", lang))
        self.lbl_host_setting.setText(tr("lbl_host", lang))
        self.lbl_port_setting.setText(tr("lbl_port", lang))

        self.grp_dedup.setTitle(tr("sec_dedup", lang))
        self.chk_dedup.setText(tr("chk_dedup_enabled", lang))
        self.lbl_dedup_win.setText(tr("lbl_dedup_interval", lang))
        self.lbl_dedup_presets.setText(tr("lbl_dedup_presets", lang))
        self.lbl_dedup_hint.setText(tr("desc_dedup_cooldown", lang))

        self.grp_wedge.setTitle(tr("sec_wedge", lang))
        self.lbl_out_mode.setText(tr("lbl_out_mode", lang))
        self.lbl_inter_key.setText(tr("lbl_inter_key", lang))
        self.lbl_pre_delay.setText(tr("lbl_pre_delay", lang))
        self.chk_restore_clip.setText(tr("chk_restore_clip", lang))

        self.grp_filt.setTitle(tr("sec_filters", lang))
        self.chk_trim_space.setText(tr("chk_trim_space", lang))
        self.lbl_replace_nl.setText(tr("lbl_replace_newlines", lang))
        self.lbl_regex_pat.setText(tr("lbl_regex_pat", lang))
        self.lbl_regex_rep.setText(tr("lbl_regex_rep", lang))
        self.chk_auto_url.setText(tr("chk_auto_url", lang))
        self.chk_copy_always.setText(tr("chk_copy_always", lang))

        # Sticky Footer
        self.btn_save_settings.setText(tr("btn_save_settings", lang))
        self.btn_reset_defaults.setText(tr("btn_reset_defaults", lang))
        self.lbl_save_status.setText(
            tr("lbl_unsaved_changes" if self.has_unsaved_changes else "lbl_all_saved", lang)
        )

        # Retranslate All Dropdown Lists & Buttons (Requirement 5)
        self._retranslate_all_dropdowns(lang)

        # Refresh QR codes & instructions for new language
        self._refresh_all_qrs()

        # Update Tray State
        self.tray.update_state(self.is_server_active, self.config.mode, lang)

    def _retranslate_all_dropdowns(self, lang: str) -> None:
        """Requirement 5: 100% complete Persian and English localization across all dropdowns and chip buttons."""
        # 1. Operation Mode Dropdown
        cur_mode = self.combo_mode.currentData() or self.config.mode
        self.combo_mode.blockSignals(True)
        self.combo_mode.clear()
        self.combo_mode.addItem(tr("opt_mode_both", lang), "both")
        self.combo_mode.addItem(tr("opt_mode_http", lang), "http")
        self.combo_mode.addItem(tr("opt_mode_bt", lang), "bluetooth")
        idx_m = self.combo_mode.findData(cur_mode)
        if idx_m >= 0:
            self.combo_mode.setCurrentIndex(idx_m)
        self.combo_mode.blockSignals(False)

        # 2. Output Mode Dropdown
        cur_out = self.combo_out_mode.currentData() or self.config.output_mode
        self.combo_out_mode.blockSignals(True)
        self.combo_out_mode.clear()
        self.combo_out_mode.addItem(tr("opt_out_type", lang), "type")
        self.combo_out_mode.addItem(tr("opt_out_paste", lang), "paste")
        self.combo_out_mode.addItem(tr("opt_out_copy", lang), "copy_only")
        self.combo_out_mode.addItem(tr("opt_out_log", lang), "log_only")
        idx_o = self.combo_out_mode.findData(cur_out)
        if idx_o >= 0:
            self.combo_out_mode.setCurrentIndex(idx_o)
        self.combo_out_mode.blockSignals(False)

        # 3. Newline Replace Dropdown
        cur_nl = self.combo_nl.currentData() or self.config.replace_newlines
        self.combo_nl.blockSignals(True)
        self.combo_nl.clear()
        self.combo_nl.addItem(tr("opt_nl_none", lang), "none")
        self.combo_nl.addItem(tr("opt_nl_tab", lang), "tab")
        self.combo_nl.addItem(tr("opt_nl_space", lang), "space")
        idx_nl = self.combo_nl.findData(cur_nl)
        if idx_nl >= 0:
            self.combo_nl.setCurrentIndex(idx_nl)
        self.combo_nl.blockSignals(False)

        # 4. BinaryEye Request Type Dropdown
        if hasattr(self, "combo_req_type"):
            cur_req = self.combo_req_type.currentData() or "post_json"
            self.combo_req_type.blockSignals(True)
            self.combo_req_type.clear()
            self.combo_req_type.addItem(tr("opt_req_post_json", lang), "post_json")
            self.combo_req_type.addItem(tr("opt_req_post_form", lang), "post_form")
            self.combo_req_type.addItem(tr("opt_req_get_query", lang), "get_query")
            self.combo_req_type.addItem(tr("opt_req_get_append", lang), "get_append")
            self.combo_req_type.addItem(tr("opt_req_get_template", lang), "get_template")
            idx_req = self.combo_req_type.findData(cur_req)
            if idx_req >= 0:
                self.combo_req_type.setCurrentIndex(idx_req)
            self.combo_req_type.blockSignals(False)

        # 5. Prefix & Suffix Presets
        if hasattr(self, "combo_prefix_preset"):
            self._populate_token_presets(self.combo_prefix_preset)
        if hasattr(self, "combo_suffix_preset"):
            self._populate_token_presets(self.combo_suffix_preset)

        # 6. Prefix & Suffix Chip Buttons
        if hasattr(self, "prefix_chip_buttons"):
            for btn, key in self.prefix_chip_buttons:
                btn.setText(tr(key, lang))
        if hasattr(self, "suffix_chip_buttons"):
            for btn, key in self.suffix_chip_buttons:
                btn.setText(tr(key, lang))

    def toggle_theme(self) -> None:
        new_theme = "light" if self.config.theme == "dark" else "dark"
        self.apply_theme(new_theme)
        self.config_manager.save(theme=new_theme)

    def apply_theme(self, theme: str) -> None:
        self.config.theme = theme
        if theme == "light":
            QApplication.instance().setStyleSheet(LIGHT_STYLESHEET)
            self.btn_theme_toggle.setText("🌙 Dark")
        else:
            QApplication.instance().setStyleSheet(DARK_STYLESHEET)
            self.btn_theme_toggle.setText("☀️ Light")
        self._update_status_card_styles()

    # ==========================================================================
    # TRAY & WINDOW MANAGEMENT
    # ==========================================================================
    def show_and_activate(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _show_qr_tab(self) -> None:
        self.show_and_activate()
        self.tabs.setCurrentIndex(2)

    @Slot(object)
    def _on_config_reloaded_from_disk(self, new_config: AppConfig) -> None:
        """Called when settings.ini is modified externally on disk."""
        old_mode = self.config.mode
        old_port = self.config.http_port
        old_host = self.config.http_host
        self.config = new_config

        self.txt_prefix.setText(new_config.prefix)
        self.txt_suffix.setText(new_config.suffix)
        self._load_settings_into_form(new_config)

        self.dedup.update_settings(
            window_ms=new_config.deduplication_window_ms,
            enabled=new_config.deduplication_enabled,
        )

        if self.is_server_active and (
            new_config.mode != old_mode
            or new_config.http_port != old_port
            or new_config.http_host != old_host
        ):
            self.stop_server()
            self.start_server()

        self._refresh_all_qrs()
        self._update_status_card_styles()
        self.tray.update_state(self.is_server_active, self.config.mode, self.config.language)

    def closeEvent(self, event) -> None:
        if self.config.minimize_to_tray:
            event.ignore()
            self.hide()
            if self.config.tray_notifications:
                self.tray.show_notification(
                    tr("app_title", self.config.language),
                    "BinaryReceptor is minimized to system tray.",
                    msec=2000,
                )
        else:
            self.exit_application()

    def exit_application(self) -> None:
        self.stop_server()
        try:
            self.keyboard_hook.stop()
            self.bt_radio.restore_radio_state()
        except Exception:
            pass
        self._worker_stop.set()
        self.config_manager.close()
        QApplication.quit()
