"""
LayoutLink USD Import (Python)
Imports USD from Maya including meshes and cameras WITH ANIMATION SUPPORT
"""

import unreal
import os


def import_usd_from_maya(file_path):
    """Import USD from Maya with mesh and camera support"""
    unreal.log("=== Python Import Starting ===")
    unreal.log(f"File: {file_path}")

    # Detect and log layer type but DON'T switch
    import simple_layers
    layer_type = simple_layers.get_layer_type(file_path)
    unreal.log(f"Layer type: {layer_type}")
    
    if layer_type == "override":
        base_path = simple_layers.get_base_from_override(file_path)
        if base_path:
            unreal.log(f"  This override references: {base_path}")
    elif layer_type == "base":
        unreal.log(f"  This is a BASE layer (source of truth)")

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

    # Load USD file AS-IS - no switching!
    stage_actor.set_actor_label("MayaLayoutImport")

    abs_file_path = os.path.abspath(file_path)
    unreal.log(f"Loading: {abs_file_path}")

    stage_actor.set_editor_property("root_layer", {"file_path": abs_file_path})
    stage_actor.set_editor_property("time", 0.0)

    # ========================================================================
    # Read animation metadata and setup Level Sequence
    # ========================================================================
    has_animation = False
    start_frame = 1
    end_frame = 120
    fps = 24
    animated_count = 0

    try:
        from pxr import Sdf, Usd
        
        # Open the stage to read animation metadata
        stage = Usd.Stage.Open(abs_file_path)
        root_layer = stage.GetRootLayer()
        
        # For layered files, check sublayers for metadata
        if root_layer.subLayerPaths:
            unreal.log("Checking sublayers for animation metadata...")
            for sublayer_path in root_layer.subLayerPaths:
                base_layer = Sdf.Layer.FindOrOpen(sublayer_path)
                if base_layer:
                    custom_data = base_layer.customLayerData or {}
                    if custom_data.get("layoutlink_has_animation"):
                        # Found animation metadata in sublayer!
                        has_animation = custom_data.get("layoutlink_has_animation", False)
                        start_frame = custom_data.get("layoutlink_start_frame", 1)
                        end_frame = custom_data.get("layoutlink_end_frame", 120)
                        fps = custom_data.get("layoutlink_fps", 24)
                        animated_count = custom_data.get("layoutlink_animated_objects", 0)
                        unreal.log(f"  Found animation in sublayer: {os.path.basename(sublayer_path)}")
                        break
        else:
            # Single file - read from root
            custom_data = root_layer.customLayerData or {}
            has_animation = custom_data.get("layoutlink_has_animation", False)
            start_frame = custom_data.get("layoutlink_start_frame", 1)
            end_frame = custom_data.get("layoutlink_end_frame", 120)
            fps = custom_data.get("layoutlink_fps", 24)
            animated_count = custom_data.get("layoutlink_animated_objects", 0)

        unreal.log(f"Animation metadata:")
        unreal.log(f"  Has animation: {has_animation}")
        unreal.log(f"  Frame range: {start_frame}-{end_frame}")
        unreal.log(f"  FPS: {fps}")
        unreal.log(f"  Animated objects: {animated_count}")

    except Exception as e:
        unreal.log(f"Note: Could not read animation metadata: {e}")

    # ========================================================================
    # Setup Level Sequence for animation playback
    # ========================================================================

    if has_animation:
        unreal.log("\n=== Setting up animation ===")

        # Get the Level Sequence that USD Stage Actor automatically creates
        level_sequence = stage_actor.get_editor_property("level_sequence")

        if level_sequence:
            unreal.log(f"✓ Found Level Sequence: {level_sequence.get_name()}")

            # Configure the sequence with the correct frame rate and range
            frame_rate = unreal.FrameRate(numerator=int(fps), denominator=1)
            level_sequence.set_display_rate(frame_rate)
            level_sequence.set_tick_resolution(frame_rate)

            # Set playback range
            level_sequence.set_playback_start(int(start_frame))
            level_sequence.set_playback_end(int(end_frame))

            # Set view range (adds padding so you can see the full timeline)
            level_sequence.set_view_range_start(float(start_frame - 10))
            level_sequence.set_view_range_end(float(end_frame + 10))

            unreal.log(f"✓ Configured Level Sequence:")
            unreal.log(f"  Frame rate: {fps} fps")
            unreal.log(f"  Playback range: {start_frame}-{end_frame}")

            # Open the sequence in Sequencer so user can see it
            unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(
                level_sequence
            )
            unreal.log(f"✓ Opened Level Sequence in Sequencer")

        else:
            unreal.log("WARNING: Expected Level Sequence but none found!")
            unreal.log("  Animation data is in USD but may not play automatically")

    else:
        unreal.log("No animation detected - imported as static layout")

    # ========================================================================
    # Camera detection
    # ========================================================================

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

    # ========================================================================
    # Summary
    # ========================================================================

    unreal.log("=" * 60)
    unreal.log("Import Summary:")
    unreal.log(f"  USD Stage Actor: MayaLayoutImport")
    unreal.log(f"  Layer type: {layer_type}")
    if has_animation:
        unreal.log(f"  Animation: {start_frame}-{end_frame} @ {fps}fps")
        unreal.log(f"  → Press PLAY in Sequencer to see animation")
    else:
        unreal.log(f"  Static layout (no animation)")
    unreal.log("=" * 60)
    unreal.log("=== Import Complete ===")

    return {
        "success": True,
        "has_animation": has_animation,
        "level_sequence": level_sequence if has_animation else None,
    }