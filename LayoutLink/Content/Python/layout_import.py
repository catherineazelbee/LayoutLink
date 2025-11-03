"""
LayoutLink USD Import (Python)
Imports USD from Maya including meshes and cameras
"""

import unreal
import os

def import_usd_from_maya(file_path):
    """Import USD from Maya with mesh and camera support"""
    unreal.log("=== Python Import Starting ===")
    unreal.log(f"File: {file_path}")
    
    # Check file exists
    if not os.path.exists(file_path):
        unreal.log_error("File not found")
        return {"success": False}
    
    # Get world
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    
    if not world:
        unreal.log_error("No world")
        return {"success": False}
    
    # Spawn USD Stage Actor
    location = unreal.Vector(0, 0, 0)
    rotation = unreal.Rotator(0, 0, 0)
    
    stage_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.UsdStageActor.static_class(),
        location,
        rotation
    )
    
    if not stage_actor:
        unreal.log_error("Failed to spawn actor")
        return {"success": False}
    
    # Load USD file - Use absolute path with dictionary
    stage_actor.set_actor_label("MayaLayoutImport")
    
    abs_file_path = os.path.abspath(file_path)
    unreal.log(f"Absolute path: {abs_file_path}")
    
    stage_actor.set_editor_property("root_layer", {"file_path": abs_file_path})
    stage_actor.set_editor_property("time", 0.0)
    
    # Try to read USD and check for cameras
    try:
        from pxr import Usd, UsdGeom
        
        stage = Usd.Stage.Open(abs_file_path)
        camera_count = 0
        
        for prim in stage.TraverseAll():
            if prim.GetTypeName() == "Camera":
                camera_count += 1
                unreal.log(f"Found camera in USD: {prim.GetPath()}")
        
        if camera_count > 0:
            unreal.log(f"Note: {camera_count} camera(s) found in USD")
            unreal.log("Cameras imported as USD prims (visible in USD Stage Editor)")
            
    except:
        pass  # Camera detection is optional
    
    unreal.log("=== Import Complete ===")
    return {"success": True}