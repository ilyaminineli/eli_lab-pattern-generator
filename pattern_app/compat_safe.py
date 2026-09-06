from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import QLabel, QPushButton, QCheckBox, QLineEdit, QPlainTextEdit, QGroupBox, QFormLayout, QTabWidget

from .compat import MainWindow as CompatMainWindow
from .compat import ANCHORS, EN_TRANSLATIONS, JA_TO_EN


class MainWindow(CompatMainWindow):
    """Safe wrapper around the extended window with Qt-compatible menus, shortcuts and localization."""

    def _build_menu(self):
        menu = self.menuBar().addMenu("File")
        actions = [
            ("Generate", self.generate),
            ("Save PNG", self.save_png),
            ("Save SVG", self.save_svg),
            ("Save preset", self.save_preset),
            ("Load preset", self.load_preset),
        ]
        self._file_actions = []
        for text, slot in actions:
            action = QAction(text, self)
            action.triggered.connect(slot)
            menu.addAction(action)
            self._file_actions.append(action)

    def _install_shortcuts(self):
        # The File menu intentionally has no QAction shortcuts. This leaves one
        # unambiguous application-wide binding for each key combination.
        self._shortcut_objects = []
        for key, slot in (
            ("Ctrl+G", self.generate),
            ("Ctrl+Shift+P", self.save_png),
            ("Ctrl+Shift+S", self.save_svg),
            ("F5", self.generate),
        ):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(slot)
            self._shortcut_objects.append(shortcut)

    def _apply_language(self, language):
        language = "ja" if language == "ja" else "en"
        translate = lambda text: EN_TRANSLATIONS.get(text, text) if language == "ja" else JA_TO_EN.get(text, text)

        for widget_type in (QGroupBox, QLabel, QPushButton, QCheckBox, QLineEdit):
            for widget in self.findChildren(widget_type):
                try:
                    widget.setText(translate(widget.text()))
                except Exception:
                    pass

        for widget in self.findChildren(QGroupBox):
            widget.setTitle(translate(widget.title()))

        tabs = self.findChild(QTabWidget)
        if tabs is not None:
            for i in range(tabs.count()):
                tabs.setTabText(i, translate(tabs.tabText(i)))

        for form in self.findChildren(QFormLayout):
            for row in range(form.rowCount()):
                item = form.itemAt(row, QFormLayout.LabelRole)
                label = item.widget() if item is not None else None
                if isinstance(label, QLabel):
                    label.setText(translate(label.text()))

        for action in self.menuBar().actions():
            action.setText(translate(action.text()))
            menu = action.menu()
            if menu is not None:
                menu.setTitle(translate(menu.title()))
                for child in menu.actions():
                    child.setText(translate(child.text()))
                    child_menu = child.menu()
                    if child_menu is not None:
                        child_menu.setTitle(translate(child_menu.title()))
                        for grandchild in child_menu.actions():
                            grandchild.setText(translate(grandchild.text()))

        if hasattr(self, "_settings_menu"):
            self._settings_menu.setTitle(translate("Settings"))

        if hasattr(self, "_lang_en"):
            self._lang_en.setChecked(language == "en")
            self._lang_ja.setChecked(language == "ja")

        if hasattr(self, "text_anchor"):
            current = self.text_anchor.currentData() or "free / current"
            self.text_anchor.blockSignals(True)
            self.text_anchor.clear()
            for key, ja in ANCHORS:
                self.text_anchor.addItem(key if language == "en" else ja, key)
            self.text_anchor.setCurrentIndex(max(0, self.text_anchor.findData(current)))
            self.text_anchor.blockSignals(False)

        self._localized_language = language


__all__ = ["MainWindow"]
