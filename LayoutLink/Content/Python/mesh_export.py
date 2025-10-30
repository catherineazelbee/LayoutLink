"""
LayoutLink Mesh Library Exporter
Exports static meshes as individual USD assets for the asset library
"""

import unreal
import os

def get_all_static_meshes():
    """Find all static meshes in the project"""
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
    
    # Get all static mesh assets
    meshes = asset_registry.get_assets_by_class("StaticMesh", True)
    
    return [mesh.get_asset() for mesh in meshes]

def sanitize_filename(name):
    """Clean up asset name for filesystem"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name

def export_mesh_to_usd(static_mesh, output_dir):
    """
    Export a single static mesh to USD.
    
    Args:
        static_mesh: The StaticMesh asset
        output_dir: Directory to save USD files
        
    Returns:
        str: Path to exported file, or None if failed
    """
    mesh_name = static_mesh.get_name()
    safe_name = sanitize_filename(mesh_name)
    output_path = os.path.join(output_dir, f"{safe_name}.usda")
    
    unreal.log(f"Exporting mesh: {mesh_name}")
    
    # Create export task
    task = unreal.AssetExportTask()
    task.object = static_mesh
    task.filename = output_path
    task.automated = True
    task.replace_identical = True
    task.prompt = False
    
    # Configure USD export options for static meshes
    options = unreal.StaticMeshExporterUSDOptions()
    options.stage_options.meters_per_unit = 0.01  # cm to meters (Unreal units)
    options.stage_options.up_axis = unreal.UsdUpAxis.Z_AXIS
    
    task.options = options
    
    # Run export
    success = unreal.Exporter.run_asset_export_task(task)
    
    if success:
        unreal.log(f"  ✓ Exported to: {output_path}")
        return output_path
    else:
        unreal.log_warning(f"  ✗ Failed to export: {mesh_name}")
        return None

def export_mesh_library(output_dir, selected_only=False):
    """
    Export static meshes to create a USD asset library.
    
    Args:
        output_dir: Directory where USD mesh files will be saved
        selected_only: If True, only export meshes used by selected actors
        
    Returns:
        dict: Export results
    """
    unreal.log("=== Mesh Library Export Starting ===")
    unreal.log(f"Output directory: {output_dir}")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        unreal.log(f"Created directory: {output_dir}")
    
    # Determine which meshes to export
    meshes_to_export = []
    
    if selected_only:
        # Get meshes from selected actors
        editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        selected_actors = editor_subsystem.get_selected_level_actors()
        
        if not selected_actors:
            unreal.log_warning("No actors selected")
            return {"success": False, "error": "No actors selected"}
        
        # Extract unique meshes from selected actors
        unique_meshes = set()
        for actor in selected_actors:
            components = actor.get_components_by_class(unreal.StaticMeshComponent)
            for comp in components:
                if comp.static_mesh:
                    unique_meshes.add(comp.static_mesh)
        
        meshes_to_export = list(unique_meshes)
        unreal.log(f"Found {len(meshes_to_export)} unique mesh(es) in selection")
        
    else:
        # Export all static meshes in project
        meshes_to_export = get_all_static_meshes()
        unreal.log(f"Found {len(meshes_to_export)} mesh(es) in project")
    
    if not meshes_to_export:
        unreal.log_warning("No meshes to export")
        return {"success": False, "error": "No meshes found"}
    
    # Export each mesh
    exported_meshes = []
    failed_meshes = []
    
    for mesh in meshes_to_export:
        result = export_mesh_to_usd(mesh, output_dir)
        
        if result:
            exported_meshes.append({
                "name": mesh.get_name(),
                "path": result,
                "asset_path": mesh.get_path_name()
            })
        else:
            failed_meshes.append(mesh.get_name())
    
    # Summary
    unreal.log("=" * 50)
    unreal.log(f"Export complete:")
    unreal.log(f"  ✓ Success: {len(exported_meshes)} meshes")
    if failed_meshes:
        unreal.log(f"  ✗ Failed: {len(failed_meshes)} meshes")
    unreal.log("=" * 50)
    
    return {
        "success": True,
        "exported_count": len(exported_meshes),
        "failed_count": len(failed_meshes),
        "exported_meshes": exported_meshes,
        "failed_meshes": failed_meshes,
        "output_dir": output_dir
    }

def export_selected_meshes_library(output_dir):
    """
    Convenience function: Export only meshes used by selected actors.
    """
    return export_mesh_library(output_dir, selected_only=True)

def export_all_meshes_library(output_dir):
    """
    Convenience function: Export all meshes in the project.
    WARNING: This can take a long time for large projects!
    """
    return export_mesh_library(output_dir, selected_only=False)