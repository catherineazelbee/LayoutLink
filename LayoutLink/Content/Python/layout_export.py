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
    """Get relative path from one file to another"""
    from_dir = os.path.dirname(os.path.abspath(from_file))
    to_path = os.path.abspath(to_file)
    
    try:
        rel_path = os.path.relpath(to_path, from_dir)
        rel_path = rel_path.replace('\\', '/')
        return rel_path
    except ValueError:
        return to_path.replace('\\', '/')

def export_selected_to_usd(file_path, asset_library_dir):
    """Export selected actors to USD layout file"""
    unreal.log("=== Layout Export Starting ===")
    unreal.log(f"Layout file: {file_path}")
    unreal.log(f"Asset library: {asset_library_dir}")
    
    # Get selected actors
    editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected_actors = editor_subsystem.get_selected_level_actors()
    
    if not selected_actors:
        unreal.log_warning("No actors selected")
        return {"success": False, "error": "No actors selected"}
    
    unreal.log(f"Exporting {len(selected_actors)} actor(s)")
    
    # Check asset library
    asset_library_exists = os.path.exists(asset_library_dir)
    if not asset_library_exists:
        unreal.log_warning("Asset library not found - exporting transforms only")
    
    # Import USD modules
    try:
        from pxr import Usd, UsdGeom, Sdf
    except ImportError:
        unreal.log_error("USD Python modules not available")
        return {"success": False, "error": "USD not available"}
    
    # Create USD stage
    abs_file_path = os.path.abspath(file_path)
    if os.path.exists(abs_file_path):
        os.remove(abs_file_path)
    
    stage = Usd.Stage.CreateNew(abs_file_path)
    if not stage:
        unreal.log_error("Failed to create USD stage")
        return {"success": False, "error": "Could not create stage"}
    
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)
    unreal.log("USD Stage created")
    
    # Process actors
    exported_count = 0
    actors_with_refs = 0
    actors_without_refs = 0
    cameras_exported = 0
    missing_meshes = []
    
    for actor in selected_actors:
        actor_label = actor.get_actor_label()
        actor_name = sanitize_name(actor_label)
        prim_path = f"/{actor_name}"
        actor_class = actor.get_class().get_name()
        
        unreal.log(f"Processing: {actor_label}")
        
        # Determine actor type and create appropriate prim
        is_camera = (actor_class == "CineCameraActor" or actor_class == "CameraActor")
        
        if is_camera:
            # === CAMERA ===
            unreal.log(f"  Detected camera: {actor_class}")
            camera_prim = UsdGeom.Camera.Define(stage, prim_path)
            
            # Get camera component and export attributes
            camera_comp = actor.get_component_by_class(unreal.CameraComponent)
            if camera_comp:
                try:
                    focal_length = camera_comp.get_editor_property("current_focal_length") / 10.0
                    filmback = camera_comp.get_editor_property("filmback")
                    sensor_width = filmback.sensor_width / 10.0
                    sensor_height = filmback.sensor_height / 10.0
                    
                    camera_prim.GetFocalLengthAttr().Set(focal_length)
                    camera_prim.GetHorizontalApertureAttr().Set(sensor_width)
                    camera_prim.GetVerticalApertureAttr().Set(sensor_height)
                    camera_prim.GetClippingRangeAttr().Set((0.1, 10000.0))
                    
                    unreal.log(f"  Camera: focal={focal_length:.1f}cm, sensor={sensor_width:.1f}x{sensor_height:.1f}cm")
                except Exception as e:
                    unreal.log_warning(f"  Could not get camera properties: {e}")
                    camera_prim.GetFocalLengthAttr().Set(3.5)
                    camera_prim.GetHorizontalApertureAttr().Set(3.6)
                    camera_prim.GetVerticalApertureAttr().Set(2.4)
            
            cameras_exported += 1
            prim_to_transform = camera_prim
            
        else:
            # === MESH ===
            static_mesh = None
            mesh_usd_path = None
            
            components = actor.get_components_by_class(unreal.StaticMeshComponent)
            if components and len(components) > 0:
                mesh_component = components[0]
                static_mesh = mesh_component.static_mesh
                
                if static_mesh:
                    mesh_name = sanitize_name(static_mesh.get_name())
                    mesh_file = f"{mesh_name}.usda"
                    mesh_full_path = os.path.join(asset_library_dir, mesh_file)
                    
                    if asset_library_exists and os.path.exists(mesh_full_path):
                        mesh_usd_path = get_relative_path(abs_file_path, mesh_full_path)
                        unreal.log(f"  Mesh: {mesh_name} -> {mesh_usd_path}")
                    elif asset_library_exists:
                        unreal.log_warning(f"  Mesh USD not found: {mesh_file}")
                        missing_meshes.append(mesh_name)
            
            # Create mesh prim
            xform_prim = stage.OverridePrim(prim_path)
            
            if mesh_usd_path:
                references = xform_prim.GetReferences()
                references.AddReference(mesh_usd_path)
                actors_with_refs += 1
                unreal.log(f"  ✓ Added reference")
            else:
                actors_without_refs += 1
            
            prim_to_transform = xform_prim
            
            # Mesh metadata
            if static_mesh:
                xform_prim.CreateAttribute("unreal:assetPath", Sdf.ValueTypeNames.String).Set(static_mesh.get_path_name())
                xform_prim.CreateAttribute("unreal:meshName", Sdf.ValueTypeNames.String).Set(static_mesh.get_name())
        
        # === SET TRANSFORM (ONCE, for both cameras and meshes) ===
        transform = actor.get_actor_transform()
        location = transform.translation
        rotation = transform.rotation.rotator()
        scale = transform.scale3d
        
        xformable = UsdGeom.Xformable(prim_to_transform)
        xformable.ClearXformOpOrder()
        
        translate_op = xformable.AddTranslateOp()
        translate_op.Set((location.x, location.y, location.z))
        
        rotate_op = xformable.AddRotateXYZOp()
        rotate_op.Set((rotation.roll, rotation.pitch, rotation.yaw))
        
        scale_op = xformable.AddScaleOp()
        scale_op.Set((scale.x, scale.y, scale.z))
        
        # Add label
        if is_camera:
            prim_to_transform.GetPrim().CreateAttribute("unreal:actorLabel", Sdf.ValueTypeNames.String).Set(actor_label)
        else:
            prim_to_transform.CreateAttribute("unreal:actorLabel", Sdf.ValueTypeNames.String).Set(actor_label)
        
        exported_count += 1
    
    # Add metadata
    root_layer = stage.GetRootLayer()
    metadata_utils.add_layoutlink_metadata(root_layer, "unreal_export", "Unreal Engine")
    
    custom_data = dict(root_layer.customLayerData)
    custom_data["layoutlink_actors_with_refs"] = actors_with_refs
    custom_data["layoutlink_actors_without_refs"] = actors_without_refs
    custom_data["layoutlink_cameras_exported"] = cameras_exported
    custom_data["layoutlink_asset_library"] = os.path.basename(asset_library_dir)
    root_layer.customLayerData = custom_data
    
    stage.Save()
    file_size = os.path.getsize(abs_file_path)
    
    # Summary
    unreal.log("=" * 60)
    unreal.log("Export Summary:")
    unreal.log(f"  Total actors: {exported_count}")
    unreal.log(f"  Meshes with refs: {actors_with_refs}")
    unreal.log(f"  Meshes without refs: {actors_without_refs}")
    unreal.log(f"  Cameras: {cameras_exported}")
    if missing_meshes:
        unreal.log(f"  Missing meshes: {len(missing_meshes)}")
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