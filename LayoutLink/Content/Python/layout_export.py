# layout_export.py
# Cleaned: parent Xform + untyped /Geo reference for meshes, proper cameras, Fix A TRS.

import os
import unreal
import metadata_utils

def _sanitize(name: str) -> str:
    bad = '<>:"/\\|?*. '
    for ch in bad:
        name = name.replace(ch, '_')
    return name

def export_selected_to_usd(file_path: str, asset_library_dir: str):
    unreal.log("=== Layout Export Starting ===")
    unreal.log(f"Layout file: {file_path}")
    unreal.log(f"Asset library: {asset_library_dir}")

    editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected = editor_subsystem.get_selected_level_actors()
    if not selected:
        unreal.log_warning("No actors selected")
        return _write_empty_stage(file_path)

    try:
        from pxr import Usd, UsdGeom, Sdf, Gf
    except Exception:
        unreal.log_error("USD Python modules not available")
        return {"success": False, "error": "USD not available"}

    abs_out = os.path.abspath(file_path)
    os.makedirs(os.path.dirname(abs_out), exist_ok=True)
    if os.path.exists(abs_out):
        try:
            os.remove(abs_out)
        except Exception as e:
            unreal.log_warning(f"Could not remove existing file: {e}")

    stage = Usd.Stage.CreateNew(abs_out)
    if not stage:
        unreal.log_error("Failed to create USD stage")
        return {"success": False, "error": "Could not create stage"}

    # Unreal world: Z-up, centimeters
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)

    # Root/default prim
    world_x = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world_x.GetPrim())

    exported_count = 0
    actors_with_refs = 0
    actors_without_refs = 0
    cameras_exported = 0
    missing_meshes = []

    lib_exists = os.path.isdir(asset_library_dir)

    for actor in selected:
        label = actor.get_actor_label()
        nice = _sanitize(label)
        unreal.log(f"Processing: {label}")
        cls_name = actor.get_class().get_name()
        prim_path = f"/World/{nice}"

        # Get TRS from actor
        xf = actor.get_actor_transform()
        loc = xf.translation
        rot = xf.rotation.rotator()  # Roll=X, Pitch=Y, Yaw=Z (deg)
        scl = xf.scale3d

        if cls_name in ("CineCameraActor", "CameraActor"):
           # --- CAMERA (matrix-based, vector-accurate) ---
            cam = UsdGeom.Camera.Define(stage, prim_path)
            cam_comp = actor.get_component_by_class(unreal.CameraComponent)
            if cam_comp:
                try:
                    focal_mm = float(cam_comp.get_editor_property("current_focal_length"))
                    filmback  = cam_comp.get_editor_property("filmback")
                    sensor_w_mm = float(filmback.sensor_width)
                    sensor_h_mm = float(filmback.sensor_height)
                    cam.GetFocalLengthAttr().Set(focal_mm)
                    cam.GetHorizontalApertureAttr().Set(sensor_w_mm)
                    cam.GetVerticalApertureAttr().Set(sensor_h_mm)
                    cam.GetClippingRangeAttr().Set((0.1, 10000.0))  # meters
                    unreal.log(f"  Camera mm: focal={focal_mm:.2f}, sensor={sensor_w_mm:.2f}x{sensor_h_mm:.2f}")
                except Exception as e:
                    unreal.log_warning(f"  Could not read camera props: {e}")

            # Build camera world transform from UE basis vectors (world space)
            from pxr import UsdGeom, Gf

            # UE world-space basis
            pos_ue = actor.get_actor_location()
            fwd_ue = actor.get_actor_forward_vector()  # +X
            right_ue = actor.get_actor_right_vector()  # +Y
            up_ue = actor.get_actor_up_vector()        # +Z

            # Convert UE (LH) -> USD (RH) by flipping Y on all vectors
            def V(v): return Gf.Vec3d(float(v.x), -float(v.y), float(v.z))
            P_usd = V(pos_ue)
            F_usd = V(fwd_ue)     # forward
            R_usd = V(right_ue)   # right
            U_usd = V(up_ue)      # up

            # USD/Maya cameras look down -Z.
            # Construct world matrix with ROWS = [right; up; -forward; translation]
            R = Gf.Vec3d(R_usd).GetNormalized()
            U = Gf.Vec3d(U_usd).GetNormalized()
            F = Gf.Vec3d(F_usd).GetNormalized()

            world_from_cam = Gf.Matrix4d(
                ( R[0], R[1], R[2], 0.0 ),
                ( U[0], U[1], U[2], 0.0 ),
                ( -F[0], -F[1], -F[2], 0.0 ),
                ( P_usd[0], P_usd[1], P_usd[2], 1.0 )
            )

            # Author a single transform op to avoid Euler-order pitfalls
            xformable = UsdGeom.Xformable(cam.GetPrim())
            xformable.ClearXformOpOrder()
            op = xformable.AddTransformOp()
            op.Set(world_from_cam)

            cameras_exported += 1
            exported_count   += 1
            continue


        # --- MESH ACTOR ---
        # Parent Xform holds TRS
        parent_xform = UsdGeom.Xform.Define(stage, prim_path).GetPrim()

        # Untyped child prim carries the reference so the Mesh type flows through
        ref_prim_path = f"{prim_path}/Geo"   # /World/<Name>/Geo
        ref_prim = stage.GetPrimAtPath(ref_prim_path)
        if not ref_prim:
            ref_prim = stage.OverridePrim(ref_prim_path)  # no type!

        mesh_usd_path = None
        static_mesh = None

        comps = actor.get_components_by_class(unreal.StaticMeshComponent)
        if comps:
            smc = comps[0]
            static_mesh = smc.static_mesh
            if static_mesh:
                mesh_name = _sanitize(static_mesh.get_name())
                mesh_file = f"{mesh_name}.usda"
                mesh_full = os.path.join(asset_library_dir, mesh_file)
                if lib_exists and os.path.exists(mesh_full):
                    abs_mesh = os.path.abspath(mesh_full).replace('\\', '/')
                    refs = ref_prim.GetReferences()
                    refs.ClearReferences()
                    refs.AddReference(abs_mesh)
                    mesh_usd_path = abs_mesh
                    actors_with_refs += 1
                    unreal.log(f"  Mesh ref (ABS) → {abs_mesh}")
                else:
                    if lib_exists:
                        unreal.log_warning(f"  Mesh USD not found in library: {mesh_file}")
                    missing_meshes.append(mesh_name)

        if not mesh_usd_path:
            actors_without_refs += 1

        # Optional debug metadata on the parent
        if static_mesh:
            parent_xform.CreateAttribute("unreal:assetPath", Sdf.ValueTypeNames.String).Set(static_mesh.get_path_name())
            parent_xform.CreateAttribute("unreal:meshName", Sdf.ValueTypeNames.String).Set(static_mesh.get_name())

       # TRS on the PARENT Xform with UE(LH) -> USD(RH) conversion
        from pxr import UsdGeom, Gf

        xf = actor.get_actor_transform()
        loc = xf.translation
        rot = xf.rotation.rotator()
        scl = xf.scale3d

        usd_loc = Gf.Vec3d(float(loc.x),  float(-loc.y),  float(loc.z))
        usd_rot = (float(rot.roll), float(-rot.pitch), float(-rot.yaw))
        usd_scl = Gf.Vec3f(float(scl.x),  float(scl.y),  float(scl.z))

        UsdGeom.Xformable(parent_xform).ClearXformOpOrder()
        xapi = UsdGeom.XformCommonAPI(parent_xform)
        xapi.SetTranslate(usd_loc)
        xapi.SetRotate(Gf.Vec3f(*usd_rot), UsdGeom.XformCommonAPI.RotationOrderXYZ)
        xapi.SetScale(usd_scl)
        xapi.SetPivot(Gf.Vec3f(0.0, 0.0, 0.0))


        parent_xform.CreateAttribute("unreal:actorLabel", Sdf.ValueTypeNames.String).Set(label)

        unreal.log(f"  TRS → T({loc.x:.2f},{loc.y:.2f},{loc.z:.2f})  "
                   f"R({rot.roll:.2f},{rot.pitch:.2f},{rot.yaw:.2f})  "
                   f"S({scl.x:.3f},{scl.y:.3f},{scl.z:.3f})")

        exported_count += 1

    # Stage-level metadata
    root_layer = stage.GetRootLayer()
    metadata_utils.add_layoutlink_metadata(root_layer, "unreal_export", "Unreal Engine")
    custom = dict(root_layer.customLayerData)
    custom["layoutlink_actors_with_refs"] = actors_with_refs
    custom["layoutlink_actors_without_refs"] = actors_without_refs
    custom["layoutlink_cameras_exported"] = cameras_exported
    custom["layoutlink_asset_library"] = os.path.basename(asset_library_dir or "")
    root_layer.customLayerData = custom

    stage.Save()

    size = os.path.getsize(abs_out)
    unreal.log("=" * 60)
    unreal.log("Export Summary:")
    unreal.log(f"  Actors: {exported_count}")
    unreal.log(f"  With refs: {actors_with_refs}")
    unreal.log(f"  Without refs: {actors_without_refs}")
    unreal.log(f"  Cameras: {cameras_exported}")
    unreal.log(f"  File size: {size} bytes")
    unreal.log("=" * 60)
    unreal.log(f"Saved: {abs_out}")
    unreal.log("=== Layout Export Complete ===")

    return {
        "success": True,
        "actor_count": exported_count,
        "actors_with_refs": actors_with_refs,
        "actors_without_refs": actors_without_refs,
        "cameras_exported": cameras_exported,
        "missing_meshes": missing_meshes,
        "file_path": abs_out,
        "file_size": size,
    }

def _write_empty_stage(file_path: str):
    """Write a valid but empty stage so you never get a blank file header."""
    try:
        from pxr import Usd, UsdGeom
        abs_out = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(abs_out), exist_ok=True)
        stage = Usd.Stage.CreateNew(abs_out)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(stage, 0.01)
        world = UsdGeom.Xform.Define(stage, "/World")
        stage.SetDefaultPrim(world.GetPrim())
        stage.Save()
        return {"success": False, "error": "No actors selected; wrote empty /World stage", "file_path": abs_out}
    except Exception as e:
        return {"success": False, "error": f"Could not write empty stage: {e}"}

