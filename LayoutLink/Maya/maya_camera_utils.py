# maya_camera_utils.py
# LayoutLink Camera Utilities for Maya — BASIS-VECTOR MATCH (clean)
# Creates native Maya cameras that match the USD proxy view by using the USD
# camera's basis vectors (forward/up) and composing under the proxy parent.

import maya.cmds as cmds
from pxr import Usd, UsdGeom, Gf
import mayaUsd.ufe as mayaUsdUfe

__version__ = "15.1-BASIS-VEC"

# ----- helpers -----

def _active_model_panel():
    for p in cmds.getPanel(vis=True) or []:
        if cmds.getPanel(to=p) == "modelPanel":
            return p
    return None

def _panel_switch_to_persp():
    panel = _active_model_panel()
    if not panel:
        return (None, None)
    try:
        cur = cmds.modelEditor(panel, q=True, camera=True)
        if cmds.objExists("persp"):
            cmds.modelEditor(panel, e=True, camera="persp")
        return (panel, cur)
    except Exception:
        return (None, None)

def _panel_restore(panel, cam):
    if panel and cam and cmds.objExists(cam):
        try:
            cmds.modelEditor(panel, e=True, camera=cam)
        except Exception:
            pass

def _maya_world_mtx(node):
    """World matrix as Gf.Matrix4d (via .worldMatrix[0])."""
    vals = cmds.getAttr(node + ".worldMatrix[0]")
    if isinstance(vals, (list, tuple)) and len(vals) == 1 and isinstance(vals[0], (list, tuple)):
        vals = vals[0]
    if not isinstance(vals, (list, tuple)) or len(vals) != 16:
        raise RuntimeError(f"Unexpected worldMatrix for {node}: {vals}")
    rows = (
        (vals[0],  vals[1],  vals[2],  vals[3]),
        (vals[4],  vals[5],  vals[6],  vals[7]),
        (vals[8],  vals[9],  vals[10], vals[11]),
        (vals[12], vals[13], vals[14], vals[15]),
    )
    return Gf.Matrix4d(rows)

def _flatten(m):
    return [
        m[0][0], m[0][1], m[0][2], m[0][3],
        m[1][0], m[1][1], m[1][2], m[1][3],
        m[2][0], m[2][1], m[2][2], m[2][3],
        m[3][0], m[3][1], m[3][2], m[3][3],
    ]

def _usd_world_mtx(prim):
    return UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())

def _normalize(v):
    l = v.GetLength()
    return v if l == 0 else v / l

# ----- main API -----

def find_all_usd_stages():
    stages = []
    for shape in cmds.ls(type="mayaUsdProxyShape") or []:
        parents = cmds.listRelatives(shape, parent=True) or []
        if parents:
            stages.append({"transform": parents[0], "shape": shape})
    return stages

