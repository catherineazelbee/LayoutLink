# usd_stage_exporter.py
# Export changes made to USD Stage Actors back to USD

import unreal
import os


def export_usd_stage_changes(usd_stage_actor, output_path, start_frame, end_frame):
    """
    Export animation/transform changes from USD Stage Actor's Level Sequence.
    
    This handles the workflow where:
    1. Maya exports layout
    2. Unreal imports as USD Stage
    3. User edits in Unreal's Level Sequence
    4. Export those changes back to USD
    
    Args:
        usd_stage_actor: The UsdStageActor
        output_path: Where to save the USD file
        start_frame: Start frame
        end_frame: End frame
        
    Returns:
        Dict with success status
    """
    unreal.log("=== Exporting USD Stage Changes ===")
    
    # Get the Level Sequence attached to this USD Stage
    level_seq = usd_stage_actor.get_editor_property("level_sequence")
    
    if not level_seq:
        error = "USD Stage has no Level Sequence"
        unreal.log_error(error)
        return {"success": False, "error": error}
    
    unreal.log(f"Level Sequence: {level_seq.get_name()}")
    
    # OPTION 1: Use USD Stage's built-in Save functionality
    # The cleanest approach is to use USD's own save mechanism
    
    unreal.log("\nUsing USD Stage Editor's save functionality...")
    unreal.log("This writes changes directly back to the USD file")
    
    # Get the root layer path from the USD Stage
    root_layer = usd_stage_actor.get_editor_property("root_layer")
    current_file = root_layer.get("file_path", "")
    
    unreal.log(f"Current USD file: {current_file}")
    
    # We can't easily automate "File → Save" from Python
    # So we give clear instructions
    
    return {
        "success": False,
        "error": "Manual save required",
        "message": (
            "USD Stage Actor changes must be saved through USD Stage Editor:\n\n"
            "1. Window → Virtual Production → USD Stage\n"
            "2. Make your changes in the Level Sequence\n"
            "3. File → Save in USD Stage Editor\n"
            "4. Changes written to USD file\n"
            "5. Maya can reload the updated file"
        ),
        "workaround": "Use native actors for Unreal-side animation edits"
    }


def should_skip_usd_stage_actor(actor):
    """
    Check if actor is a USD Stage Actor.
    Returns (should_skip, message)
    """
    cls_name = actor.get_class().get_name()
    
    if cls_name == "UsdStageActor":
        return (True, "USD Stage Actor - use USD Stage Editor to save changes")
    
    return (False, None)