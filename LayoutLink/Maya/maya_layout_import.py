"""
LayoutLink USD Import for Maya
Imports Unreal layouts as USD Stages (NOT File→Import!)
Automatically handles Z-up to Y-up conversion
"""

import maya.cmds as cmds
import os

def import_usd_from_unreal(file_path):
    """
    Import USD layout from Unreal as a USD Stage.
    
    CRITICAL: Uses proxy shape creation, NOT File→Import!
    File→Import converts to Maya data and flattens references.
    USD Stage preserves references and USD composition.
    
    Automatically rotates Z-up stages (Unreal) to display correctly in Y-up Maya.
    
    Args:
        file_path (str): Path to USD layout file from Unreal
        
    Returns:
        dict: Import result with success status
    """
    print("=== Layout Import Starting ===")
    print(f"File: {file_path}")
    
    # Load mayaUsd plugin if not loaded
    if not cmds.pluginInfo('mayaUsdPlugin', query=True, loaded=True):
        try:
            cmds.loadPlugin('mayaUsdPlugin')
            print("✓ Loaded mayaUsd plugin")
        except:
            print("ERROR: Could not load mayaUsd plugin")
            return {"success": False, "error": "mayaUsd plugin not available"}
    
    # Check file exists
    if not os.path.exists(file_path):
        print("ERROR: File not found")
        return {"success": False, "error": "File not found"}
    
    try:
        from pxr import Usd, UsdGeom, Sdf
        
        # STEP 1: Check the up axis of the incoming file
        temp_stage = Usd.Stage.Open(file_path)
        stage_up_axis = UsdGeom.GetStageUpAxis(temp_stage)
        is_z_up = (stage_up_axis == UsdGeom.Tokens.z)
        
        print(f"File up axis: {stage_up_axis}")
        print(f"Maya up axis: Y")
        
        if is_z_up:
            print("⚠ Z-up file detected - will apply rotation for Maya")
        
        # STEP 2: Create transform node
        transform_node = cmds.createNode('transform', name='UnrealLayout_temp')
        
        # STEP 3: Create USD proxy shape under it
        shape_node = cmds.createNode('mayaUsdProxyShape', parent=transform_node)
        
        # STEP 4: Set the USD file path
        cmds.setAttr(f'{shape_node}.filePath', file_path, type='string')
        
        # STEP 5: Rename for clarity
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        transform_node = cmds.rename(transform_node, f"UnrealLayout_{base_name}")
        
        # STEP 6: Apply rotation correction if Z-up
        if is_z_up:
            # Z-up to Y-up: Rotate -90 degrees around X axis
            cmds.setAttr(f'{transform_node}.rotateX', -90)
            print("✓ Applied Z-up to Y-up conversion (rotated -90° around X)")
        
        print(f"✓ Created USD Stage: {transform_node}")
        print(f"  Shape node: {shape_node}")
        
        # STEP 7: Try to read metadata
        try:
            import maya_metadata_utils
            
            layer = Sdf.Layer.FindOrOpen(file_path)
            if layer:
                metadata = maya_metadata_utils.read_layoutlink_metadata(layer)
                if metadata:
                    print("\n=== Layout Info ===")
                    print(f"From: {metadata.get('layoutlink_app', 'Unknown')}")
                    print(f"Artist: {metadata.get('layoutlink_artist', 'Unknown')}")
                    print(f"Date: {metadata.get('layoutlink_timestamp', 'Unknown')}")
                    print("=" * 50)
        except Exception as e:
            print(f"Note: Could not read metadata: {e}")
        
        print("=== Import Complete ===")
        
        return {
            "success": True,
            "stage_transform": transform_node,
            "stage_shape": shape_node,
            "applied_rotation": is_z_up
        }
        
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def import_with_file_dialog():
    """
    Show file dialog and import selected USD file.
    Convenience function for UI buttons.
    """
    file_path = cmds.fileDialog2(
        fileFilter="USD Files (*.usd *.usda *.usdc);;All Files (*.*)",
        dialogStyle=2,
        fileMode=1,  # Single file
        caption="Import USD Layout from Unreal",
        startingDirectory="C:/SharedUSD/layouts/unreal_layouts"
    )
    
    if file_path:
        return import_usd_from_unreal(file_path[0])
    else:
        print("Import cancelled")
        return {"success": False, "error": "Cancelled"}