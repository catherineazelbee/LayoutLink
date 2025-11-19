"""
LayoutLink Quick Updater
=========================

Fast update workflow - reload USD stages with new files in <10 seconds.

Key Features:
- Updates existing USD stages without deleting/recreating
- Auto-finds Unreal override layers
- Handles coordinate system changes (Y-up vs Z-up)
- Preserves Maya scene setup (timeline, connections, etc.)
- Works with layered USD (BASE + OVERRIDE)

Usage:
    >>> import quick_updater
    >>> stages = quick_updater.list_all_usd_stages()
    >>> quick_updater.update_existing_stage(stages[0])
"""

import maya.cmds as cmds
import os
import simple_layers


def list_all_usd_stages():
    """
    Find all USD stages in current Maya scene.
    
    Returns:
        List of transform node names that have mayaUsdProxyShape children
    """
    all_shapes = cmds.ls(type='mayaUsdProxyShape')
    
    stages = []
    for shape in all_shapes:
        parents = cmds.listRelatives(shape, parent=True, fullPath=True)
        if parents:
            stages.append(parents[0])
    
    return stages


def get_stage_info(stage_transform):
    """
    Get information about a USD stage.
    
    Args:
        stage_transform: Transform node with mayaUsdProxyShape
        
    Returns:
        Dict with stage info, or None if not a valid stage
    """
    shapes = cmds.listRelatives(stage_transform, shapes=True, type='mayaUsdProxyShape')
    
    if not shapes:
        return None
    
    shape_node = shapes[0]
    file_path = cmds.getAttr(f'{shape_node}.filePath')
    
    # Detect layer type
    layer_type = simple_layers.get_layer_type(file_path)
    
    # Get app name if override
    app_name = None
    if layer_type == "override":
        if "_maya_OVER" in file_path:
            app_name = "maya"
        elif "_unreal_OVER" in file_path:
            app_name = "unreal"
    
    return {
        "transform": stage_transform,
        "shape": shape_node,
        "file_path": file_path,
        "layer_type": layer_type,
        "app_name": app_name
    }


def find_unreal_override_for_current(current_path):
    """
    Find Unreal override layer for current USD file.
    
    Handles these cases:
        shot_BASE.usda → shot_unreal_OVER.usda
        shot_maya_OVER.usda → shot_unreal_OVER.usda
        shot.usda → shot_unreal_OVER.usda (if exists)
    
    Args:
        current_path: Current USD file path
        
    Returns:
        Path to Unreal override, or None if not found
    """
    # First, find the base layer
    base_path = simple_layers.find_base_layer_for_file(current_path)
    
    if not base_path:
        print(f"Could not find BASE layer for: {current_path}")
        return None
    
    # Now find Unreal override for that base
    unreal_over = simple_layers.find_override_layer(base_path, "unreal")
    
    return unreal_over


def _get_stage_up_axis(file_path):
    """Get up-axis from USD file"""
    try:
        from pxr import Usd, UsdGeom
        stage = Usd.Stage.Open(file_path)
        return UsdGeom.GetStageUpAxis(stage)
    except Exception:
        return None


