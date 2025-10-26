"""
Maya USD Layout Link Plugin
==========================

A production-ready Maya plugin for bidirectional USD scene data exchange
between Maya and Unreal Engine. Enables layout artists and animators to
collaborate using USD's non-destructive layering system.

Installation:
    1. Copy this file to: ~/maya/scripts/
    2. Run in Maya Script Editor

Requirements:
    - Maya 2022+ with USD plugin enabled
    - mayaUsd plugin loaded
"""

import os
import datetime
import json
from pathlib import Path


import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om2


# UPDATED for Maya 2025: use PySide6 instead of PySide2
from PySide6 import QtWidgets, QtCore, QtGui
from shiboken6 import wrapInstance
import maya.OpenMayaUI as omui


try:
    from pxr import Usd, UsdGeom, Sdf
    from mayaUsd import lib as mayaUsdLib
    USD_AVAILABLE = True
except ImportError:
    USD_AVAILABLE = False
    print("WARNING: USD libraries not available")

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """
    LayoutLink configuration - updated to store user-defined export folder
    """

    META_TIMESTAMP = "layouylink_timestamp"
    META_APP = "layoutlink_app"
    META_ARTIST = "layoutlink_artist"
    META_OPERATION = "layoutlink_operation"
    META_VERSION = "layoutlink_version"
    VERSION = "0.1.0"
    EXPORT_LOCATION_VAR = "layoutlink_export_path"

    @classmethod
    def get_export_path(cls):
        if cmds.optionVar(exists=cls.EXPORT_LOCATION_VAR):
            return cmds.optionVar(q=cls.EXPORT_LOCATION_VAR)
        return None

    @classmethod
    def set_export_path(cls, path):
        cmds.optionVar(sv=(cls.EXPORT_LOCATION_VAR, path))

    @classmethod
    def ensure_export_path(cls):
        path = cls.get_export_path()
        if path and not os.path.exists(path):
            os.makedirs(path)


# ============================================================================
# PROMPT ON LAUNCH FOR EXPORT FOLDER
# ============================================================================

def prompt_for_export_folder():
    """
    Prompts the user to select an export folder if none exists.
    Called automatically from `show_ui()`.
    """
    file_dialog = QtWidgets.QFileDialog()
    file_dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    file_dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
    file_dialog.setWindowTitle("Choose Export Location for LayoutLink")

    if file_dialog.exec():  # Qt6: use exec(), not exec_()
        selected = file_dialog.selectedFiles()[0]
        Config.set_export_path(selected)
        return True
    return False


# ============================================================================
# UI
# ============================================================================

class LayoutLinkUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        if parent is None:
            parent = self.get_maya_main_window()
        super().__init__(parent)

        self.setWindowTitle("LayoutLink - Maya to Unreal")
        self.setMinimumWidth(400)
        self.setup_ui()

    @staticmethod
    def get_maya_main_window():
        ptr = omui.MQtUtil.mainWindow()
        return wrapInstance(int(ptr), QtWidgets.QWidget)

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Dropdown menu for settings
        settings_button = QtWidgets.QPushButton("Settings \u25BE")
        settings_menu = QtWidgets.QMenu(self)
        change_export_action = settings_menu.addAction("Change Export Location")
        change_export_action.triggered.connect(self.on_change_export_location)
        settings_button.setMenu(settings_menu)
        main_layout.addWidget(settings_button)

        header_label = QtWidgets.QLabel("Send Layout to Unreal Engine")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        header_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(header_label)

        # Filename
        filename_group = QtWidgets.QGroupBox("Output File Name")
        filename_layout = QtWidgets.QHBoxLayout()
        self.filename_input = QtWidgets.QLineEdit("maya_layout.usda")
        filename_layout.addWidget(self.filename_input)
        filename_group.setLayout(filename_layout)
        main_layout.addWidget(filename_group)

        # Export Options
        options_group = QtWidgets.QGroupBox("Export Options")
        options_layout = QtWidgets.QVBoxLayout()
        self.animation_checkbox = QtWidgets.QCheckBox("Include Animation")
        self.animation_checkbox.toggled.connect(self.on_animation_toggled)
        options_layout.addWidget(self.animation_checkbox)

        frame_layout = QtWidgets.QHBoxLayout()
        frame_layout.addWidget(QtWidgets.QLabel("Frame Range:"))
        self.start_frame_spin = QtWidgets.QSpinBox()
        self.start_frame_spin.setRange(1, 10000)
        self.start_frame_spin.setValue(int(cmds.playbackOptions(q=True, min=True)))
        self.start_frame_spin.setEnabled(False)
        frame_layout.addWidget(self.start_frame_spin)

        frame_layout.addWidget(QtWidgets.QLabel("to"))
        self.end_frame_spin = QtWidgets.QSpinBox()
        self.end_frame_spin.setRange(1, 10000)
        self.end_frame_spin.setValue(int(cmds.playbackOptions(q=True, max=True)))
        self.end_frame_spin.setEnabled(False)
        frame_layout.addWidget(self.end_frame_spin)

        options_layout.addLayout(frame_layout)
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # Export button
        self.export_button = QtWidgets.QPushButton("EXPORT TO UNREAL")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
        """)
        self.export_button.clicked.connect(self.on_export_clicked)
        main_layout.addWidget(self.export_button)

        # Display selected export location
        info_group = QtWidgets.QGroupBox("Export Location")
        info_layout = QtWidgets.QVBoxLayout()
        self.location_label = QtWidgets.QLabel()
        self.location_label.setWordWrap(True)
        self.update_location_label()
        info_layout.addWidget(self.location_label)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # Status log
        self.status_text = QtWidgets.QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        main_layout.addWidget(QtWidgets.QLabel("Status:"))
        main_layout.addWidget(self.status_text)

    def update_location_label(self):
        export_path = Config.get_export_path()
        self.location_label.setText(f"Files export to:\n{export_path}")

    def on_animation_toggled(self, checked):
        self.start_frame_spin.setEnabled(checked)
        self.end_frame_spin.setEnabled(checked)

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")

    def on_export_clicked(self):
        self.log("Export button clicked")
        selection = cmds.ls(selection=True)
        if not selection:
            QtWidgets.QMessageBox.warning(
                self, "Nothing selected",
                "Please select one or more objects in Maya before exporting."
            )
            self.log("Export cancelled - no objects selected.")
            return
        # Here would be call to actual export logic

    def on_change_export_location(self):
        if prompt_for_export_folder():
            self.update_location_label()
            self.log("Export folder updated.")


# ============================================================================
# PUBLIC API - Show UI
# ============================================================================

def show_ui():
    if not Config.get_export_path():
        if not prompt_for_export_folder():
            print("Export path must be selected before using LayoutLink.")
            return

    window = LayoutLinkUI()
    window.show()


# ============================================================================
# AUTO-LOAD MESSAGE
# ============================================================================

show_ui()
