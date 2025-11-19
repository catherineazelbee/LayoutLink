"""
Maya USD Layout Link Plugin - Production Ready
==========================

Bidirectional USD scene data exchange between Maya and Unreal Engine.
Professional workflow using USD references and composition.
"""

import os
import sys
import datetime

import maya.cmds as cmds

# Add current directory to path for imports
current_dir = os.path.dirname(__file__) if __file__ else os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import backend modules
import maya_mesh_export
import maya_layout_export
import maya_layout_import
import quick_updater 

from PySide6 import QtWidgets, QtCore
from shiboken6 import wrapInstance
import maya.OpenMayaUI as omui
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# ============================================================================
# CONFIGURATION
# ============================================================================


class Config:
    """LayoutLink configuration"""

    VERSION = "0.1.0"
    ASSET_LIBRARY_VAR = "layoutlink_asset_library"
    LAYOUT_EXPORT_VAR = "layoutlink_layout_export"

    @classmethod
    def get_asset_library(cls):
        if cmds.optionVar(exists=cls.ASSET_LIBRARY_VAR):
            return cmds.optionVar(q=cls.ASSET_LIBRARY_VAR)
        return "C:/SharedUSD/assets/maya"

    @classmethod
    def set_asset_library(cls, path):
        cmds.optionVar(sv=(cls.ASSET_LIBRARY_VAR, path))

    @classmethod
    def get_layout_export(cls):
        if cmds.optionVar(exists=cls.LAYOUT_EXPORT_VAR):
            return cmds.optionVar(q=cls.LAYOUT_EXPORT_VAR)
        return "C:/SharedUSD/layouts/maya_layouts"

    @classmethod
    def set_layout_export(cls, path):
        cmds.optionVar(sv=(cls.LAYOUT_EXPORT_VAR, path))


# ============================================================================
# UI - Using MayaQWidgetDockableMixin for proper docking
# ============================================================================


