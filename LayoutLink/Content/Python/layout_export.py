"""
LayoutLink USD Layout Export (Python)
Exports Unreal layout with USD references to mesh library
Supports meshes and cameras
"""

import unreal
import metadata_utils
import os

def sanitize_name(name):
    """Clean up name for USD compatibility"""
    invalid_chars = '<>:"/\\|?*. '
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name

def get_relative_path(from_file, to_file):
    """
    Get relative path from one file to another.
    USD references use relative paths for portability.
    """
    from_dir = os.path.dirname(os.path.abspath(from_file))
    to_path = os.path.abspath(to_file)
    
    try:
        rel_path = os.path.relpath(to_path, from_dir)
        # USD uses forward slashes
        rel_path = rel_path.replace('\\', '/')
        return rel_path
    except ValueError:
        # If on different drives on Windows, return absolute path
        return to_path.replace('\\', '/')

def export_selected_to_usd(file_path, asset_library_dir):
    """
    Export selected actors to USD layout file with references to mesh library.
    Supports static mesh actors and cameras.
    
    Args:
        file_path (str): Where to save the layout USD file
        asset_library_dir (str): Directory containing exported mesh USD files
    
    Returns:
        dict: Result with success status and actor count
    """
    unreal.log("=== Layout Export Starting ===")
    unreal.log(f"Layout file: {file_path}")
    unreal.log(f"Asset library: {asset_library_dir}")
    
    # STEP 1: Get selected actors
    editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected_actors = editor_subsystem.get_selected_level_actors()
    
    if not selected_actors:
        unreal.log_warning("No actors selected")
        return {"success": False, "error": "No actors selected"}
    
    unreal.log(f"Exporting {len(selected_actors)} actor(s)")
    
    # STEP 2: Check if asset library exists (optional)
    asset_library_exists = os.path.exists(asset_library_dir)
    if not asset_library_exists:
        unreal.log_warning(f"Asset library not found: {asset_library_dir}")
        unreal.log_warning("Exporting transforms only (no mesh references)")
    
    # STEP 3: Import USD Python modules
    try:
        from pxr import Usd, UsdGeom, Sdf
    except ImportError:
        unreal.log_error("USD Python modules not available")
        return {"success": False, "error": "USD not available"}
    
    # STEP 4: Remove existing file and create new USD stage
    abs_file_path = os.path.abspath(file_path)
    if os.path.exists(abs_file_path):
        unreal.log(f"Removing existing file: {abs_file_path}")
        os.remove(abs_file_path)
    
    # Create new USD stage
    stage = Usd.Stage.CreateNew(abs_file_path)
    
    if not stage:
        unreal.log_error("Failed to create USD stage")
        return {"success": False, "error": "Could not create stage"}
    
    # Set up axis and units to match Unreal (Z-up, cm)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)  # cm to meters
    
    unreal.log("USD Stage created")
    
    # STEP 5: Process each selected actor
    exported_count = 0
    actors_with_refs = 0
    actors_without_refs = 0
    missing_meshes = []
    cameras_exported = 0
    
    for actor in selected_actors:
        actor_label = actor.get_actor_label()
        actor_name = sanitize_name(actor_label)
        prim_path = f"/{actor_name}"
        
        unreal.log(f"Processing: {actor_label}")
        
        # Check what type of actor this is
        actor_class = actor.get_class().get_name()
        
        # CAMERA HANDLING
        if actor_class == "CineCameraActor" or actor_class == "CameraActor":
            unreal.log(f"  Detected camera: {actor_class}")
            
            # Create camera prim
            camera_prim = UsdGeom.Camera.Define(stage, prim_path)
            
            # Get camera component
            camera_comp = actor.get_component_by_class(unreal.CameraComponent)
            
            if camera_comp:
                # Export camera attributes - Use correct Unreal property names
                try:
                    # For CineCameraComponent, properties are:
                    focal_length = camera_comp.get_editor_property("current_focal_length") / 10.0  # mm to cm
                    
                    # Filmback settings
                    filmback = camera_comp.get_editor_property("filmback")
                    sensor_width = filmback.sensor_width / 10.0   # mm to cm  
                    sensor_height = filmback.sensor_height / 10.0 # mm to cm
                    
                    camera_prim.GetFocalLengthAttr().Set(focal_length)
                    camera_prim.GetHorizontalApertureAttr().Set(sensor_width)
                    camera_prim.GetVerticalApertureAttr().Set(sensor_height)
                    
                    unreal.log(f"  Camera: focal={focal_length}cm, sensor={sensor_width}x{sensor_height}cm")
                    
                except Exception as e:
                    unreal.log_warning(f"  Could not get all camera properties: {e}")
                    # Set defaults if properties fail
                    camera_prim.GetFocalLengthAttr().Set(3.5)
                    camera_prim.GetHorizontalApertureAttr().Set(3.6)
                    camera_prim.GetVerticalApertureAttr().Set(2.4)
                
                # Clipping planes
                camera_prim.GetClippingRangeAttr().Set((0.1, 10000.0))
            
            cameras_exported += 1
            prim_to_transform = camera_prim
            
        # MESH HANDLING (existing code)
        else:
            static_mesh = None
            mesh_usd_path = None
            
            components = actor.get_components_by_class(unreal.StaticMeshComponent)
            if components and len(components) > 0:
                mesh_component = components[0]
                static_mesh = mesh_component.static_mesh
                
                if static_mesh:
                    # Use the MESH NAME not the actor name for the file
                    mesh_asset_name = static_mesh.get_name()
                    mesh_name = sanitize_name(mesh_asset_name)
                    mesh_file = f"{mesh_name}.usda"
                    mesh_full_path = os.path.join(asset_library_dir, mesh_file)
                    
                    # Check if mesh USD file exists (only if asset library exists)
                    if asset_library_exists and os.path.exists(mesh_full_path):
                        # Get relative path from layout file to mesh file
                        mesh_usd_path = get_relative_path(abs_file_path, mesh_full_path)
                        unreal.log(f"  Mesh: {mesh_name} -> {mesh_usd_path}")
                    elif asset_library_exists:
                        unreal.log_warning(f"  Mesh USD not found: {mesh_file}")
                        missing_meshes.append(mesh_name)
            
            # Create prim for mesh actor - use OverridePrim so reference type wins
            xform_prim = stage.OverridePrim(prim_path)
            
            # Add USD reference to mesh if available
            if mesh_usd_path:
                references = xform_prim.GetReferences()
                references.AddReference(mesh_usd_path)
                actors_with_refs += 1
                unreal.log(f"  ✓ Added reference to: {mesh_usd_path}")
            else:
                actors_without_refs += 1
            
            prim_to_transform = xform_prim
            
            # Add metadata attributes for meshes
            if static_mesh:
                unreal_asset_attr = xform_prim.CreateAttribute("unreal:assetPath", Sdf.ValueTypeNames.String)
                unreal_asset_attr.Set(static_mesh.get_path_name())
                
                unreal_mesh_attr = xform_prim.CreateAttribute("unreal:meshName", Sdf.ValueTypeNames.String)
                unreal_mesh_attr.Set(static_mesh.get_name())
        
        # SET TRANSFORM (works for both cameras and meshes)
        transform = actor.get_actor_transform()
        location = transform.translation
        rotation = transform.rotation.rotator()
        scale = transform.scale3d
        
        xformable = UsdGeom.Xformable(prim_to_transform)
        xformable.ClearXformOpOrder()
        
        # Add transform operations
        translate_op = xformable.AddTranslateOp()
        translate_op.Set((location.x, location.y, location.z))
        
        # SPECIAL HANDLING: Camera rotation conversion
        if actor_class == "CineCameraActor" or actor_class == "CameraActor":
            # Convert Unreal camera rotation (looks down +X in Z-up)
            # to Maya camera rotation (looks down -Z in Y-up)
            # 
            # Unreal: Z-up, camera forward = +X
            # Maya: Y-up, camera forward = -Z
            #
            # Conversion: Add -90° to pitch (Y rotation) to convert look direction
            converted_rotation = (
                rotation.roll,           # X (roll) - keep same
                rotation.pitch - 90.0,   # Y (pitch) - rotate -90° to convert +X to -Z
                rotation.yaw             # Z (yaw) - keep same
            )
            unreal.log(f"  Camera rotation converted: ({rotation.roll:.1f}, {rotation.pitch:.1f}, {rotation.yaw:.1f}) → ({converted_rotation[0]:.1f}, {converted_rotation[1]:.1f}, {converted_rotation[2]:.1f})")
            
            rotate_op = xformable.AddRotateXYZOp()
            rotate_op.Set(converted_rotation)
        else:
            # Regular mesh rotation - no conversion needed
            rotate_op = xformable.AddRotateXYZOp()
            rotate_op.Set((rotation.roll, rotation.pitch, rotation.yaw))
        
        scale_op = xformable.AddScaleOp()
        scale_op.Set((scale.x, scale.y, scale.z))
        
        # Add label attribute
        unreal_label_attr = prim_to_transform.GetPrim().CreateAttribute("unreal:actorLabel", Sdf.ValueTypeNames.String) if cameras_exported > 0 else prim_to_transform.CreateAttribute("unreal:actorLabel", Sdf.ValueTypeNames.String)
        unreal_label_attr.Set(actor_label)
        
        exported_count += 1
    
    # STEP 6: Add LayoutLink metadata
    root_layer = stage.GetRootLayer()
    metadata_utils.add_layoutlink_metadata(
        root_layer,
        operation="unreal_export",
        app="Unreal Engine"
    )
    
    # Add export statistics to metadata
    custom_data = dict(root_layer.customLayerData)
    custom_data["layoutlink_actors_with_refs"] = actors_with_refs
    custom_data["layoutlink_actors_without_refs"] = actors_without_refs
    custom_data["layoutlink_cameras_exported"] = cameras_exported
    custom_data["layoutlink_asset_library"] = os.path.basename(asset_library_dir)
    root_layer.customLayerData = custom_data
    
    # STEP 7: Save the stage
    stage.Save()
    
    # Get file size for verification
    file_size = os.path.getsize(abs_file_path)
    
    # Print summary
    unreal.log("=" * 60)
    unreal.log("Export Summary:")
    unreal.log(f"  Total actors: {exported_count}")
    unreal.log(f"  Meshes with references: {actors_with_refs}")
    unreal.log(f"  Meshes without references: {actors_without_refs}")
    unreal.log(f"  Cameras: {cameras_exported}")
    if missing_meshes:
        unreal.log(f"  Missing mesh assets: {len(missing_meshes)}")
        for mesh in missing_meshes:
            unreal.log(f"    - {mesh}.usda")
    unreal.log(f"  File size: {file_size} bytes")
    unreal.log("=" * 60)
    unreal.log(f"Saved: {abs_file_path}")
    unreal.log("=== Layout Export Complete ===")
    
    return {
        "success": True,
        "actor_count": exported_count,
        "actors_with_refs": actors_with_refs,
        "actors_without_refs": actors_without_refs,
        "cameras_exported": cameras_exported,
        "missing_meshes": missing_meshes,
        "file_path": abs_file_path,
        "file_size": file_size
    }