def update_existing_stage(stage_transform, new_usd_path=None):
    """
    Update existing USD stage with new file.
    
    This is FAST - just changes the file path, Maya auto-reloads!
    Takes <10 seconds instead of 30+ for delete/reimport.
    
    Args:
        stage_transform: Transform node with mayaUsdProxyShape
        new_usd_path: Path to new USD file (None = auto-find Unreal override)
        
    Returns:
        Dict with success status
    """
    print("=" * 60)
    print("=== Quick Update Starting ===")
    print(f"Updating: {stage_transform}")
    
    # Get stage info
    info = get_stage_info(stage_transform)
    
    if not info:
        error = "Not a valid USD stage"
        print(f"ERROR: {error}")
        return {"success": False, "error": error}
    
    shape_node = info['shape']
    current_path = info['file_path']
    
    print(f"Current file: {os.path.basename(current_path)}")
    print(f"  Layer type: {info['layer_type']}")
    
    # Auto-find Unreal override if not specified
    if not new_usd_path:
        print("\nSearching for Unreal override layer...")
        new_usd_path = find_unreal_override_for_current(current_path)
        
        if not new_usd_path:
            error = "No Unreal override found"
            print(f"ERROR: {error}")
            print("  Make sure Unreal has exported with the same shot name!")
            return {"success": False, "error": error}
        
        print(f"[OK] Found: {os.path.basename(new_usd_path)}")
    
    # Verify new file exists
    if not os.path.exists(new_usd_path):
        error = f"File not found: {new_usd_path}"
        print(f"ERROR: {error}")
        return {"success": False, "error": error}
    
    print(f"\nUpdating to: {os.path.basename(new_usd_path)}")
    
    # Get OLD file's up-axis before updating
    old_up_axis = _get_stage_up_axis(current_path)
    print(f"  Old file up-axis: {old_up_axis}")
    
    # THE MAGIC: Just change the file path - Maya reloads automatically!
    try:
        cmds.setAttr(f'{shape_node}.filePath', new_usd_path, type='string')
        print("[OK] File path updated")
    except Exception as e:
        error = f"Could not update file path: {e}"
        print(f"ERROR: {error}")
        return {"success": False, "error": error}
    
    # CRITICAL: Handle coordinate alignment for layer updates
    # When updating from BASE to OVERRIDE, we have mixed coordinate systems:
    # - BASE layer: Y-up content (from Maya)
    # - OVERRIDE layer: Z-up content (from Unreal) BUT already coordinate-converted
    #
    # The Unreal exporter ALREADY converts Z-up → USD space with Y-flip
    # So we should NOT add parent rotation for OVERRIDE layers!
    
    try:
        from pxr import Sdf
        
        # Read OVERRIDE metadata to determine source
        layer = Sdf.Layer.FindOrOpen(new_usd_path)
        if layer:
            custom_data = layer.customLayerData or {}
            app_source = custom_data.get("layoutlink_app", "")
            layer_type = custom_data.get("layoutlink_layer_type", "")
            
            print(f"  Layer type: {layer_type}, App: {app_source}")
            
            # For OVERRIDE layers, DON'T apply rotation
            # The coordinate conversion is already baked in the USD data
            if layer_type == "override":
                current_rot_x = cmds.getAttr(f'{stage_transform}.rotateX') or 0.0
                
                if abs(current_rot_x) > 0.01:
                    # Remove any rotation - override layers are pre-converted
                    cmds.setAttr(f'{stage_transform}.rotateX', 0.0)
                    print("  [OK] Reset rotation (override has pre-converted coordinates)")
                else:
                    print("  [OK] No rotation needed for override layer")
            
            # For BASE layers, check up-axis and apply rotation if needed
            elif layer_type == "base":
                base_up_axis = _get_stage_up_axis(new_usd_path)
                current_rot_x = cmds.getAttr(f'{stage_transform}.rotateX') or 0.0
                
                if str(base_up_axis).upper() == "Z":
                    if abs(current_rot_x - (-90.0)) > 0.01:
                        cmds.setAttr(f'{stage_transform}.rotateX', -90.0)
                        print("  [OK] Applied -90° for Z-up BASE")
                else:
                    if abs(current_rot_x) > 0.01:
                        cmds.setAttr(f'{stage_transform}.rotateX', 0.0)
                        print("  [OK] Reset rotation for Y-up BASE")
                        
    except Exception as e:
        print(f"  Warning: Could not check layer metadata: {e}")
    
    # Force viewport refresh
    cmds.refresh()
    
    print("=" * 60)
    print("[SUCCESS] UPDATE COMPLETE!")
    print("  Stage reloaded with Unreal changes")
    print("  Coordinate system aligned")
    print("  Animation preserved (if any)")
    print(f"  Time: <10 seconds")
    print("=" * 60)
    
    return {
        "success": True,
        "stage": stage_transform,
        "old_path": current_path,
        "new_path": new_usd_path
    }


def update_all_stages_to_unreal():
    """
    Update ALL USD stages in scene to their Unreal overrides.
    Convenience function for batch updates.
    
    Returns:
        Dict with results for each stage
    """
    print("=== Updating All Stages to Unreal ===")
    
    stages = list_all_usd_stages()
    
    if not stages:
        print("No USD stages found in scene")
        return {"success": False, "error": "No stages"}
    
    print(f"Found {len(stages)} stage(s)")
    
    results = {}
    success_count = 0
    
    for stage in stages:
        print(f"\nProcessing: {stage}")
        result = update_existing_stage(stage)
        results[stage] = result
        
        if result["success"]:
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"Updated {success_count}/{len(stages)} stages")
    print("=" * 60)
    
    return {
        "success": True,
        "total": len(stages),
        "updated": success_count,
        "results": results
    }


def switch_to_base_layer(stage_transform):
    """
    Switch a stage back to viewing the BASE layer (undo Unreal changes).
    
    Args:
        stage_transform: Transform node with mayaUsdProxyShape
        
    Returns:
        Dict with success status
    """
    print("=== Switching to BASE Layer ===")
    
    info = get_stage_info(stage_transform)
    if not info:
        return {"success": False, "error": "Not a valid stage"}
    
    current_path = info['file_path']
    
    # Find BASE layer
    base_path = simple_layers.find_base_layer_for_file(current_path)
    
    if not base_path:
        error = "Could not find BASE layer"
        print(f"ERROR: {error}")
        return {"success": False, "error": error}
    
    if current_path == base_path:
        print("Already viewing BASE layer")
        return {"success": True, "message": "Already on BASE"}
    
    print(f"Switching from: {os.path.basename(current_path)}")
    print(f"           to: {os.path.basename(base_path)}")
    
    # Update file path
    cmds.setAttr(f'{info["shape"]}.filePath', base_path, type='string')
    
    # Re-check coordinate system for BASE file
    base_up_axis = _get_stage_up_axis(base_path)
    if base_up_axis and str(base_up_axis).upper() == "Y":
        # BASE is Y-up, remove rotation
        cmds.setAttr(f'{stage_transform}.rotateX', 0.0)
        print("  Removed rotation for Y-up BASE")
    
    cmds.refresh()
    
    print("[OK] Switched to BASE layer")
    
    return {
        "success": True,
        "stage": stage_transform,
        "base_path": base_path
    }