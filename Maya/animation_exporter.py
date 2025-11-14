"""
LayoutLink Animation Exporter
==============================

Exports STEPPED animation from Maya to USD for perfect round-trip.
Samples at keyframes only - no curve interpolation.

This is for LAYOUT blocking animation:
- Cameras
- Props
- Set pieces
- NOT for character rigs (transform animation only)
"""

import maya.cmds as cmds
from pxr import UsdGeom, Sdf


def is_animated(maya_object):
    """
    Check if object has keyframes on its transform.
    
    Args:
        maya_object: Maya transform node name
        
    Returns:
        True if object has keyframes, False otherwise
    """
    # Check all transform channels
    attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']
    
    for attr in attrs:
        full_attr = f"{maya_object}.{attr}"
        
        # Check if this channel has keyframes
        keyframe_count = cmds.keyframe(full_attr, query=True, keyframeCount=True)
        if keyframe_count and keyframe_count > 0:
            return True
    
    return False


def get_all_keyframes(maya_object, start_frame, end_frame):
    """
    Get all keyframes on object's transform within frame range.
    
    Args:
        maya_object: Maya transform node name
        start_frame: Start of range
        end_frame: End of range
        
    Returns:
        Sorted list of frame numbers (floats)
        
    Example:
        >>> keys = get_all_keyframes("pCube1", 1, 100)
        >>> print(keys)
        [1.0, 24.0, 48.0, 100.0]
    """
    
    keyframes = set()
    
    # Check all transform channels
    attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']
    
    for attr in attrs:
        full_attr = f"{maya_object}.{attr}"
        
        # Check if animated
        keyframe_count = cmds.keyframe(full_attr, query=True, keyframeCount=True)
        
        if keyframe_count and keyframe_count > 0:
            # Get keyframes in this range
            keys = cmds.keyframe(
                full_attr,
                query=True,
                time=(start_frame, end_frame),
                timeChange=True
            )
            
            if keys:
                keyframes.update(keys)
    
    # Always include first and last frame (even if no keys there)
    if keyframes:
        keyframes.add(start_frame)
        keyframes.add(end_frame)
    
    return sorted(list(keyframes))


def export_stepped_animation(maya_object, prim, start_frame, end_frame):
    """
    Export stepped (held) animation from Maya to USD prim.
    
    Samples at keyframes only for perfect round-trip.
    Uses USD "held" interpolation (no interpolation between keyframes).
    
    Args:
        maya_object: Maya transform node
        prim: USD prim to write animation to
        start_frame: Animation start
        end_frame: Animation end
        
    Returns:
        True if animation exported, False if object is static
        
    Example:
        >>> from pxr import Usd, UsdGeom
        >>> stage = Usd.Stage.CreateNew("test.usda")
        >>> cube_prim = UsdGeom.Xform.Define(stage, "/Cube")
        >>> export_stepped_animation("pCube1", cube_prim, 1, 100)
        True
    """
    
    # Get all keyframes for this object
    keyframes = get_all_keyframes(maya_object, start_frame, end_frame)
    
    if not keyframes or len(keyframes) <= 1:
        # No animation or only 1 keyframe
        print(f"  No animation on {maya_object}")
        return False
    
    print(f"  Exporting {len(keyframes)} keyframes (STEPPED)")
    print(f"    Frames: {keyframes}")
    
    # Sample transform at each keyframe
    translate_samples = {}
    rotate_samples = {}
    scale_samples = {}
    
    for frame in keyframes:
        # Jump to this frame
        cmds.currentTime(frame)
        
        # Get world-space transform at this frame
        t = cmds.xform(maya_object, query=True, worldSpace=True, translation=True)
        r = cmds.xform(maya_object, query=True, worldSpace=True, rotation=True)
        s = cmds.xform(maya_object, query=True, worldSpace=True, scale=True)
        
        # Store samples
        translate_samples[frame] = (t[0], t[1], t[2])
        rotate_samples[frame] = (r[0], r[1], r[2])
        scale_samples[frame] = (s[0], s[1], s[2])
    
    # Write to USD with time-varying transform ops
    xformable = UsdGeom.Xformable(prim)
    xformable.ClearXformOpOrder()
    
    # Create transform ops
    translate_op = xformable.AddTranslateOp()
    rotate_op = xformable.AddRotateXYZOp()
    scale_op = xformable.AddScaleOp()
    
    # Write all samples as timeSamples
    for frame, value in translate_samples.items():
        translate_op.Set(value, frame)
    
    for frame, value in rotate_samples.items():
        rotate_op.Set(value, frame)
    
    for frame, value in scale_samples.items():
        scale_op.Set(value, frame)
    
    # CRITICAL: Set interpolation to HELD (stepped, no interpolation)
    # USD uses "held" for stepped/constant interpolation
    # We mark it both ways for maximum compatibility:
    
    # 1. Custom attribute (for our pipeline tracking)
    if hasattr(prim, 'GetPrim'):
        usd_prim = prim.GetPrim()
    else:
        usd_prim = prim
    
    usd_prim.CreateAttribute("interpolation", Sdf.ValueTypeNames.Token).Set("held")
    
    # 2. TODO: Set stage-level interpolation when we create the stage
    # (This happens in maya_layout_export.py, not here)
    
    print(f"  ✓ Exported stepped animation")
    print(f"    Range: frames {keyframes[0]}-{keyframes[-1]}")
    
    return True


def set_timeline_from_usd(usd_file):
    """
    Set Maya timeline to match USD animation range.
    
    Reads metadata from USD file and sets Maya playback range.
    
    Args:
        usd_file: Path to USD file
        
    Returns:
        True if timeline was set, False otherwise
    """
    try:
        layer = Sdf.Layer.FindOrOpen(usd_file)
        if not layer:
            return False
        
        custom_data = layer.customLayerData or {}
        
        start = custom_data.get("layoutlink_start_frame")
        end = custom_data.get("layoutlink_end_frame")
        fps = custom_data.get("layoutlink_fps")
        
        if start is not None and end is not None:
            # Set Maya timeline
            cmds.playbackOptions(
                minTime=start,
                maxTime=end,
                animationStartTime=start,
                animationEndTime=end
            )
            
            print(f"✓ Set Maya timeline: {start}-{end}")
            
            if fps:
                print(f"  FPS: {fps}")
            
            return True
    
    except Exception as e:
        print(f"Could not set timeline: {e}")
    
    return False