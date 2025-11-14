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

    # Detect layer type
    import simple_layers

    layer_type = simple_layers.get_layer_type(file_path)
    unreal.log(f"Layer type detected: {layer_type}")

    if layer_type == "override":
        base_path = simple_layers.get_base_from_override(file_path)
        if base_path:
            unreal.log(f"  References BASE: {base_path}")
        else:
            unreal.log("  WARNING: Could not find BASE layer!")

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
        unreal.UsdStageActor.static_class(), location, rotation
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

    stage_actor.set_editor_property("time", 0.0)

    # Read animation metadata and set timeline
    try:
        from pxr import Sdf

        layer = Sdf.Layer.FindOrOpen(abs_file_path)
        if layer:
            custom_data = layer.customLayerData or {}

            start = custom_data.get("layoutlink_start_frame")
            end = custom_data.get("layoutlink_end_frame")

            if start is not None and end is not None:
                # Use correct Unreal property names
                stage_actor.set_editor_property(
                    "initial_load_set", unreal.UsdInitialLoadSet.LOAD_ALL
                )

                # Set time range (use StartTimeCode and EndTimeCode, not start_time_code)
                try:
                    stage_actor.set_editor_property("StartTimeCode", float(start))
                    stage_actor.set_editor_property("EndTimeCode", float(end))
                    unreal.log(f"✓ Animation range set: {start}-{end}")
                except:
                    # If that doesn't work, try lowercase
                    unreal.log(f"Note: Animation range in metadata: {start}-{end}")
                    unreal.log("Add USD Stage Actor to Sequencer to see animation")

    except Exception as e:
        unreal.log(f"Note: Could not set animation range: {e}")

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
