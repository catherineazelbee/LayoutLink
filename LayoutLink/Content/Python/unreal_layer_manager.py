# unreal_layer_manager.py

"""
Automatic USD layer management for Unreal Engine.
Ensures BASE layers are never edited directly.
"""

import unreal
from pxr import Sdf, Usd, UsdUtils
import os

class UnrealUsdLayerManager:
    """
    Protects BASE layers by automatically creating/switching to override layers.
    """
    
    def __init__(self, stage_actor):
        self.stage_actor = stage_actor
        self.stage = None
        self.root_layer = None
        
        
    def setup_from_stage_actor(self):
        """Initialize from a USD Stage Actor"""
        if not self.stage_actor:
            return False
            
        # Get the USD file path from the stage actor
        root_layer = self.stage_actor.get_editor_property("root_layer")
        if not root_layer:
            return False
            
        # root_layer is a FilePath object, not a dict!
        file_path = root_layer.file_path  # Direct attribute access
        if not file_path or not os.path.exists(file_path):
            return False
            
        # Open the stage directly with pxr
        self.stage = Usd.Stage.Open(file_path)
        if not self.stage:
            return False
            
        self.root_layer = self.stage.GetRootLayer()
        return True
        
    def ensure_override_for_edit(self):
        """
        Main function: Ensure we're editing an override, not BASE.
        Call this after importing any USD file!
        """
        if not self.setup_from_stage_actor():
            unreal.log_warning("Could not setup layer manager")
            return None
            
        current_path = self.root_layer.identifier
        unreal.log(f"Checking layer protection for: {current_path}")
        
        # Simple_layers detection
        import simple_layers
        layer_type = simple_layers.get_layer_type(current_path)
        
        if layer_type == "override":
            unreal.log("Already on override layer - safe to edit")
            return current_path
            
        elif layer_type == "base":
            unreal.log("WARNING: Opened BASE layer directly!")
            unreal.log("Creating Unreal override layer for safe editing...")
            
            # Create override using your existing system
            override_path = simple_layers.create_override_layer(current_path, "unreal")
            
            # Update the stage actor to point to override
            self.stage_actor.set_editor_property(
                "root_layer", 
                {"file_path": override_path}
            )
            
            unreal.log(f"✓ Switched to OVERRIDE: {override_path}")
            unreal.log(f"✓ BASE protected: {current_path}")
            
            return override_path
            
        else:
            # Unknown/new file - create BASE first
            unreal.log("New file - will create BASE on first save")
            return current_path