"""
LayoutLink Mesh Library Exporter for Maya
Exports Maya meshes as individual USD assets using direct USD Python API
(bypasses broken mayaUSDExport)
"""

import maya.cmds as cmds
import os
from pxr import Usd, UsdGeom, Sdf, Vt

def get_all_meshes():
    """Find all mesh transforms in the scene"""
    all_meshes = cmds.ls(type='mesh', long=True)
    transforms = []
    for mesh in all_meshes:
        if cmds.getAttr(mesh + '.intermediateObject'):
            continue
        parents = cmds.listRelatives(mesh, parent=True, fullPath=True)
        if parents:
            transforms.append(parents[0])
    return list(set(transforms))

def sanitize_filename(name):
    """Clean up name for filesystem"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    name = name.split(':')[-1]
    name = name.split('|')[-1]
    return name

def export_mesh_to_usd(mesh_transform, output_dir):
    """
    Export a single Maya mesh to USD using direct USD Python API.
    
    Args:
        mesh_transform: Maya transform node containing mesh
        output_dir: Directory to save USD files
        
    Returns:
        str: Path to exported file, or None if failed
    """
    mesh_name = cmds.ls(mesh_transform, shortNames=True)[0]
    safe_name = sanitize_filename(mesh_name)
    output_path = os.path.join(output_dir, f"{safe_name}.usda")
    
    print(f"Exporting mesh: {mesh_name}")
    
    try:
        # Get the mesh shape node
        shapes = cmds.listRelatives(mesh_transform, shapes=True, noIntermediate=True, fullPath=True)
        if not shapes:
            print(f"  No shape found for {mesh_name}")
            return None
        
        shape_node = shapes[0]
        
        # Create USD stage
        stage = Usd.Stage.CreateNew(output_path)
        
        # Set up axis and units (Maya is Y-up, cm)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 0.01)
        
        # Create mesh prim
        mesh_prim = UsdGeom.Mesh.Define(stage, f"/{safe_name}")
        
        # Get Maya mesh data
        # VERTICES
        vtx_count = cmds.polyEvaluate(shape_node, vertex=True)
        points = []
        for i in range(vtx_count):
            pos = cmds.xform(f"{shape_node}.vtx[{i}]", q=True, worldSpace=True, translation=True)
            points.append((pos[0], pos[1], pos[2]))
        
        mesh_prim.GetPointsAttr().Set(points)
        
        # FACE VERTEX COUNTS (how many vertices per face)
        face_count = cmds.polyEvaluate(shape_node, face=True)
        face_vertex_counts = []
        for i in range(face_count):
            vtx_in_face = cmds.polyInfo(f"{shape_node}.f[{i}]", faceToVertex=True)[0]
            # Parse result like "FACE     0:      0 1 2 3\n"
            vtx_list = vtx_in_face.split(':')[1].strip().split()
            face_vertex_counts.append(len(vtx_list))
        
        mesh_prim.GetFaceVertexCountsAttr().Set(face_vertex_counts)
        
        # FACE VERTEX INDICES
        face_vertex_indices = []
        for i in range(face_count):
            vtx_in_face = cmds.polyInfo(f"{shape_node}.f[{i}]", faceToVertex=True)[0]
            vtx_list = vtx_in_face.split(':')[1].strip().split()
            face_vertex_indices.extend([int(v) for v in vtx_list])
        
        mesh_prim.GetFaceVertexIndicesAttr().Set(face_vertex_indices)
        
        # NORMALS
        normals = []
        for i in range(face_count):
            for j in range(face_vertex_counts[i]):
                normal = cmds.polyNormalPerVertex(
                    f"{shape_node}.vtxFace[{face_vertex_indices[sum(face_vertex_counts[:i]) + j]}][{i}]",
                    q=True, xyz=True
                )
                normals.append((normal[0], normal[1], normal[2]))
        
        mesh_prim.GetNormalsAttr().Set(normals)
        mesh_prim.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
        
        # UVs (if they exist)
        uv_sets = cmds.polyUVSet(shape_node, q=True, allUVSets=True)
        if uv_sets:
            uv_set = uv_sets[0]  # Use first UV set
            uvs = cmds.polyEditUV(f"{shape_node}.map[*]", q=True, uValue=True, vValue=True)
            
            if uvs and len(uvs) > 0:
                # Interleave U and V into (u,v) pairs
                uv_pairs = [(uvs[i], uvs[i+1]) for i in range(0, len(uvs), 2)]
                
                # Create primvar for UVs - must use GetPrim() not the mesh object directly
                uv_primvar = UsdGeom.PrimvarsAPI(mesh_prim).CreatePrimvar(
                    "st", 
                    Sdf.ValueTypeNames.TexCoord2fArray,
                    UsdGeom.Tokens.faceVarying
                )
                uv_primvar.Set(uv_pairs)
        
        # Set subdivision scheme
        mesh_prim.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)
        
        # Set as default prim
        stage.SetDefaultPrim(mesh_prim.GetPrim())
        
        # Save the stage
        stage.GetRootLayer().Save()
        
        # Verify file size
        file_size = os.path.getsize(output_path)
        print(f"  ✓ Exported to: {output_path} ({file_size} bytes)")
        
        if file_size > 1000:
            print(f"  ✓✓ SUCCESS! File has geometry data!")
        
        return output_path
        
    except Exception as e:
        print(f"  ✗ Failed to export {mesh_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def export_mesh_library(output_dir, selected_only=False):
    """
    Export Maya meshes to create a USD asset library.
    
    Args:
        output_dir: Directory where USD mesh files will be saved
        selected_only: If True, only export selected meshes
        
    Returns:
        dict: Export results
    """
    print("=== Mesh Library Export Starting ===")
    print(f"Output directory: {output_dir}")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    # Determine which meshes to export
    if selected_only:
        selection = cmds.ls(selection=True, long=True, transforms=True)
        meshes_to_export = []
        
        for obj in selection:
            shapes = cmds.listRelatives(obj, shapes=True, noIntermediate=True)
            if shapes:
                for shape in shapes:
                    if cmds.nodeType(shape) == 'mesh':
                        meshes_to_export.append(obj)
                        break
        
        if not meshes_to_export:
            print("No mesh objects selected")
            return {"success": False, "error": "No mesh objects selected"}
        
        print(f"Found {len(meshes_to_export)} mesh(es) in selection")
    else:
        meshes_to_export = get_all_meshes()
        print(f"Found {len(meshes_to_export)} mesh(es) in scene")
    
    if not meshes_to_export:
        print("No meshes to export")
        return {"success": False, "error": "No meshes found"}
    
    # Export each mesh
    exported_meshes = []
    failed_meshes = []
    
    for mesh in meshes_to_export:
        result = export_mesh_to_usd(mesh, output_dir)
        
        if result:
            mesh_name = cmds.ls(mesh, shortNames=True)[0]
            exported_meshes.append({
                "name": mesh_name,
                "path": result
            })
        else:
            failed_meshes.append(cmds.ls(mesh, shortNames=True)[0])
    
    # Summary
    print("=" * 50)
    print(f"Export complete:")
    print(f"  Success: {len(exported_meshes)} meshes")
    if failed_meshes:
        print(f"  Failed: {len(failed_meshes)} meshes")
    print("=" * 50)
    
    return {
        "success": True,
        "exported_count": len(exported_meshes),
        "failed_count": len(failed_meshes),
        "exported_meshes": exported_meshes,
        "failed_meshes": failed_meshes,
        "output_dir": output_dir
    }

def export_selected_meshes_library(output_dir):
    """Convenience function: Export only selected meshes."""
    return export_mesh_library(output_dir, selected_only=True)

def export_all_meshes_library(output_dir):
    """Convenience function: Export all meshes in the scene."""
    return export_mesh_library(output_dir, selected_only=False)