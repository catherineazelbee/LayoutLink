"""
LayoutLink USD Export (Python)
Handles exporting Unreal actors to USD for Maya import
"""

import unreal
import metadata_utils

def export_selected_to_usd(file_path):
    """
    Export selected actors to USD file with LayoutLink metadata.
    
    Args:
        file_path (str): Where to save the USD file
    
    Returns:
        dict: Result with success status and actor count
    """
    unreal.log("=== Python USD Export Starting ===")
    unreal.log(f"Target: {file_path}")
    
    # STEP 1: Get selected actors
    editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected_actors = editor_subsystem.get_selected_level_actors()
    
    if not selected_actors:
        unreal.log_warning("No actors selected")
        return {"success": False, "error": "No actors selected"}
    
    unreal.log(f"Exporting {len(selected_actors)} actor(s)")
    for actor in selected_actors:
        unreal.log(f"  - {actor.get_actor_label()}")
    
    # STEP 2: Import USD Python modules
    try:
        from pxr import Usd, Sdf
    except ImportError:
        unreal.log_error("USD Python modules not available")
        return {"success": False, "error": "USD not available"}
    
    # STEP 3: Create or overwrite USD layer
    # Check if file exists and delete it first
    import os
    if os.path.exists(file_path):
        unreal.log(f"File exists, removing: {file_path}")
        os.remove(file_path)

    # Now create new layer
    layer = Sdf.Layer.CreateNew(file_path)
        
    # STEP 4: Add metadata using shared utility
    metadata_utils.add_layoutlink_metadata(
        layer, 
        operation="unreal_export", 
        app="Unreal Engine"
    )
    
    # STEP 5: Save the file
    layer.Save()
    
    unreal.log(f"Created USD file: {file_path}")
    unreal.log("=== Python USD Export Complete ===")
    
    return {
        "success": True,
        "actor_count": len(selected_actors),
        "file_path": file_path
    }