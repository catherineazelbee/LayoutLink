"""
LayoutLink USD Layout Export for Maya
Exports Maya layout with USD references to mesh library
"""

import maya.cmds as cmds
import maya_metadata_utils
import os

def sanitize_name(name):
    """Clean up name for USD compatibility"""
    invalid_chars = '<>:"/\\|?*. '
    for char in invalid_chars:
        name = name.replace(char, '_')
    # Remove namespace and path separators
    name = name.split(':')[-1]
    name = name.split('|')[-1]
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
    Export selected Maya objects to USD layout file with references to mesh library.
    
    Args:
        file_path (str): Where to save the layout USD file
        asset_library_dir (str): Directory containing exported mesh USD files
    
    Returns:
        dict: Result with success status and object count
    """
    print("=== Layout Export Starting ===")
    print(f"Layout file: {file_path}")
    print(f"Asset library: {asset_library_dir}")
    
    # STEP 1: Get selected objects
    selected = cmds.ls(selection=True, long=True, transforms=True)
    
    if not selected:
        print("No objects selected")
        return {"success": False, "error": "No objects selected"}
    
    print(f"Exporting {len(selected)} object(s)")
    
    # STEP 2: Check if asset library exists (optional)
    asset_library_exists = os.path.exists(asset_library_dir)
    if not asset_library_exists:
        print(f"WARNING: Asset library not found: {asset_library_dir}")
        print("Exporting transforms only (no mesh references)")
    
    # STEP 3: Import USD Python modules
    try:
        from pxr import Usd, UsdGeom, Sdf
    except ImportError:
        print("ERROR: USD Python modules not available")
        return {"success": False, "error": "USD not available"}
    
    # STEP 4: Remove existing file and create new USD stage
    abs_file_path = os.path.abspath(file_path)
    if os.path.exists(abs_file_path):
        print(f"Removing existing file: {abs_file_path}")
        os.remove(abs_file_path)
    
    # Create new USD stage
    stage = Usd.Stage.CreateNew(abs_file_path)
    
    if not stage:
        print("ERROR: Failed to create USD stage")
        return {"success": False, "error": "Could not create stage"}
    
    # Set up axis and units to match Maya (Y-up, cm)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)  # cm to meters
    
    print("USD Stage created")
    
    # STEP 5: Process each selected object
    exported_count = 0
    objects_with_refs = 0
    objects_without_refs = 0
    missing_meshes = []
    
    for obj in selected:
        obj_short_name = cmds.ls(obj, shortNames=True)[0]
        obj_name = sanitize_name(obj_short_name)
        prim_path = f"/{obj_name}"
        
        print(f"Processing: {obj_short_name}")
        
        # Check if object has mesh shape
        has_mesh = False
        mesh_usd_path = None
        
        shapes = cmds.listRelatives(obj, shapes=True, noIntermediate=True, fullPath=True)
        if shapes:
            for shape in shapes:
                if cmds.nodeType(shape) == 'mesh':
                    has_mesh = True
                    mesh_name = sanitize_name(obj_short_name)
                    mesh_file = f"{mesh_name}.usda"
                    mesh_full_path = os.path.join(asset_library_dir, mesh_file)
                    
                    # Check if mesh USD file exists
                    if asset_library_exists and os.path.exists(mesh_full_path):
                        mesh_usd_path = get_relative_path(abs_file_path, mesh_full_path)
                        print(f"  Mesh: {mesh_name} -> {mesh_usd_path}")
                    elif asset_library_exists:
                        print(f"  WARNING: Mesh USD not found: {mesh_file}")
                        missing_meshes.append(mesh_name)
                    else:
                        print(f"  Mesh: {mesh_name} (no reference - library not found)")
                    break
        
        # Create prim - use OverridePrim so reference type wins
        xform_prim = stage.OverridePrim(prim_path)
        
        # Add USD reference to mesh if available
        if mesh_usd_path:
            references = xform_prim.GetReferences()
            references.AddReference(mesh_usd_path)
            objects_with_refs += 1
            print(f"  ✓ Added reference to: {mesh_usd_path}")
        else:
            objects_without_refs += 1
        
        # Get transform from Maya
        translation = cmds.xform(obj, query=True, worldSpace=True, translation=True)
        rotation = cmds.xform(obj, query=True, worldSpace=True, rotation=True)
        scale = cmds.xform(obj, query=True, worldSpace=True, scale=True)
        
        # Set transform in USD
        xformable = UsdGeom.Xformable(xform_prim)
        xformable.ClearXformOpOrder()
        
        # Add transform operations
        translate_op = xformable.AddTranslateOp()
        translate_op.Set((translation[0], translation[1], translation[2]))
        
        # Maya rotation (XYZ order)
        rotate_op = xformable.AddRotateXYZOp()
        rotate_op.Set((rotation[0], rotation[1], rotation[2]))
        
        scale_op = xformable.AddScaleOp()
        scale_op.Set((scale[0], scale[1], scale[2]))
        
        # Add metadata attributes
        if has_mesh:
            maya_obj_attr = xform_prim.CreateAttribute("maya:objectName", Sdf.ValueTypeNames.String)
            maya_obj_attr.Set(obj_short_name)
        
        maya_label_attr = xform_prim.CreateAttribute("maya:originalName", Sdf.ValueTypeNames.String)
        maya_label_attr.Set(obj_short_name)
        
        exported_count += 1
    
    # STEP 6: Add LayoutLink metadata
    root_layer = stage.GetRootLayer()
    maya_metadata_utils.add_layoutlink_metadata(
        root_layer,
        operation="maya_export",
        app="Maya"
    )
    
    # Add export statistics to metadata
    custom_data = dict(root_layer.customLayerData)
    custom_data["layoutlink_objects_with_refs"] = objects_with_refs
    custom_data["layoutlink_objects_without_refs"] = objects_without_refs
    custom_data["layoutlink_asset_library"] = os.path.basename(asset_library_dir)
    root_layer.customLayerData = custom_data
    
    # STEP 7: Save the stage
    stage.Save()
    
    # Get file size for verification
    file_size = os.path.getsize(abs_file_path)
    
    # Print summary
    print("=" * 60)
    print("Export Summary:")
    print(f"  Total objects: {exported_count}")
    print(f"  With mesh references: {objects_with_refs}")
    print(f"  Without references: {objects_without_refs}")
    if missing_meshes:
        print(f"  Missing mesh assets: {len(missing_meshes)}")
        for mesh in missing_meshes:
            print(f"    - {mesh}.usda")
    print(f"  File size: {file_size} bytes")
    print("=" * 60)
    print(f"Saved: {abs_file_path}")
    print("=== Layout Export Complete ===")
    
    return {
        "success": True,
        "object_count": exported_count,
        "objects_with_refs": objects_with_refs,
        "objects_without_refs": objects_without_refs,
        "missing_meshes": missing_meshes,
        "file_path": abs_file_path,
        "file_size": file_size
    }