def create_maya_camera_from_usd(stage_info, camera_prim_path):
    """Create a native Maya camera that matches the USD proxy view."""
    stage_xf = stage_info["transform"]
    stage_shape = stage_info["shape"]

    print(f"\nConverting USD camera: {camera_prim_path}")
    print(f"  Using version: {__version__}")

    panel, old_cam = _panel_switch_to_persp()
    try:
        stage = mayaUsdUfe.getStage(f"|{stage_xf}|{stage_shape}")
        if not stage:
            print("  ERROR: Could not get USD stage")
            return None

        prim = stage.GetPrimAtPath(camera_prim_path)
        if not prim or prim.GetTypeName() != "Camera":
            print(f"  ERROR: Not a camera prim: {camera_prim_path}")
            return None

        ucam = UsdGeom.Camera(prim)

        # ---- Lens (USD mm) -> Maya (mm/inches/cm) ----
        focal_mm = ucam.GetFocalLengthAttr().Get() or 35.0
        hap_mm   = ucam.GetHorizontalApertureAttr().Get() or 36.0
        vap_mm   = ucam.GetVerticalApertureAttr().Get()   or 24.0
        near_m, far_m = (0.1, 10000.0)
        cr = ucam.GetClippingRangeAttr().Get()
        if cr: near_m, far_m = cr

        hap_in = hap_mm / 25.4
        vap_in = vap_mm / 25.4
        near_cm = near_m * 100.0
        far_cm  = far_m * 100.0

        # ---- Create Maya camera ----
        cam_name = camera_prim_path.split("/")[-1] + "_maya"
        cam = cmds.camera(name=cam_name)
        cam_xf, cam_shape = cam[0], cam[1]
        cmds.setAttr(f"{cam_shape}.focalLength", focal_mm)
        cmds.setAttr(f"{cam_shape}.horizontalFilmAperture", hap_in)
        cmds.setAttr(f"{cam_shape}.verticalFilmAperture",   vap_in)
        cmds.setAttr(f"{cam_shape}.nearClipPlane", near_cm)
        cmds.setAttr(f"{cam_shape}.farClipPlane",  far_cm)

        # ---- Build USD camera world from COLUMN vectors ----
        W = _usd_world_mtx(prim)

        origin = W.ExtractTranslation()  # Gf.Vec3d
        xcol = Gf.Vec3d(W[0][0], W[1][0], W[2][0])  # +X
        ycol = Gf.Vec3d(W[0][1], W[1][1], W[2][1])  # +Y (up)
        zcol = Gf.Vec3d(W[0][2], W[1][2], W[2][2])  # +Z

        fwd   = _normalize(-zcol)                     # cameras look down -Z
        up    = _normalize(ycol)
        right = _normalize(Gf.Cross(fwd, up))
        up    = _normalize(Gf.Cross(right, fwd))      # re-orthonormalize

        world_from_usd_cam = Gf.Matrix4d(
            ( right[0], right[1], right[2], 0.0 ),
            ( up[0],    up[1],    up[2],    0.0 ),
            ( -fwd[0],  -fwd[1],  -fwd[2],  0.0 ),
            ( origin[0], origin[1], origin[2], 1.0 )
        )

        # ---- Compose under proxy parent (which already has -90 X for Y-up view) ----
        cmds.parent(cam_xf, stage_xf)

        parent_world = _maya_world_mtx(stage_xf)
        local_mtx    = parent_world.GetInverse() * world_from_usd_cam

        # Optional LOCAL yaw tweak about the camera pivot (default 0)
        YAW_OFFSET_DEG = 0.0  # set to -90.0 or your measured -91.041794 if needed
        if abs(YAW_OFFSET_DEG) > 1e-6:
            ry = Gf.Matrix4d(1.0)
            ry.SetRotate(Gf.Rotation(Gf.Vec3d(0,1,0), YAW_OFFSET_DEG))
            tx, ty, tz = local_mtx[3][0], local_mtx[3][1], local_mtx[3][2]
            rot_only = Gf.Matrix4d(local_mtx); rot_only[3][0]=rot_only[3][1]=rot_only[3][2]=0.0
            rot_only = rot_only * ry
            rot_only[3][0], rot_only[3][1], rot_only[3][2] = tx, ty, tz
            local_mtx = rot_only

        cmds.xform(cam_xf, m=_flatten(local_mtx), ws=False)  # apply LOCAL under parent
        if cmds.objExists(f"{cam_xf}.rotateAxis"):
            cmds.setAttr(f"{cam_xf}.rotateAxis", 0, 0, 0)

        print(f"  Lens: {focal_mm:.2f}mm, aperture: {hap_mm:.2f}×{vap_mm:.2f}mm")
        print(f"  Clip: {near_cm:.2f}–{far_cm:.2f} cm")
        print(f"✓ Created Maya camera: {cam_xf} (parent {stage_xf})")
        return cam_xf

    except Exception as e:
        print(f"ERROR creating Maya camera: {e}")
        import traceback; traceback.print_exc()
        return None
    finally:
        _panel_restore(panel, old_cam)

def create_maya_cameras_from_all_usd_stages():
    print("=" * 60)
    print(f"Creating Maya Cameras - Version {__version__}")
    print("=" * 60)

    stages = find_all_usd_stages()
    if not stages:
        print("No USD stages found")
        return []

    created = []
    for info in stages:
        stage = mayaUsdUfe.getStage(f"|{info['transform']}|{info['shape']}")
        if not stage:
            continue
        for prim in stage.TraverseAll():
            if prim.GetTypeName() == "Camera":
                path = str(prim.GetPath())
                print(f"  USD camera: {path}")
                cam = create_maya_camera_from_usd(info, path)
                if cam:
                    created.append(cam)

    print("\n" + "=" * 60)
    print(f"Created {len(created)} Maya camera(s)")
    print("=" * 60)
    return created