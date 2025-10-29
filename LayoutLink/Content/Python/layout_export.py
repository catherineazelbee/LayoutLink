"""
LayoutLink USD Layout Export (Python)
Exports Unreal layout with USD references to mesh library
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
    
    # STEP 2: Verify asset library exists
    if not os.path.exists(asset_library_dir):
        unreal.log_error(f"Asset library directory not found: {asset_library_dir}")
        return {"success": False, "error": "Asset library not found"}
    
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
    
    for actor in selected_actors:
        actor_label = actor.get_actor_label()
        actor_name = sanitize_name(actor_label)
        prim_path = f"/{actor_name}"
        
        unreal.log(f"Processing: {actor_label}")
        
        # Get static mesh component (if this actor has one)
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
                
                # Check if mesh USD file exists
                if os.path.exists(mesh_full_path):
                    # Get relative path from layout file to mesh file
                    mesh_usd_path = get_relative_path(abs_file_path, mesh_full_path)
                    unreal.log(f"  Mesh: {mesh_name} -> {mesh_usd_path}")
                else:
                    unreal.log_warning(f"  Mesh USD not found: {mesh_file}")
                    missing_meshes.append(mesh_name)
        
        # Create prim for this actor
        xform_prim = stage.DefinePrim(prim_path, "Xform")
        
        # Add USD reference to mesh if available
        if mesh_usd_path:
            references = xform_prim.GetReferences()
            references.AddReference(mesh_usd_path)
            actors_with_refs += 1
            unreal.log(f"  ✓ Added reference to: {mesh_usd_path}")
        else:
            actors_without_refs += 1
        
        # Set transform
        transform = actor.get_actor_transform()
        location = transform.translation
        rotation = transform.rotation.rotator()
        scale = transform.scale3d
        
        xformable = UsdGeom.Xformable(xform_prim)
        xformable.ClearXformOpOrder()
        
        # Add transform operations
        translate_op = xformable.AddTranslateOp()
        translate_op.Set((location.x, location.y, location.z))
        
        # Unreal rotation: Roll (X), Pitch (Y), Yaw (Z)
        rotate_op = xformable.AddRotateXYZOp()
        rotate_op.Set((rotation.roll, rotation.pitch, rotation.yaw))
        
        scale_op = xformable.AddScaleOp()
        scale_op.Set((scale.x, scale.y, scale.z))
        
        # Add metadata attributes
        if static_mesh:
            unreal_asset_attr = xform_prim.CreateAttribute("unreal:assetPath", Sdf.ValueTypeNames.String)
            unreal_asset_attr.Set(static_mesh.get_path_name())
            
            unreal_mesh_attr = xform_prim.CreateAttribute("unreal:meshName", Sdf.ValueTypeNames.String)
            unreal_mesh_attr.Set(static_mesh.get_name())
        
        unreal_label_attr = xform_prim.CreateAttribute("unreal:actorLabel", Sdf.ValueTypeNames.String)
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
    unreal.log(f"  With mesh references: {actors_with_refs}")
    unreal.log(f"  Without references: {actors_without_refs}")
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
        "missing_meshes": missing_meshes,
        "file_path": abs_file_path,
        "file_size": file_size
    }