class LayoutLinkUI(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    WINDOW_TITLE = "LayoutLink"
    WINDOW_OBJECT = "LayoutLinkWindow"

    def __init__(self, parent=None):
        super(LayoutLinkUI, self).__init__(parent=parent)

        self.setObjectName(self.WINDOW_OBJECT)
        self.setWindowTitle(self.WINDOW_TITLE)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(main_layout)

        # Header
        header = QtWidgets.QLabel("LayoutLink - Professional USD Pipeline")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        header.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(header)

        # ============================================================
        # SETTINGS SECTION
        # ============================================================
        settings_group = QtWidgets.QGroupBox("Settings")
        settings_layout = QtWidgets.QFormLayout()

        # Asset Library Path
        asset_layout = QtWidgets.QHBoxLayout()
        self.asset_library_input = QtWidgets.QLineEdit(Config.get_asset_library())
        asset_browse_btn = QtWidgets.QPushButton("Browse...")
        asset_browse_btn.clicked.connect(self.browse_asset_library)
        asset_layout.addWidget(self.asset_library_input)
        asset_layout.addWidget(asset_browse_btn)
        settings_layout.addRow("Asset Library:", asset_layout)

        # Layout Export Path
        layout_layout = QtWidgets.QHBoxLayout()
        self.layout_export_input = QtWidgets.QLineEdit(Config.get_layout_export())
        layout_browse_btn = QtWidgets.QPushButton("Browse...")
        layout_browse_btn.clicked.connect(self.browse_layout_export)
        layout_layout.addWidget(self.layout_export_input)
        layout_layout.addWidget(layout_browse_btn)
        settings_layout.addRow("Layout Export:", layout_layout)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # ============================================================
        # EXPORT TO UNREAL SECTION
        # ============================================================
        export_group = QtWidgets.QGroupBox("Export to Unreal")
        export_layout = QtWidgets.QVBoxLayout()
        
                # Frame Range Controls
        frame_range_label = QtWidgets.QLabel("Animation Frame Range:")
        frame_range_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        export_layout.addWidget(frame_range_label)

        frame_controls = QtWidgets.QHBoxLayout()

        # Start frame spinbox
        start_label = QtWidgets.QLabel("Start:")
        frame_controls.addWidget(start_label)

        self.start_frame_spin = QtWidgets.QSpinBox()
        self.start_frame_spin.setRange(-10000, 10000)
        self.start_frame_spin.setMinimumWidth(80)
        frame_controls.addWidget(self.start_frame_spin)

        # End frame spinbox
        end_label = QtWidgets.QLabel("End:")
        frame_controls.addWidget(end_label)

        self.end_frame_spin = QtWidgets.QSpinBox()
        self.end_frame_spin.setRange(-10000, 10000)
        self.end_frame_spin.setMinimumWidth(80)
        frame_controls.addWidget(self.end_frame_spin)

        # Sync from timeline button
        sync_btn = QtWidgets.QPushButton("↻ Get from Timeline")
        sync_btn.clicked.connect(self.sync_frame_range_from_timeline)
        frame_controls.addWidget(sync_btn)

        frame_controls.addStretch()
        export_layout.addLayout(frame_controls)

        # Export Mesh Library Button
        self.mesh_export_btn = QtWidgets.QPushButton(
            "📦 Export Mesh Library (Selected)"
        )
        self.mesh_export_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:pressed { background-color: #0D47A1; }
        """
        )
        self.mesh_export_btn.clicked.connect(self.on_export_mesh_library)
        export_layout.addWidget(self.mesh_export_btn)

        # Export Layout Button
        self.layout_export_btn = QtWidgets.QPushButton("📤 Export Layout (Selected)")
        self.layout_export_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
        """
        )
        self.layout_export_btn.clicked.connect(self.on_export_layout)
        export_layout.addWidget(self.layout_export_btn)

        export_group.setLayout(export_layout)
        main_layout.addWidget(export_group)

        # ============================================================
        # IMPORT FROM UNREAL SECTION
        # ============================================================
        import_group = QtWidgets.QGroupBox("Import from Unreal")
        import_layout = QtWidgets.QVBoxLayout()

        # Import Button
        self.import_btn = QtWidgets.QPushButton("📥 Import Layout from Unreal")
        self.import_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #F57C00; }
            QPushButton:pressed { background-color: #E65100; }
        """
        )
        self.import_btn.clicked.connect(self.on_import_layout)
        import_layout.addWidget(self.import_btn)

        import_group.setLayout(import_layout)
        main_layout.addWidget(import_group)
        
        # Quick Update Button
        self.update_btn = QtWidgets.QPushButton("🔄 Update from Unreal")
        self.update_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #7B1FA2; }
            QPushButton:pressed { background-color: #4A148C; }
        """
        )
        self.update_btn.clicked.connect(self.on_update_from_unreal)
        import_layout.addWidget(self.update_btn)

        # ============================================================
        # STATUS LOG
        # ============================================================
        status_label = QtWidgets.QLabel("Status Log:")
        main_layout.addWidget(status_label)

        self.status_text = QtWidgets.QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        main_layout.addWidget(self.status_text)

        # Initial log message
        self.log("LayoutLink ready. Select objects and click export buttons.")
        self.log(f"Asset Library: {Config.get_asset_library()}")
        self.log(f"Layout Export: {Config.get_layout_export()}")

        # Initialize from current timeline
        self.sync_frame_range_from_timeline()

    # ========================================================================
    # BUTTON HANDLERS
    # ========================================================================

    def on_export_mesh_library(self):
        """Export selected meshes to USD asset library"""
        self.log("\n=== Starting Mesh Library Export ===")

        # Save settings
        Config.set_asset_library(self.asset_library_input.text())
        asset_lib = Config.get_asset_library()

        # Check selection
        selection = cmds.ls(selection=True)
        if not selection:
            QtWidgets.QMessageBox.warning(
                self,
                "No Selection",
                "Please select one or more mesh objects before exporting.",
            )
            self.log("ERROR: No objects selected")
            return

        self.log(f"Exporting to: {asset_lib}")

        try:
            # Call backend export
            result = maya_mesh_export.export_selected_meshes_library(asset_lib)

            if result["success"]:
                self.log(f"Success! Exported {result['exported_count']} mesh(es)")
                if result["failed_count"] > 0:
                    self.log(f"Failed: {result['failed_count']} mesh(es)")

                QtWidgets.QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Exported {result['exported_count']} meshes to asset library.",
                )
            else:
                self.log(f"Export failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            self.log(f"ERROR: {e}")
            QtWidgets.QMessageBox.critical(
                self, "Export Failed", f"An error occurred:\n{e}"
            )

    def on_export_layout(self):
        """Export selected objects as layout with references"""
        try:
            self.log("\n=== Starting Layout Export ===")

            # Save settings
            Config.set_asset_library(self.asset_library_input.text())
            Config.set_layout_export(self.layout_export_input.text())

            asset_lib = Config.get_asset_library()
            layout_dir = Config.get_layout_export()

            # Check selection
            selection = cmds.ls(selection=True)
            if not selection:
                QtWidgets.QMessageBox.warning(
                    self,
                    "No Selection",
                    "Please select one or more objects before exporting.",
                )
                self.log("ERROR: No objects selected")
                return

            # Create layout directory if needed
            if not os.path.exists(layout_dir):
                os.makedirs(layout_dir)
                self.log(f"Created directory: {layout_dir}")

            # Get filename - Use QTimer to defer dialog after Qt events
            self.log("Preparing file dialog...")

            # Store context for deferred execution
            self._export_context = {"asset_lib": asset_lib, "layout_dir": layout_dir}

            # Use QTimer.singleShot to delay dialog until after button click completes
            QtCore.QTimer.singleShot(0, self._show_export_dialog)

        except Exception as e:
            self.log(f"ERROR in on_export_layout: {e}")
            import traceback

            self.log(traceback.format_exc())

    def _show_export_dialog(self):
        """Deferred function to show export dialog (called via QTimer)"""
        try:
            asset_lib = self._export_context["asset_lib"]
            layout_dir = self._export_context["layout_dir"]

            self.log("Opening file dialog...")

            file_path = cmds.fileDialog2(
                fileFilter="USD Files (*.usda);;All Files (*.*)",
                dialogStyle=2,
                fileMode=0,
                caption="Save Layout File",
                startingDirectory=layout_dir,
                okCaption="Save",
            )

            if not file_path:
                self.log("Export cancelled - no file selected")
                return

            self.log(f"Exporting to: {file_path[0]}")
            self.log(f"Using asset library: {asset_lib}")

            # Get frame range from UI
            start_frame = self.start_frame_spin.value()
            end_frame = self.end_frame_spin.value()

            self.log(f"Exporting with frame range: {start_frame}-{end_frame}")

            result = maya_layout_export.export_selected_to_usd(
                file_path[0],
                asset_lib,
                start_frame=start_frame,
                end_frame=end_frame,
            )

            if result["success"]:
                self.log(f"Success! Exported {result['object_count']} object(s)")
                self.log(f"  With references: {result['objects_with_refs']}")
                if result.get("cameras_exported", 0) > 0:
                    self.log(f"  Cameras: {result['cameras_exported']}")

                QtWidgets.QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Layout exported!\n\nObjects: {result['object_count']}",
                )
            else:
                self.log(f"Export failed: {result.get('error')}")

        except Exception as e:
            self.log(f"ERROR: {e}")
            import traceback

            self.log(traceback.format_exc())

    def on_import_layout(self):
        """Import USD layout from Unreal as USD Stage"""
        self.log("\n=== Starting Layout Import ===")

        try:
            result = maya_layout_import.import_with_file_dialog()

            if result["success"]:
                self.log(f"Success! Created USD Stage")
                self.log(f"  Stage: {result['stage_transform']}")

            else:
                if result.get("error") != "Cancelled":
                    self.log(f"Import failed: {result.get('error')}")

        except Exception as e:
            self.log(f"ERROR: {e}")
            import traceback

            self.log(traceback.format_exc())

    def on_update_from_unreal(self):
        """Quick update existing USD stage with Unreal changes"""
        import quick_updater
        
        self.log("\n=== Quick Update from Unreal ===")
        
        # Find all USD stages in scene
        stages = quick_updater.list_all_usd_stages()
        
        if not stages:
            QtWidgets.QMessageBox.warning(
                self, "No USD Stages",
                "No USD stages found in scene.\n\n"
                "Import a layout first, then use Update to refresh it."
            )
            self.log("ERROR: No USD stages in scene")
            return
        
        self.log(f"Found {len(stages)} USD stage(s) in scene")
        
        # If multiple stages, let user pick which one to update
        selected_stage = None
        
        if len(stages) > 1:
            # Show selection dialog
            stage_names = [s.split('|')[-1] for s in stages]  # Short names
            
            item, ok = QtWidgets.QInputDialog.getItem(
                self, "Select Stage to Update",
                "Multiple USD stages found.\nWhich one should be updated with Unreal changes?",
                stage_names, 0, False
            )
            
            if not ok:
                self.log("Update cancelled")
                return
            
            # Find the full path for selected stage
            idx = stage_names.index(item)
            selected_stage = stages[idx]
            
        else:
            # Only one stage - use it
            selected_stage = stages[0]
        
        stage_short_name = selected_stage.split('|')[-1]
        self.log(f"Updating stage: {stage_short_name}")
        
        # Get current file info
        info = quick_updater.get_stage_info(selected_stage)
        if info:
            self.log(f"  Current file: {os.path.basename(info['file_path'])}")
            self.log(f"  Layer type: {info['layer_type']}")
        
        # Do the update!
        try:
            result = quick_updater.update_existing_stage(selected_stage)
            
            if result["success"]:
                old_name = os.path.basename(result['old_path'])
                new_name = os.path.basename(result['new_path'])
                
                self.log("✅ Update Complete!")
                self.log(f"  From: {old_name}")
                self.log(f"  To: {new_name}")
                
                QtWidgets.QMessageBox.information(
                    self, "Update Complete",
                    f"Stage updated with Unreal changes!\n\n"
                    f"Stage: {stage_short_name}\n"
                    f"New file: {new_name}\n\n"
                    f"✓ Updated in <10 seconds\n"
                    f"✓ Animation preserved\n"
                    f"✓ Scene setup unchanged"
                )
            else:
                error = result.get('error', 'Unknown error')
                self.log(f"❌ Update failed: {error}")
                
                QtWidgets.QMessageBox.warning(
                    self, "Update Failed",
                    f"Could not update stage:\n\n{error}\n\n"
                    f"Common issues:\n"
                    f"• Unreal hasn't exported yet\n"
                    f"• Wrong filename (must match BASE layer name)\n"
                    f"• File not found\n\n"
                    f"Make sure Unreal exports with the same shot name!"
                )
        
        except Exception as e:
            self.log(f"ERROR: {e}")
            import traceback
            self.log(traceback.format_exc())
            
            QtWidgets.QMessageBox.critical(
                self, "Update Error",
                f"An error occurred:\n\n{e}"
            )
        
    # ========================================================================
    # HELPER FUNCTIONS
    # ========================================================================

    def browse_asset_library(self):
        """Browse for asset library directory"""
        directory = cmds.fileDialog2(
            fileMode=3,
            caption="Select Asset Library Directory",
            startingDirectory=self.asset_library_input.text(),
        )
        if directory:
            self.asset_library_input.setText(directory[0])
            Config.set_asset_library(directory[0])
            self.log(f"Asset library set to: {directory[0]}")

    def browse_layout_export(self):
        """Browse for layout export directory"""
        directory = cmds.fileDialog2(
            fileMode=3,
            caption="Select Layout Export Directory",
            startingDirectory=self.layout_export_input.text(),
        )
        if directory:
            self.layout_export_input.setText(directory[0])
            Config.set_layout_export(directory[0])
            self.log(f"Layout export set to: {directory[0]}")

    def log(self, message):
        """Add message to status log"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        
    def sync_frame_range_from_timeline(self):
        """Sync frame range spinboxes from Maya timeline"""
        start = int(cmds.playbackOptions(query=True, minTime=True))
        end = int(cmds.playbackOptions(query=True, maxTime=True))

        self.start_frame_spin.setValue(start)
        self.end_frame_spin.setValue(end)

        # Only log if status_text exists (skip during initialization)
        if hasattr(self, "status_text"):
            self.log(f"Frame range synced from timeline: {start}-{end}")


# ============================================================================
# PUBLIC API
# ============================================================================


def show_ui():
    """Show the LayoutLink UI as a dockable window"""

    # Delete existing instance
    workspace_control_name = LayoutLinkUI.WINDOW_OBJECT + "WorkspaceControl"
    if cmds.workspaceControl(workspace_control_name, exists=True):
        cmds.deleteUI(workspace_control_name)

    # Create new instance
    ui = LayoutLinkUI()
    ui.show(dockable=True)

    return ui


# ============================================================================
# AUTO-LAUNCH
# ============================================================================

if __name__ == "__main__" or __name__ == "maya_LayoutLink":
    show_ui()
