# maya_layout_import.py
# LayoutLink USD Import for Maya — proxy import with optional up-axis alignment.
# - Loads a mayaUsdProxyShape, sets filePath and primPath=/World.
# - Draws all USD "purposes".
# - If the USD stage is Z-up (Unreal), rotates the parent transform -90° in X so it
#   looks upright relative to Maya's Y-up grid (like a manual "Import as Maya" would).

import os
import maya.cmds as cmds


def _get_stage_up_axis(file_path):
    try:
        from pxr import Usd, UsdGeom

        stage = Usd.Stage.Open(file_path)
        # Returns 'Y' or 'Z'
        return UsdGeom.GetStageUpAxis(stage)
    except Exception:
        return None


def import_usd_from_unreal(file_path, align_to_maya_up=True):
    print("=== Layout Import Starting ===")
    print(f"File: {file_path}")

    # NEW: Detect if this is a layered file
    import simple_layers
    layer_type = simple_layers.get_layer_type(file_path)
    print(f"Layer type: {layer_type}")

    if layer_type == "override":
        base_path = simple_layers.get_base_from_override(file_path)
        if base_path:
            print(f"  Base layer: {base_path}")
            print("  Importing layered USD (base + override)")

    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
        try:
            cmds.loadPlugin("mayaUsdPlugin")
            print("✓ Loaded mayaUsd plugin")
        except Exception:
            print("ERROR: Could not load mayaUsd plugin")
            return {"success": False, "error": "mayaUsd plugin not available"}

    if not os.path.exists(file_path):
        print("ERROR: File not found")
        return {"success": False, "error": "File not found"}

    try:
        up_axis = _get_stage_up_axis(file_path)  # 'Y' or 'Z' (or None on failure)
        print(f"Stage upAxis: {up_axis}")

        base = os.path.splitext(os.path.basename(file_path))[0]
        # Create a transform parent so we can rotate to match Maya's Y-up if desired
        xform = cmds.createNode("transform", name=f"UnrealLayout_{base}")
        shape = cmds.createNode("mayaUsdProxyShape", parent=xform)

        # Point the proxy to the composed root
        cmds.setAttr(f"{shape}.filePath", file_path, type="string")
        cmds.setAttr(f"{shape}.primPath", "/World", type="string")

        # Ensure all draw purposes are enabled (so nothing is hidden by purpose)
        for attr in ("drawRenderPurpose", "drawProxyPurpose", "drawGuidePurpose"):
            if cmds.objExists(f"{shape}.{attr}"):
                cmds.setAttr(f"{shape}.{attr}", 1)

        # Align Z-up USD stages to Maya's Y-up viewport (visual convenience)
        if align_to_maya_up and (up_axis is None or str(up_axis).upper() == "Z"):
            # Rotate -90° around X so USD Z becomes Maya Y
            try:
                cmds.setAttr(f"{xform}.rotateX", -90.0)
                print("Applied -90° X on parent to match Maya Y-up view")
            except Exception as e:
                print(f"Note: Could not set rotateX on {xform}: {e}")

        print(f"✓ Created USD Stage: {xform}")
        print(f"  Shape node: {shape}")
        print("=== Import Complete ===")

        return {
            "success": True,
            "stage_transform": xform,
            "stage_shape": shape,
            "aligned_to_maya_up": bool(align_to_maya_up),
            "stage_up_axis": up_axis,
        }

    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def import_with_file_dialog(align_to_maya_up=True):
    file_path = cmds.fileDialog2(
        fileFilter="USD Files (*.usd *.usda *.usdc);;All Files (*.*)",
        dialogStyle=2,
        fileMode=1,
        caption="Import USD Layout from Unreal",
        startingDirectory="C:/SharedUSD/layouts/unreal_layouts",
    )
    if file_path:
        return import_usd_from_unreal(file_path[0], align_to_maya_up=align_to_maya_up)
    else:
        print("Import cancelled")
        return {"success": False, "error": "Cancelled"}
