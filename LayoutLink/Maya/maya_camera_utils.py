"""
LayoutLink Camera Utilities for Maya - VERSION 8.0 FINAL
Handles camera look direction differences between Unreal and Maya
"""

import maya.cmds as cmds
from pxr import Usd, UsdGeom
import mayaUsd.ufe as mayaUsdUfe

__version__ = "8.0-LOOK-DIRECTION-FIX"

def find_all_usd_stages():
    """Find all USD proxy shapes in the scene"""
    proxy_shapes = cmds.ls(type='mayaUsdProxyShape')
    
    stages = []
    for shape in proxy_shapes:
        parents = cmds.listRelatives(shape, parent=True)
        if parents:
            transform = parents[0]
            stages.append({
                'transform': transform,
                'shape': shape
            })
    
    return stages

def create_maya_camera_from_usd(stage_info, camera_prim_path):
    """
    Create a native Maya camera from a USD camera prim.
    VERSION 8.0: Fixes camera look direction difference
    """
    stage_transform = stage_info['transform']
    stage_shape = stage_info['shape']
    
    print(f"\nConverting USD camera: {camera_prim_path}")
    print(f"  Using version: {__version__}")
    
    try:
        # Get the USD stage
        stage = mayaUsdUfe.getStage(f'|{stage_transform}|{stage_shape}')
        
        if not stage:
            print("  ERROR: Could not get USD stage")
            return None
        
        # Get the camera prim
        camera_prim = stage.GetPrimAtPath(camera_prim_path)
        
        if not camera_prim or camera_prim.GetTypeName() != "Camera":
            print(f"  ERROR: Not a camera prim: {camera_prim_path}")
            return None
        
        # === READ USD CAMERA ATTRIBUTES ===
        usd_camera = UsdGeom.Camera(camera_prim)
        
        focal_length = 35.0  # Default in mm
        h_aperture = 36.0 / 25.4  # Default in inches
        v_aperture = 24.0 / 25.4
        near_clip = 10.0
        far_clip = 10000.0
        
        # Unreal exports in cm, detect and convert
        if usd_camera.GetFocalLengthAttr():
            val = usd_camera.GetFocalLengthAttr().Get()
            if val is not None:
                if val < 10:  # Likely cm from Unreal
                    focal_length = val * 10.0  # cm to mm
                else:
                    focal_length = val
                print(f"  Focal: {focal_length}mm")
        
        if usd_camera.GetHorizontalApertureAttr():
            val = usd_camera.GetHorizontalApertureAttr().Get()
            if val is not None:
                if val < 10:  # Likely cm
                    h_aperture = (val * 10.0) / 25.4  # cm to mm to inches
                else:
                    h_aperture = val / 25.4
                print(f"  H-aperture: {h_aperture * 25.4:.1f}mm")
        
        if usd_camera.GetVerticalApertureAttr():
            val = usd_camera.GetVerticalApertureAttr().Get()
            if val is not None:
                if val < 10:  # Likely cm
                    v_aperture = (val * 10.0) / 25.4
                else:
                    v_aperture = val / 25.4
                print(f"  V-aperture: {v_aperture * 25.4:.1f}mm")
        
        if usd_camera.GetClippingRangeAttr():
            val = usd_camera.GetClippingRangeAttr().Get()
            if val is not None:
                near_clip = val[0] * 100.0  # meters to cm
                far_clip = val[1] * 100.0
        
        # === READ TRANSFORMS ===
        xformable = UsdGeom.Xformable(camera_prim)
        time = Usd.TimeCode.Default()
        ops = xformable.GetOrderedXformOps()
        
        usd_translate = [0, 0, 0]
        usd_rotate = [0, 0, 0]
        usd_scale = [1, 1, 1]
        
        for op in ops:
            op_type = op.GetOpType()
            value = op.Get(time)
            
            if value is None:
                continue
            
            if op_type == UsdGeom.XformOp.TypeTranslate:
                usd_translate = list(value)
            elif op_type == UsdGeom.XformOp.TypeRotateXYZ:
                usd_rotate = list(value)
            elif op_type == UsdGeom.XformOp.TypeScale:
                usd_scale = list(value)
        
        print(f"  USD Transform:")
        print(f"    Translate: {usd_translate}")
        print(f"    Rotate: {usd_rotate}")
        
        # === CREATE MAYA CAMERA ===
        camera_name = camera_prim_path.split('/')[-1]
        maya_cam = cmds.camera(name=f"{camera_name}_maya")
        cam_transform = maya_cam[0]
        cam_shape = maya_cam[1]
        
        # Set camera lens attributes
        cmds.setAttr(f"{cam_shape}.focalLength", focal_length)
        cmds.setAttr(f"{cam_shape}.horizontalFilmAperture", h_aperture)
        cmds.setAttr(f"{cam_shape}.verticalFilmAperture", v_aperture)
        cmds.setAttr(f"{cam_shape}.nearClipPlane", near_clip)
        cmds.setAttr(f"{cam_shape}.farClipPlane", far_clip)
        
        # === APPLY TRANSFORMS WITH LOOK DIRECTION FIX ===
        # Parent under stage to inherit Z-up to Y-up conversion
        cmds.parent(cam_transform, stage_transform)
        
        # Apply position (this is correct)
        cmds.setAttr(f"{cam_transform}.translateX", usd_translate[0])
        cmds.setAttr(f"{cam_transform}.translateY", usd_translate[1])
        cmds.setAttr(f"{cam_transform}.translateZ", usd_translate[2])
        
        # Apply rotation with camera look direction compensation
        # Unreal camera looks down +X, Maya looks down -Z
        # This requires a 90Â° Y rotation to align look directions
        cmds.setAttr(f"{cam_transform}.rotateX", usd_rotate[0])
        cmds.setAttr(f"{cam_transform}.rotateY", usd_rotate[1] - 90.0)  # Add 90Â° to align look direction
        cmds.setAttr(f"{cam_transform}.rotateZ", usd_rotate[2])
        
        cmds.setAttr(f"{cam_transform}.scaleX", usd_scale[0])
        cmds.setAttr(f"{cam_transform}.scaleY", usd_scale[1])
        cmds.setAttr(f"{cam_transform}.scaleZ", usd_scale[2])
        
        print(f"âœ“ Created Maya camera: {cam_transform}")
        print(f"  Parent: {stage_transform}")
        print(f"  Applied +90Â° Y rotation for look direction alignment")
        print(f"  Final rotation: ({usd_rotate[0]:.1f}, {usd_rotate[1] + 90:.1f}, {usd_rotate[2]:.1f})")
        
        return cam_transform
        
    except Exception as e:
        print(f"ERROR creating Maya camera: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_maya_cameras_from_all_usd_stages():
    """Find all USD cameras and create native Maya cameras"""
    print("="*50)
    print(f"Creating Maya Cameras - Version {__version__}")
    print("="*50)
    
    stages = find_all_usd_stages()
    
    if not stages:
        print("No USD stages found")
        return []
    
    print(f"Found {len(stages)} USD stage(s)")
    
    created_cameras = []
    
    for stage_info in stages:
        stage_name = stage_info['transform']
        print(f"\nChecking stage: {stage_name}")
        
        stage = mayaUsdUfe.getStage(f"|{stage_info['transform']}|{stage_info['shape']}")
        
        if not stage:
            print("  Could not access stage")
            continue
        
        for prim in stage.TraverseAll():
            if prim.GetTypeName() == "Camera":
                camera_path = str(prim.GetPath())
                print(f"  Found USD camera: {camera_path}")
                
                maya_cam = create_maya_camera_from_usd(stage_info, camera_path)
                
                if maya_cam:
                    created_cameras.append(maya_cam)
    
    print("\n" + "=" * 50)
    print(f"Created {len(created_cameras)} Maya camera(s)")
    print("=" * 50)
    
    return created_cameras
