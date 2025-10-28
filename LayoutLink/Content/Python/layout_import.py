"""
LayoutLink USD Import (Python)
"""

import unreal

def import_usd_from_maya(file_path):
    """Import USD from Maya"""
    unreal.log("=== Python Import Starting ===")
    unreal.log(f"File: {file_path}")
    
    # Check file exists
    import os
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
    
    # Load USD file
    stage_actor.set_actor_label("MayaLayoutImport")
    stage_actor.set_editor_property("root_layer", file_path)
    stage_actor.set_editor_property("time", 0.0)
    
    unreal.log("=== Import Complete ===")
    return {"success": True}