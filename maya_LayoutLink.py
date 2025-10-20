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

# Maya imports
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om2

# PySide imports - Support both Maya 2025 (PySide6) and Maya 2022-2024 (PySide2)
try:
    # Try PySide6 first (Maya 2025+)
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance
    print("LayoutLink: Using PySide6 (Maya 2025+)")
except ImportError:
    try:
        # Fall back to PySide2 (Maya 2022-2024)
        from PySide2 import QtWidgets, QtCore, QtGui
        from shiboken2 import wrapInstance
        print("LayoutLink: Using PySide2 (Maya 2022-2024)")
    except ImportError:
        print("ERROR: Neither PySide6 nor PySide2 found!")
        raise

import maya.OpenMayaUI as omui

# USD imports
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
    Configuration settings for LayoutLink.
    Edit to match project your project structure.
    """

    # This is where USD files are shared between Maya and Unreal
    # Change this to your actual shared location (Windows)
    SHARED_USD_PATH = "C:/SharedUSD"

    # Subdirectories within shared path
    MAYA_EXPORT_DIR = "maya_exports"
    UNREAL_EXPORT_DIR = "unreal_exports"

    # Metadata keys for tracking plugin-specific info
    META_TIMESTAMP = "layoutlink_timestamp"
    META_APP = "layoutlink_app"
    META_ARTIST = "layoutlink_artist"
    META_OPERATION = "layoutlink_operation"
    META_VERSION = "layoutlink_version"

    VERSION = "0.1.0"

    @classmethod
    def get_maya_export_path(cls):
        """Get the full path to Maya export directory"""
        path = os.path.join(cls.SHARED_USD_PATH, cls.MAYA_EXPORT_DIR)
        if not os.path.exists(path):
            os.makedirs(path)
        return path
    
    @classmethod
    def get_unreal_export_path(cls):
        """Get the full path to Unreal export directory"""
        path = os.path.join(cls.SHARED_USD_PATH, cls.UNREAL_EXPORT_DIR)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

# ============================================================================
# METADATA MANAGER
# ============================================================================

class MetadataManager:
    """
    Handles reading and writing metadata to USD layers.
    Helps track what changes are made, when they are made, and from which program.
    """

    @staticmethod
    def add_metadata(usd_file_path, operation="export"):
        """
        Add LayoutLink metadata to a USD file after exporting from Maya.

        Args:
            usd_file_path (str): Path to the USD file
            operation (str): Type of operation (ex: push/pull)
        
        Returns:
            bool: True if success
        """
        if not os.path.exists(usd_file_path):
            print(f"File not found: {usd_file_path}")
            return False

        try:
            # Open the USD layer
            layer = Sdf.Layer.FindOrOpen(usd_file_path)
            if not layer:
                print(f"Could not open USD layer: {usd_file_path}")
                return False

            # Get or create customLayerData dictionary
            custom_data = dict(layer.customLayerData)

            # Add custom metadata
            custom_data[Config.META_TIMESTAMP] = datetime.datetime.utcnow().isoformat() + 'Z'
            custom_data[Config.META_ARTIST] = os.getenv('USER', 'unknown')
            custom_data[Config.META_OPERATION] = operation
            custom_data[Config.META_VERSION] = Config.VERSION

            # Write back to the layer
            layer.customLayerData = custom_data
            layer.Save()

            print(f"Added metadata to: {os.path.basename(usd_file_path)}")
            return True

        except Exception as e:
            print(f"Error adding metadata: {e}")
            return False
        
    @staticmethod
    def read_metadata(usd_file_path):
        """
        Read LayoutLink metadata from a USD file

        Args: 
            usd_file_path (str): Path to the USD file
        
        Returns:
            dict: Metadata dictionary, or None if not found
        """
        if not os.path.exists(usd_file_path):
            return None

        try:
            layer = Sdf.Layer.FindOrOpen(usd_file_path)
            if not layer:
                return None
            
            custom_data = layer.customLayerData

            # Extract LayoutLink metadata
            metadata = {}
            for key in [Config.META_TIMESTAMP, Config.META_ARTIST,
                        Config.META_APP, Config.META_OPERATION, Config.META_VERSION]:
                if key in custom_data:
                    metadata[key] = custom_data[key]

            return metadata if metadata else None

        except Exception as e:
            print(f"Error reading metadata: {e}")
            return None

    @staticmethod
    def print_metadata(usd_file_path):
        """
        Print metadata from a USD file in a readable format.

        Args:
            usd_file_path (str): Path to the USD file
        """
        metadata = MetadataManager.read_metadata(usd_file_path)

        if not metadata:
            print(f"No LayoutLink metadata found in: {usd_file_path}")
            return

        print(f"\n=== LayoutLink Metadata ===")
        print(f"File: {os.path.basename(usd_file_path)}")
        print(f"Timestamp: {metadata.get(Config.META_TIMESTAMP, 'N/A')}")
        print(f"Artist: {metadata.get(Config.META_ARTIST, 'N/A')}")
        print(f"App: {metadata.get(Config.META_APP, 'N/A')}")
        print(f"Operation: {metadata.get(Config.META_OPERATION, 'N/A')}")
        print(f"Version: {metadata.get(Config.META_VERSION, 'N/A')}")
        print(f"===========================\n")

# ============================================================================
# EXPORT MANAGER
# ============================================================================

class ExportManager:
    """
    Handles exporting Maya content to USD files.
    Core functionality for sending data to Unreal.
    """

    @staticmethod
    def export_selected(output_path, export_animation=False, 
                        start_frame=None, end_frame=None):
        """
        Export currently selected Maya objects to a USD file.

        Args:
            output_path (str): Where to save the USD file
            export_animation (bool): Whether to export animation
            start_frame (int): Animation start frame
            end_frame (int): Animation end frame

        Returns:
            bool: True if export succeeded
        """
        # Check if anything is selected
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            print("ERROR: Nothing selected to export")
            cmds.warning("Please select objects to export")
            return False
        
        print(f"\n=== Exporting to USD ===")
        print(f"Selected objects: {len(selection)}")
        print(f"Output: {output_path}")

        # Build export options
        export_options = {
            'file': output_path,
            'selection': True,
            'shadingMode': 'useRegistry',
            'convertMaterialsTo': ['UsdPreviewSurface'],
            'exportInstances': True,
            'mergeTransformAndShape': True,
            'exportDisplayColor': True,
            'exportUVs': True,
            'exportVisibility': True,
        }

        # Add animation options if requested
        if export_animation:
            if start_frame is None:
                start_frame = int(cmds.playbackOptions(q=True, min=True))
            if end_frame is None:
                end_frame = int(cmds.playbackOptions(q=True, max=True))
            
            export_options['animation'] = True
            export_options['frameRange'] = (start_frame, end_frame)
            export_options['eulerFilter'] = True

            print(f"Animation: Frames {start_frame} to {end_frame}")

        # Perform the export
        try: 
            cmds.mayaUSDExport(**export_options)
            print(f"Export successful!")
            print(f"========================\n")

            # Add the metadata to the exported file
            MetadataManager.add_metadata(output_path, operation="maya_export")

            return True

        except Exception as e:
            print(f"Export failed: {e}")
            print(f"========================\n")
            cmds.error(f"USD Export failed: {e}")
            return False
    
    @staticmethod
    def export_cameras_only(output_path):
        """
        Export only camera objects from the scene. 
        Useful for layout artists sharing camera work.

        Args:
            output_path (str): Where to save the USD file

        Returns: 
            bool: True if successful
        """
        # Find all cameras (excluding default cameras)
        all_cameras = cmds.ls(type='camera', long=True)
        default_cameras = ['frontShape', 'perspShape', 'sideShape', 'topShape']

        user_cameras = []
        for cam in all_cameras:
            # Get the short name for comparison
            short_name = cam.split('|')[-1]
            if short_name not in default_cameras:
                # Get the transform node (parent)
                transform = cmds.listRelatives(cam, parent=True, fullPath=True)
                if transform:
                    user_cameras.extend(transform)

        if not user_cameras:
            print("No user cameras found in scene")
            return False
        
        # Select cameras and export
        cmds.select(user_cameras, replace=True)
        return ExportManager.export_selected(output_path, export_animation=False)

# ============================================================================
# SIMPLE UI FOR LAYOUT ARTISTS
# ============================================================================

class LayoutLinkUI(QtWidgets.QDialog):
    """
    Simple, artist-friendly UI for pushing/pulling USD data.
    Big clear buttons, minimal technical jargon.
    """
    
    def __init__(self, parent=None):
        # Get Maya's main window as parent
        if parent is None:
            parent = self.get_maya_main_window()
        
        super().__init__(parent)
        
        self.setWindowTitle("LayoutLink - Maya to Unreal")
        self.setMinimumWidth(400)
        
        self.setup_ui()
    
    @staticmethod
    def get_maya_main_window():
        """Get Maya's main window as a QWidget"""
        ptr = omui.MQtUtil.mainWindow()
        return wrapInstance(int(ptr), QtWidgets.QWidget)
    
    def setup_ui(self):
        """Create all the UI elements"""
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # === HEADER ===
        header_label = QtWidgets.QLabel("Send Layout to Unreal Engine")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        header_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(header_label)
        
        # === FILE NAME INPUT ===
        filename_group = QtWidgets.QGroupBox("Output File Name")
        filename_layout = QtWidgets.QHBoxLayout()
        
        self.filename_input = QtWidgets.QLineEdit("maya_layout.usda")
        filename_layout.addWidget(self.filename_input)
        
        filename_group.setLayout(filename_layout)
        main_layout.addWidget(filename_group)
        
        # === OPTIONS ===
        options_group = QtWidgets.QGroupBox("Export Options")
        options_layout = QtWidgets.QVBoxLayout()
        
        # Animation checkbox
        self.animation_checkbox = QtWidgets.QCheckBox("Include Animation")
        self.animation_checkbox.setChecked(False)
        self.animation_checkbox.toggled.connect(self.on_animation_toggled)
        options_layout.addWidget(self.animation_checkbox)
        
        # Frame range (initially disabled)
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
        
        # === EXPORT BUTTON (BIG AND CLEAR) ===
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
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.export_button.clicked.connect(self.on_export_clicked)
        main_layout.addWidget(self.export_button)
        
        # === INFO DISPLAY ===
        info_group = QtWidgets.QGroupBox("Export Location")
        info_layout = QtWidgets.QVBoxLayout()
        
        self.location_label = QtWidgets.QLabel()
        self.location_label.setWordWrap(True)
        self.location_label.setStyleSheet("padding: 5px;")
        self.update_location_label()
        info_layout.addWidget(self.location_label)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # === STATUS LOG ===
        self.status_text = QtWidgets.QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        self.status_text.setPlaceholderText("Status messages will appear here...")
        main_layout.addWidget(QtWidgets.QLabel("Status:"))
        main_layout.addWidget(self.status_text)
        
        # === UTILITY BUTTONS ===
        util_layout = QtWidgets.QHBoxLayout()
        
        list_files_btn = QtWidgets.QPushButton("View Exported Files")
        list_files_btn.clicked.connect(self.on_list_files)
        util_layout.addWidget(list_files_btn)
        
        open_folder_btn = QtWidgets.QPushButton("Open Export Folder")
        open_folder_btn.clicked.connect(self.on_open_folder)
        util_layout.addWidget(open_folder_btn)
        
        main_layout.addLayout(util_layout)
    
    def update_location_label(self):
        """Update the label showing where files will be exported"""
        export_path = Config.get_maya_export_path()
        filename = self.filename_input.text()
        full_path = os.path.join(export_path, filename)
        self.location_label.setText(f"Files export to:\n{full_path}")
    
    def on_animation_toggled(self, checked):
        """Enable/disable frame range inputs based on animation checkbox"""
        self.start_frame_spin.setEnabled(checked)
        self.end_frame_spin.setEnabled(checked)
    
    def log(self, message):
        """Add a message to the status log"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
    
    def on_export_clicked(self):
        """Handle the main export button click"""
        # Check if anything is selected
        selection = cmds.ls(selection=True)
        if not selection:
            QtWidgets.QMessageBox.warning(
                self,
                "Nothing Selected",
                "Please select objects in Maya before exporting."
            )
            return
        
        # Get filename
        filename = self.filename_input.text()
        if not filename:
            QtWidgets.QMessageBox.warning(
                self,
                "No Filename",
                "Please enter a filename."
            )
            return
        
        # Ensure .usda extension
        if not filename.endswith(('.usd', '.usda', '.usdc')):
            filename += '.usda'
        
        # Build full path
        export_path = Config.get_maya_export_path()
        full_path = os.path.join(export_path, filename)
        
        # Get animation settings
        include_animation = self.animation_checkbox.isChecked()
        start_frame = self.start_frame_spin.value() if include_animation else None
        end_frame = self.end_frame_spin.value() if include_animation else None
        
        # Log start
        self.log(f"Exporting {len(selection)} object(s)...")
        
        # Perform export
        success = ExportManager.export_selected(
            full_path,
            export_animation=include_animation,
            start_frame=start_frame,
            end_frame=end_frame
        )
        
        if success:
            self.log("Export successful!")
            QtWidgets.QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported to:\n{full_path}\n\n"
                "You can now import this file in Unreal Engine."
            )
        else:
            self.log("Export failed")
            QtWidgets.QMessageBox.critical(
                self,
                "Export Failed",
                "Export failed. Check the Script Editor for details."
            )
    
    def on_list_files(self):
        """Show a dialog with all exported files"""
        export_dir = Config.get_maya_export_path()
        
        files = []
        for file in os.listdir(export_dir):
            if file.endswith(('.usd', '.usda', '.usdc')):
                files.append(file)
        
        if not files:
            QtWidgets.QMessageBox.information(
                self,
                "No Files",
                "No USD files found in export directory."
            )
            return
        
        # Create list dialog
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Exported Files")
        dialog.setMinimumSize(400, 300)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        list_widget = QtWidgets.QListWidget()
        for file in sorted(files):
            list_widget.addItem(file)
        
        layout.addWidget(list_widget)
        
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()
    
    def on_open_folder(self):
        """Open the export folder in file browser"""
        export_dir = Config.get_maya_export_path()
        
        # Platform-specific folder opening
        if os.name == 'nt':  # Windows
            os.startfile(export_dir)
        elif os.name == 'posix':  # Mac/Linux
            os.system(f'open "{export_dir}"')


# ============================================================================
# PUBLIC API - Main entry point
# ============================================================================

def show_ui():
    """
    Show the LayoutLink UI.
    This is what artists will run!
    
    Example:
        import maya_LayoutLink as mll
        mll.show_ui()
    """
    global layoutlink_window
    
    # Close existing window if it exists
    try:
        layoutlink_window.close()
        layoutlink_window.deleteLater()
    except:
        pass
    
    # Create and show new window
    layoutlink_window = LayoutLinkUI()
    layoutlink_window.show()
    
    return layoutlink_window


# ============================================================================
# AUTO-LOAD MESSAGE
# ============================================================================

# Load Maya USD plugin if not already loaded
if not cmds.pluginInfo('mayaUsdPlugin', q=True, loaded=True):
    try:
        cmds.loadPlugin('mayaUsdPlugin')
        print("LayoutLink: Loaded Maya USD plugin")
    except:
        print("LayoutLink: Warning - Could not load Maya USD plugin")

print("\n" + "="*60)
print("MAYA LAYOUTLINK v0.1.0")
print("="*60)
print("\nTo open the UI:")
print("  import maya_LayoutLink as mll")
print("  mll.show_ui()")
print()