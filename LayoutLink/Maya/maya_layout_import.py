"""
LayoutLink USD Import for Maya
Imports Unreal layouts as USD Stages (NOT File→Import!)
"""

import maya.cmds as cmds
import os

def import_usd_from_unreal(file_path):
    """
    Import USD layout from Unreal as a USD Stage.
    
    CRITICAL: Uses mayaUsdCreateStageFromFile, NOT File→Import!
    File→Import converts to Maya data and flattens references.
    USD Stage preserves references and USD composition.
    
    Args:
        file_path (str): Path to USD layout file from Unreal
        
    Returns:
        dict: Import result with success status
    """
    print("=== Layout Import Starting ===")
    print(f"File: {file_path}")
    
    # Check file exists
    if not os.path.exists(file_path):
        print("ERROR: File not found")
        return {"success": False, "error": "File not found"}
    
    try:
        # Import as USD Stage (NOT File→Import!)
        # This preserves USD references and composition
        stage_nodes = cmds.mayaUsdCreateStageFromFile(
            filePath=file_path,
            primPath='/'
        )
        
        if not stage_nodes:
            print("ERROR: Failed to create USD stage")
            return {"success": False, "error": "Failed to create stage"}
        
        # stage_nodes returns [transform, shape]
        stage_transform = stage_nodes[0]
        stage_shape = stage_nodes[1]
        
        # Rename for clarity
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        stage_transform = cmds.rename(stage_transform, f"UnrealLayout_{base_name}")
        
        print(f"✓ Created USD Stage: {stage_transform}")
        print(f"  Shape node: {stage_shape}")
        
        # Try to read metadata
        try:
            from pxr import Sdf
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
        except:
            pass  # Metadata is optional
        
        print("=== Import Complete ===")
        
        return {
            "success": True,
            "stage_transform": stage_transform,
            "stage_shape": stage_shape
        }
        
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
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
        caption="Import USD Layout from Unreal"
    )
    
    if file_path:
        return import_usd_from_unreal(file_path[0])
    else:
        print("Import cancelled")
        return {"success": False, "error": "Cancelled"}