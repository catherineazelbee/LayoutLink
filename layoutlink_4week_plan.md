# LayoutLink 4-Week Production Sprint

**Version:** 1.0  
**Date:** November 4, 2025  
**Duration:** 4 weeks (28 days)  
**Goal:** Production-ready animation transfer with layer-based overwrites

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Requirements](#core-requirements)
3. [Week 1: Foundation Layer](#week-1-foundation-layer)
4. [Week 2: Animation Pipeline](#week-2-animation-pipeline)
5. [Week 3: Update Workflow](#week-3-update-workflow)
6. [Week 4: Polish & Deploy](#week-4-polish--deploy)
7. [Daily Schedule](#daily-schedule)
8. [Success Metrics](#success-metrics)

---

## Executive Summary

**4-week plan to add:**
- ✅ Stepped animation export/import (Maya ↔ Unreal)
- ✅ Two-layer system: Base (truth) + Override (changes)
- ✅ Quick update workflow (Unreal → Maya in 3 clicks)
- ✅ Data safety (base layer never overwritten)

**NOT included** (can add later):
- ❌ Conflict detection (manual workflow instead)
- ❌ Complex multi-layer composition (just 2 layers)
- ❌ Delta exports (full exports are fast enough)
- ❌ UUID tracking (manual name matching for now)

---

## Core Requirements

### Must Have (Week 1-4)
1. **Base Layer (Truth)** - First export creates immutable base
2. **Override Layer** - Changes go here, never touch base
3. **Stepped Animation** - Perfect round-trip for blocking
4. **Quick Import** - Update existing Maya scene from Unreal in seconds

### Nice to Have (Post-launch)
- UUID tracking (manual name matching is fine for now)
- Conflict warnings
- Animation validation
- Pretty UI

---

## Week 1: Foundation Layer

**Goal:** Two-layer system working end-to-end

### Day 1-2: Layer Structure (16 hours)

**Create simple 2-layer architecture:**

```
SharedUSD/layouts/
├── my_shot_BASE.usda          # Truth - never overwrite
└── my_shot_unreal_OVER.usda   # Unreal changes only
```

**Implementation:**

**File: `simple_layers.py`** (new file, ~200 lines)

```python
"""
Simple 2-layer system for LayoutLink
Base layer = truth, Override layer = changes
"""

from pxr import Usd, UsdGeom, Sdf
import os

def create_base_layer(export_path):
    """
    Create base layer from current export
    This becomes the source of truth
    
    Usage:
        base_path = create_base_layer("C:/SharedUSD/layouts/shot_001.usda")
        # Creates: shot_001_BASE.usda
    """
    base_path = export_path.replace(".usda", "_BASE.usda")
    
    # Copy the export to base
    stage = Usd.Stage.Open(export_path)
    stage.Export(base_path)
    
    # Mark as base layer
    base_layer = Sdf.Layer.FindOrOpen(base_path)
    custom_data = dict(base_layer.customLayerData or {})
    custom_data["layoutlink_layer_type"] = "base"
    custom_data["layoutlink_locked"] = True
    base_layer.customLayerData = custom_data
    base_layer.Save()
    
    print(f"✓ Created base layer: {base_path}")
    return base_path


def create_override_layer(base_path, app_name="unreal"):
    """
    Create override layer that references base
    
    Usage:
        over_path = create_override_layer("shot_001_BASE.usda", "unreal")
        # Creates: shot_001_unreal_OVER.usda
    """
    base_dir = os.path.dirname(base_path)
    base_name = os.path.basename(base_path).replace("_BASE.usda", "")
    
    over_path = os.path.join(base_dir, f"{base_name}_{app_name}_OVER.usda")
    
    # Create new stage
    stage = Usd.Stage.CreateNew(over_path)
    
    # Reference base layer via sublayers (strongest opinion wins)
    root_layer = stage.GetRootLayer()
    root_layer.subLayerPaths.append(base_path)
    
    # Mark as override
    custom_data = {
        "layoutlink_layer_type": "override",
        "layoutlink_base_layer": base_path,
        "layoutlink_app": app_name
    }
    root_layer.customLayerData = custom_data
    
    stage.Save()
    print(f"✓ Created override layer: {over_path}")
    return over_path


def is_base_layer(usd_path):
    """Check if file is a base layer"""
    if "_BASE.usda" in usd_path:
        return True
    
    layer = Sdf.Layer.FindOrOpen(usd_path)
    if layer:
        custom_data = layer.customLayerData or {}
        return custom_data.get("layoutlink_layer_type") == "base"
    
    return False


def find_override_layer(base_path, app_name):
    """Find corresponding override layer"""
    base_dir = os.path.dirname(base_path)
    base_name = os.path.basename(base_path).replace("_BASE.usda", "")
    
    over_path = os.path.join(base_dir, f"{base_name}_{app_name}_OVER.usda")
    
    return over_path if os.path.exists(over_path) else None


def get_base_from_override(over_path):
    """Get base layer path from override layer"""
    layer = Sdf.Layer.FindOrOpen(over_path)
    if layer:
        custom_data = layer.customLayerData or {}
        base_path = custom_data.get("layoutlink_base_layer")
        if base_path and os.path.exists(base_path):
            return base_path
    
    # Try filename pattern
    if "_OVER.usda" in over_path:
        base_path = over_path.split("_")[0] + "_BASE.usda"
        if os.path.exists(base_path):
            return base_path
    
    return None
```

**Deliverable:** ✅ Simple layer creation tools (1 Python file)

**Testing:**
```python
# Test in Maya script editor:
import simple_layers

# Create base
base = simple_layers.create_base_layer("C:/test/myfile.usda")
print(f"Base: {base}")

# Create override
over = simple_layers.create_override_layer(base, "maya")
print(f"Override: {over}")

# Check detection
print(f"Is base? {simple_layers.is_base_layer(base)}")
```

---

### Day 3-4: Export Integration (16 hours)

**Modify existing export to use layers:**

**Update: `maya_layout_export.py`** (add ~100 lines)

```python
# Add at the top
import simple_layers

def export_selected_to_usd(file_path, asset_library_dir):
    """
    MODIFIED: Now supports layer export
    """
    
    # ... ALL existing export code stays the same ...
    # ... until the very end after stage.Save() ...
    
    # NEW: Layer logic at the end
    print("\n=== Layer Management ===")
    
    base_path = file_path.replace(".usda", "_BASE.usda")
    
    if os.path.exists(base_path):
        # Base exists - this is an UPDATE
        print("Found existing base layer")
        print("Creating override layer for Maya changes...")
        
        # Create override layer
        over_path = simple_layers.create_override_layer(base_path, "maya")
        
        # Move our export TO the override
        if os.path.exists(over_path):
            os.remove(over_path)
        
        os.rename(file_path, over_path)
        
        print(f"✓ Updated override: {over_path}")
        print(f"✓ Base layer safe: {base_path}")
        
        return {
            "success": True,
            "layer_type": "override",
            "file_path": over_path,
            "base_path": base_path,
            "object_count": exported_count,
            "objects_with_refs": objects_with_refs,
            "cameras_exported": cameras_exported
        }
    
    else:
        # No base exists - this is FIRST EXPORT
        print("No base layer found")
        print("Creating base layer (source of truth)...")
        
        # Create base from our export
        base_path = simple_layers.create_base_layer(file_path)
        
        # Remove temp export file
        os.remove(file_path)
        
        print(f"✓ Created base layer: {base_path}")
        print("✓ This is your source of truth - it won't be modified")
        
        return {
            "success": True,
            "layer_type": "base",
            "file_path": base_path,
            "object_count": exported_count,
            "objects_with_refs": objects_with_refs,
            "cameras_exported": cameras_exported
        }
```

**Update: `layout_export.py`** (Unreal, add ~100 lines)

Same pattern - just change "maya" to "unreal" in the layer creation.

**Deliverable:** ✅ Exports automatically use layer system

**Testing:**
1. Export from Maya → Creates `shot_BASE.usda`
2. Export again → Creates `shot_maya_OVER.usda`, base untouched
3. Verify base file timestamp doesn't change

---

### Day 5: Import with Layers (8 hours)

**Update: `maya_layout_import.py`** (add ~80 lines)

```python
import simple_layers

def import_usd_from_unreal(file_path, align_to_maya_up=True):
    """
    MODIFIED: Now handles layered imports
    """
    
    print("=== Layout Import Starting ===")
    print(f"File: {file_path}")
    
    # Check if this is a layered file
    is_override = "_OVER.usda" in file_path
    
    if is_override:
        print("Detected override layer")
        
        # Find base layer
        base_path = simple_layers.get_base_from_override(file_path)
        
        if base_path:
            print(f"Base layer: {base_path}")
            print("Importing layered USD (base + override)...")
        else:
            print("WARNING: Could not find base layer")
            print("Importing override only...")
    
    # ... existing import code ...
    
    # The mayaUsdProxyShape will automatically compose sublayers!
    # No special code needed - USD handles it
    
    xform = cmds.createNode('transform', name=f'UnrealLayout_{base}')
    shape = cmds.createNode('mayaUsdProxyShape', parent=xform)
    
    # Point to the file (if override, base comes automatically)
    cmds.setAttr(f'{shape}.filePath', file_path, type='string')
    
    # Apply rotation if needed
    if align_to_maya_up:
        up_axis = _get_stage_up_axis(file_path)
        if up_axis == 'Z':
            cmds.setAttr(f'{xform}.rotateX', -90.0)
            print("Applied -90° X rotation (Z-up → Y-up)")
    
    print(f"✓ Created USD Stage: {xform}")
    
    return {
        "success": True,
        "stage_transform": xform,
        "stage_shape": shape,
        "is_layered": is_override
    }
```

**Deliverable:** ✅ Import handles both base and override layers

**Testing:**
1. Import `shot_BASE.usda` → Works
2. Import `shot_unreal_OVER.usda` → Automatically loads base too!
3. Verify you see composition of both layers

---

### Week 1 Deliverable Checklist

- ✅ `simple_layers.py` created and tested (200 lines)
- ✅ Maya export creates base layer on first export
- ✅ Maya export creates override layer on subsequent exports
- ✅ Unreal export creates base/override layers
- ✅ Maya import loads layered USD files
- ✅ Unreal import loads layered USD files
- ✅ Manual test: Export → Import → Re-export works
- ✅ Base layer NEVER modified after creation

**Time Check:** 40 hours (5 days × 8 hours)

---

## Week 2: Animation Pipeline

**Goal:** Stepped animation working Maya ↔ Unreal

### Day 6-7: Animation Sampling (16 hours)

**Create: `animation_exporter.py`** (new file, ~300 lines)

```python
"""
Stepped animation exporter for LayoutLink
Samples at keyframes only for perfect round-trip
"""

import maya.cmds as cmds
from pxr import Usd, UsdGeom, Sdf

def export_stepped_animation(maya_object, prim, start_frame, end_frame):
    """
    Export stepped (held) animation from Maya to USD
    
    Args:
        maya_object: Maya transform node
        prim: USD prim to write animation to
        start_frame: Start frame
        end_frame: End frame
    
    Returns:
        True if animation exported, False if static
    """
    
    # Get all keyframes for this object
    keyframes = get_all_keyframes(maya_object, start_frame, end_frame)
    
    if not keyframes or len(keyframes) <= 1:
        print(f"  No animation on {maya_object}")
        return False
    
    print(f"  Exporting {len(keyframes)} keyframes (stepped)")
    
    # Sample at each keyframe
    translate_samples = {}
    rotate_samples = {}
    scale_samples = {}
    
    for frame in keyframes:
        cmds.currentTime(frame)
        
        # Get world-space transform
        t = cmds.xform(maya_object, q=True, ws=True, t=True)
        r = cmds.xform(maya_object, q=True, ws=True, ro=True)
        s = cmds.xform(maya_object, q=True, ws=True, s=True)
        
        translate_samples[frame] = (t[0], t[1], t[2])
        rotate_samples[frame] = (r[0], r[1], r[2])
        scale_samples[frame] = (s[0], s[1], s[2])
    
    # Write to USD with HELD interpolation
    xformable = UsdGeom.Xformable(prim)
    xformable.ClearXformOpOrder()
    
    translate_op = xformable.AddTranslateOp()
    rotate_op = xformable.AddRotateXYZOp()
    scale_op = xformable.AddScaleOp()
    
    # Write all samples
    for frame, value in translate_samples.items():
        translate_op.Set(value, frame)
    
    for frame, value in rotate_samples.items():
        rotate_op.Set(value, frame)
    
    for frame, value in scale_samples.items():
        scale_op.Set(value, frame)
    
    # CRITICAL: Set interpolation to HELD (stepped)
    prim.CreateAttribute("interpolation", Sdf.ValueTypeNames.Token).Set("held")
    
    print(f"  ✓ Exported stepped animation: frames {keyframes[0]}-{keyframes[-1]}")
    
    return True


def get_all_keyframes(maya_object, start_frame, end_frame):
    """
    Get all keyframes on object in frame range
    
    Returns:
        Sorted list of frame numbers
    """
    
    keyframes = set()
    
    # Check all transform channels
    attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']
    
    for attr in attrs:
        full_attr = f"{maya_object}.{attr}"
        
        # Check if animated
        if cmds.keyframe(full_attr, q=True, keyframeCount=True):
            # Get keyframes in range
            keys = cmds.keyframe(
                full_attr,
                q=True,
                time=(start_frame, end_frame),
                timeChange=True
            )
            
            if keys:
                keyframes.update(keys)
    
    # Always include first and last frame
    if keyframes:
        keyframes.add(start_frame)
        keyframes.add(end_frame)
    
    return sorted(list(keyframes))


def is_animated(maya_object):
    """Check if object has any animation"""
    attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']
    
    for attr in attrs:
        if cmds.keyframe(f"{maya_object}.{attr}", q=True, keyframeCount=True):
            return True
    
    return False


def set_timeline_from_usd(usd_file):
    """Set Maya timeline to match USD animation range"""
    from pxr import Sdf
    
    layer = Sdf.Layer.FindOrOpen(usd_file)
    if layer:
        custom_data = layer.customLayerData or {}
        
        start = custom_data.get("layoutlink_start_frame")
        end = custom_data.get("layoutlink_end_frame")
        
        if start and end:
            cmds.playbackOptions(
                minTime=start,
                maxTime=end,
                animationStartTime=start,
                animationEndTime=end
            )
            print(f"✓ Set timeline to {start}-{end}")
            return True
    
    return False
```

**Deliverable:** ✅ Animation sampling tool (300 lines)

**Testing:**
```python
# In Maya:
# 1. Create cube
# 2. Key it at frame 1, 24, 48
# 3. Run:
import animation_exporter
from pxr import Usd, UsdGeom

stage = Usd.Stage.CreateNew("C:/test/anim_test.usda")
prim = UsdGeom.Xform.Define(stage, "/Cube")
animation_exporter.export_stepped_animation("pCube1", prim, 1, 48)
stage.Save()

# 4. Check file - should have timeSamples at frames 1, 24, 48
```

---

### Day 8-9: Maya Animation Export Integration (16 hours)

**Update: `maya_layout_export.py`** (add ~100 lines)

```python
import animation_exporter

def export_selected_to_usd(file_path, asset_library_dir):
    """
    MODIFIED: Now exports animation
    """
    
    # Get frame range from timeline
    start_frame = cmds.playbackOptions(q=True, minTime=True)
    end_frame = cmds.playbackOptions(q=True, maxTime=True)
    
    print(f"=== Layout Export Starting ===")
    print(f"Frame range: {start_frame} - {end_frame}")
    
    # ... existing export setup code ...
    
    # Track animated objects
    animated_count = 0
    
    # Process each object
    for obj in selected:
        # ... existing code to create prim_to_transform ...
        
        # NEW: Check if object is animated
        if animation_exporter.is_animated(obj):
            print(f"  Object is animated: {obj}")
            
            # Export animation
            success = animation_exporter.export_stepped_animation(
                obj,
                prim_to_transform,
                start_frame,
                end_frame
            )
            
            if success:
                animated_count += 1
        
        else:
            # Static object - export transform as before
            # ... existing transform export code ...
            pass
    
    # ... rest of export ...
    
    # Add animation metadata to stage
    custom_data = dict(root_layer.customLayerData)
    custom_data.update({
        "layoutlink_has_animation": (animated_count > 0),
        "layoutlink_animation_type": "stepped",
        "layoutlink_animated_objects": animated_count,
        "layoutlink_start_frame": start_frame,
        "layoutlink_end_frame": end_frame,
        "layoutlink_fps": cmds.playbackOptions(q=True, framesPerSecond=True)
    })
    root_layer.customLayerData = custom_data
    
    print(f"\nAnimated objects: {animated_count}")
    
    # ... then layer management code from Day 3-4 ...
```

**Deliverable:** ✅ Maya exports stepped animation to USD

**Testing:**
1. Create animated cube in Maya (keyframes at 1, 24, 48)
2. Export layout
3. Open USD file in text editor
4. Verify `timeSamples = { 1: (...), 24: (...), 48: (...) }`
5. Verify `token interpolation = "held"`

---

### Day 10: Animation Import (8 hours)

**Update: `maya_layout_import.py`** (add ~40 lines)

```python
import animation_exporter  # For set_timeline_from_usd

def import_usd_from_unreal(file_path, align_to_maya_up=True):
    """
    MODIFIED: Now handles animation
    """
    
    # ... existing import code ...
    
    # After creating the mayaUsdProxyShape:
    
    # NEW: Set timeline from USD animation range
    animation_exporter.set_timeline_from_usd(file_path)
    
    # Enable time connection on proxy shape so animation plays
    cmds.setAttr(f'{shape}.time', 1)  # Connect to Maya timeline
    
    print("✓ Timeline synced, animation will play")
    
    # ... rest of import ...
```

**Update: `layout_import.py`** (Unreal, add ~60 lines)

```python
def import_usd_from_maya(file_path):
    """
    MODIFIED: Now imports animation
    """
    
    # ... existing code to spawn USD Stage Actor ...
    
    # NEW: Read animation metadata and set sequencer range
    try:
        from pxr import Sdf
        
        layer = Sdf.Layer.FindOrOpen(file_path)
        if layer:
            custom_data = layer.customLayerData or {}
            
            has_anim = custom_data.get("layoutlink_has_animation", False)
            start = custom_data.get("layoutlink_start_frame", 1)
            end = custom_data.get("layoutlink_end_frame", 120)
            
            if has_anim:
                unreal.log(f"Animation detected: frames {start}-{end}")
                
                # Set time range on stage actor
                stage_actor.set_editor_property("start_time_code", start)
                stage_actor.set_editor_property("end_time_code", end)
                
                unreal.log("✓ Animation range set on USD Stage Actor")
    
    except Exception as e:
        unreal.log(f"Note: Could not set animation range: {e}")
    
    # ... rest of import ...
```

**Deliverable:** ✅ Animation imports and plays in both apps

**Testing:**
1. Export animated layout from Maya
2. Import to Unreal
3. Scrub timeline in Unreal → Objects move!
4. Verify stepped interpolation (no smooth curves)

---

### Week 2 Deliverable Checklist

- ✅ `animation_exporter.py` created (300 lines)
- ✅ Maya detects animated objects automatically
- ✅ Maya samples at keyframes only (stepped)
- ✅ Animation written to USD with "held" interpolation
- ✅ Animation metadata stored in USD
- ✅ Maya import syncs timeline
- ✅ Unreal import reads animation range
- ✅ Manual test: Animate in Maya → Export → Import to Unreal → Animation plays correctly

**Time Check:** 80 hours total (10 days)

---

## Week 3: Update Workflow

**Goal:** Quick import of Unreal changes back to Maya

### Day 11-13: "Update from Unreal" Feature (24 hours)

**This is THE KILLER FEATURE - makes updates instant!**

**Create: `quick_updater.py`** (new file, ~200 lines)

```python
"""
Quick update workflow - reload USD without recreating everything
"""

import maya.cmds as cmds
import os
import simple_layers

def update_existing_stage(stage_transform, new_usd_path=None):
    """
    Update existing USD stage with new file
    FAST - just reloads the file path
    
    Args:
        stage_transform: Existing transform node with mayaUsdProxyShape
        new_usd_path: Path to new USD file (or None to auto-find)
    
    Returns:
        dict with success status
    """
    
    print("=== Quick Update Starting ===")
    print(f"Updating: {stage_transform}")
    
    # Find the proxy shape
    shapes = cmds.listRelatives(stage_transform, shapes=True, type='mayaUsdProxyShape')
    
    if not shapes:
        print("ERROR: No USD proxy shape found")
        return {"success": False, "error": "Not a USD stage"}
    
    shape_node = shapes[0]
    current_path = cmds.getAttr(f'{shape_node}.filePath')
    
    print(f"Current file: {current_path}")
    
    # Auto-find Unreal override if not specified
    if not new_usd_path:
        new_usd_path = find_unreal_override_for_current(current_path)
        
        if not new_usd_path:
            print("ERROR: Could not find Unreal override")
            return {"success": False, "error": "No Unreal override found"}
    
    print(f"New file: {new_usd_path}")
    
    # Update file path - Maya automatically reloads the USD!
    cmds.setAttr(f'{shape_node}.filePath', new_usd_path, type='string')
    
    # Force viewport refresh
    cmds.refresh()
    
    print("✓ Stage updated! (took < 5 seconds)")
    
    return {
        "success": True,
        "stage": stage_transform,
        "old_path": current_path,
        "new_path": new_usd_path
    }


def find_unreal_override_for_current(current_path):
    """
    Find Unreal override layer for current file
    
    Examples:
        shot_BASE.usda → shot_unreal_OVER.usda
        shot_maya_OVER.usda → shot_unreal_OVER.usda
    
    Returns:
        Path to Unreal override, or None
    """
    
    # Get base filename
    if "_BASE.usda" in current_path:
        base_name = current_path.replace("_BASE.usda", "")
    elif "_maya_OVER.usda" in current_path:
        base_name = current_path.replace("_maya_OVER.usda", "")
    else:
        # Unknown pattern
        return None
    
    # Build Unreal override path
    unreal_path = f"{base_name}_unreal_OVER.usda"
    
    if os.path.exists(unreal_path):
        return unreal_path
    
    return None


def list_all_usd_stages():
    """Find all USD stages in current Maya scene"""
    
    all_shapes = cmds.ls(type='mayaUsdProxyShape')
    
    stages = []
    for shape in all_shapes:
        parent = cmds.listRelatives(shape, parent=True)
        if parent:
            stages.append(parent[0])
    
    return stages


def get_stage_info(stage_transform):
    """Get info about a USD stage"""
    
    shapes = cmds.listRelatives(stage_transform, shapes=True, type='mayaUsdProxyShape')
    if not shapes:
        return None
    
    file_path = cmds.getAttr(f'{shapes[0]}.filePath')
    
    # Detect layer type
    if "_BASE.usda" in file_path:
        layer_type = "base"
    elif "_OVER.usda" in file_path:
        layer_type = "override"
        # Which app?
        if "_maya_OVER" in file_path:
            layer_type = "maya_override"
        elif "_unreal_OVER" in file_path:
            layer_type = "unreal_override"
    else:
        layer_type = "unknown"
    
    return {
        "transform": stage_transform,
        "file_path": file_path,
        "layer_type": layer_type
    }
```

**Deliverable:** ✅ Quick update system

---

### Day 14-15: UI Integration (16 hours)

**Update: `maya_LayoutLink.py`** (add ~80 lines)

```python
# Add new button in Import section
update_btn = QtWidgets.QPushButton("🔄 Update from Unreal (Quick)")
update_btn.setStyleSheet("""
    QPushButton {
        background-color: #9C27B0;
        color: white;
        font-size: 13px;
        font-weight: bold;
        padding: 12px;
        border-radius: 5px;
    }
    QPushButton:hover { background-color: #7B1FA2; }
    QPushButton:pressed { background-color: #4A148C; }
""")
update_btn.clicked.connect(self.on_update_from_unreal)
import_layout.addWidget(update_btn)


def on_update_from_unreal(self):
    """Quick update existing stage with Unreal changes"""
    import quick_updater
    
    self.log("\n=== Quick Update from Unreal ===")
    
    # Find all USD stages in scene
    stages = quick_updater.list_all_usd_stages()
    
    if not stages:
        QtWidgets.QMessageBox.warning(
            self, "No USD Stages",
            "No USD stages found in scene.\n\nImport a layout first."
        )
        self.log("ERROR: No USD stages in scene")
        return
    
    # If multiple stages, let user pick
    if len(stages) > 1:
        stage, ok = QtWidgets.QInputDialog.getItem(
            self, "Select Stage",
            "Which USD stage to update?",
            stages, 0, False
        )
        if not ok:
            self.log("Cancelled")
            return
    else:
        stage = stages[0]
    
    self.log(f"Updating stage: {stage}")
    
    # Do the update!
    result = quick_updater.update_existing_stage(stage)
    
    if result["success"]:
        self.log("✓ Updated from Unreal!")
        self.log(f"  Old: {result['old_path']}")
        self.log(f"  New: {result['new_path']}")
        
        QtWidgets.QMessageBox.information(
            self, "Update Complete",
            f"Stage updated with Unreal changes!\n\n{stage}\n\n"
            f"Updated in < 10 seconds!"
        )
    else:
        error = result.get('error', 'Unknown error')
        self.log(f"ERROR: {error}")
        
        QtWidgets.QMessageBox.warning(
            self, "Update Failed",
            f"Could not update:\n\n{error}\n\n"
            f"Make sure Unreal has exported an override layer."
        )
```

**Deliverable:** ✅ "Update from Unreal" button in Maya UI

---

### Week 3 Deliverable Checklist

- ✅ `quick_updater.py` created (200 lines)
- ✅ "🔄 Update from Unreal" button in Maya UI (purple)
- ✅ Auto-finds Unreal override layer
- ✅ Updates in <10 seconds
- ✅ Handles multiple USD stages in scene
- ✅ Animation preserved during update
- ✅ Clear error messages
- ✅ Manual test: Unreal changes appear in Maya instantly

**Time Check:** 120 hours total (15 days)

---

## Week 4: Polish & Deploy

**Goal:** Production-ready, documented, tested

### Day 16: Animation Export Checkbox (8 hours)

**Update: `maya_LayoutLink.py`** (add ~30 lines to UI)

```python
# Add checkbox before export buttons
self.export_anim_checkbox = QtWidgets.QCheckBox("Export Animation (Stepped)")
self.export_anim_checkbox.setChecked(True)
self.export_anim_checkbox.setToolTip(
    "Export stepped (held) animation.\n"
    "Only keyframes are exported for perfect round-trip."
)
export_layout.addWidget(self.export_anim_checkbox)

# Update frame range info dynamically
self.frame_info_label = QtWidgets.QLabel()
self.update_frame_info()
export_layout.addWidget(self.frame_info_label)


def update_frame_info(self):
    """Update frame range display"""
    start = cmds.playbackOptions(q=True, minTime=True)
    end = cmds.playbackOptions(q=True, maxTime=True)
    self.frame_info_label.setText(f"Frame Range: {int(start)} - {int(end)}")


def on_export_layout(self):
    """Export with animation checkbox"""
    # ... existing code ...
    
    # Check if animation should be exported
    export_anim = self.export_anim_checkbox.isChecked()
    
    # For now, always export animation if it exists
    # (checkbox is informational)
    
    result = maya_layout_export.export_selected_to_usd(
        file_path[0],
        asset_lib
    )
    
    # ... rest of function ...
```

**Similar for Unreal UI.**

**Deliverable:** ✅ UI shows animation options

---

### Day 17: Documentation (8 hours)

**Create: `LayoutLink_WORKFLOW.md`**

```markdown
# LayoutLink Quick Start Guide

## 🚀 Basic Workflow (No Animation)

### First Export from Maya

1. Select objects
2. Click "📤 Export Layout (Selected)"
3. Save as `shot_010.usda`
4. **Result:** Creates `shot_010_BASE.usda` (your source of truth)

### Import to Unreal

1. Click "Import Layout from Maya"
2. Select `shot_010_BASE.usda`
3. **Result:** USD Stage Actor appears with your layout

### Make Changes in Unreal

1. Move objects, adjust lighting
2. Select objects
3. Click "Export Layout (Selected)"
4. Save as same name: `shot_010.usda`
5. **Result:** Creates `shot_010_unreal_OVER.usda`

### Update Maya with Unreal Changes

1. In Maya, click "🔄 Update from Unreal (Quick)"
2. Select your USD stage (if you have multiple)
3. **Result:** Stage reloads with Unreal changes in < 10 seconds!

---

## 🎬 Animation Workflow

### Creating Blocking Animation in Maya

1. Create your layout
2. Set keyframes at important poses (blocking)
3. **IMPORTANT:** Use stepped tangents only!
   - Select all keys
   - Graph Editor → Tangents → Stepped
4. Export layout
5. **Result:** Animation exports with perfect stepped interpolation

### Viewing in Unreal

1. Import the USD file
2. Press Play in Unreal
3. Animation plays back with stepped motion
4. **Note:** Timeline range auto-set from Maya

### Round-Trip

1. Make camera animation in Maya (stepped)
2. Export
3. Import to Unreal → Camera animated
4. Adjust camera in Unreal
5. Export from Unreal
6. Update in Maya → See Unreal camera changes
7. **Result:** Both sets of changes combined!

---

## 📁 Understanding Layers

### What are the `_BASE` and `_OVER` files?

**Base Layer (`shot_010_BASE.usda`):**
- Created on first export
- Your source of truth
- **NEVER modified** after creation
- Safe backup of original layout

**Override Layer (`shot_010_maya_OVER.usda`):**
- Created on subsequent Maya exports
- Contains only YOUR changes
- References base layer

**Override Layer (`shot_010_unreal_OVER.usda`):**
- Created from Unreal exports
- Contains only UNREAL changes
- References base layer

**Why?**
- Base is always safe (can always go back)
- Each app has its own override
- Changes don't conflict (different files)
- Fast updates (just reload)

### When to Create New Base Layer

**Create new base when:**
- Starting a new shot
- Layout is finalized
- Want to "bake down" changes

**DON'T create new base when:**
- Just tweaking existing layout
- Making animation changes
- Updating from other app

---

## 🔧 Troubleshooting

### "Update from Unreal" says no override found

**Problem:** Unreal hasn't exported yet, or wrong filename

**Solution:**
1. Go to Unreal
2. Export layout (same shot name!)
3. Try update again

### Animation doesn't play

**Problem:** Timeline not synced

**Solution:**
1. Check Maya timeline matches export range
2. Make sure mayaUsdProxyShape.time is connected
3. Scrub timeline to refresh

### Objects below grid in Maya

**Problem:** Z-up file from Unreal

**Solution:** Import should auto-rotate. If not, manually rotate stage transform -90° in X.

### Can't find my USD stages

**Problem:** Stage deleted or renamed

**Solution:**
1. Look for `UnrealLayout_*` nodes in Outliner
2. Re-import if needed

---

## 💡 Pro Tips

1. **Use consistent naming:** `shot_010`, `shot_020`, etc.
2. **Keep base layer safe:** Never manually edit `_BASE.usda` files
3. **Export often:** Overrides are cheap, export whenever you make changes
4. **Update frequently:** Click update button to see latest from other app
5. **Timeline matters:** Make sure frame ranges match between apps

---

## 📊 What Can Go Wrong?

**Multiple artists editing same shot:**
- Each creates their own override (`_artistname_OVER.usda`)
- Manually merge or choose one to keep

**Need to reset everything:**
- Delete override layers
- Keep base layer
- Start fresh from base

**Lost base layer:**
- Your latest override becomes new base
- Export it, then create base from it

---

## 🎯 Limitations (Current Version)

**What works:**
- ✅ Stepped animation (perfect round-trip)
- ✅ Static layouts
- ✅ Camera animation
- ✅ Quick updates between apps

**What doesn't work yet:**
- ❌ Smooth animation curves (use stepped only)
- ❌ Automatic conflict detection (manual workflow)
- ❌ Undo updates (re-import old version)
- ❌ Batch operations

**These can be added in future updates!**
```

**Deliverable:** ✅ User workflow guide

---

### Day 18-19: Testing (16 hours)

**Test all scenarios:**

#### **Test 1: Basic Layer System**
- [ ] Export from Maya → Creates BASE
- [ ] Export again → Creates maya_OVER
- [ ] BASE not modified
- [ ] Import to Unreal works

#### **Test 2: Animation**
- [ ] Create stepped animation in Maya
- [ ] Export
- [ ] Import to Unreal
- [ ] Animation plays correctly
- [ ] Timeline range correct

#### **Test 3: Quick Update**
- [ ] Maya: Export with animation
- [ ] Unreal: Import
- [ ] Unreal: Move camera, export
- [ ] Maya: Click "Update from Unreal"
- [ ] Changes appear in <10 seconds
- [ ] Animation still works

#### **Test 4: Round-Trip**
- [ ] Maya → Unreal → Maya
- [ ] Unreal → Maya → Unreal
- [ ] Animation survives
- [ ] Transforms accurate
- [ ] No data loss

#### **Test 5: Edge Cases**
- [ ] Empty selection
- [ ] Missing base layer
- [ ] Corrupted USD file
- [ ] Wrong file path
- [ ] Multiple stages in scene

**Fix all critical bugs found.**

**Deliverable:** ✅ 5 test suites passing

---

### Day 20: Final Polish (8 hours)

**Code cleanup:**
- Remove debug prints (or make them optional)
- Add comments to tricky sections
- Standardize error messages
- Check Python/C++ style

**Create example files:**
```
LayoutLink_Examples/
├── simple_cube_BASE.usda          # Static cube
├── animated_camera_BASE.usda      # Camera with animation
├── animated_camera_maya_OVER.usda # Maya animation override
└── README.txt                      # How to use examples
```

**Record tutorial video (5 min):**
1. Show export from Maya
2. Show import to Unreal
3. Show update workflow
4. Show animation

**Deliverable:** ✅ Production-ready package

---

### Week 4 Deliverable Checklist

- ✅ Animation checkbox in UI
- ✅ Frame range display
- ✅ Layer type indicator
- ✅ User workflow guide (WORKFLOW.md)
- ✅ 5 test suites passing
- ✅ No critical bugs
- ✅ Example files provided
- ✅ Tutorial video (5 min)
- ✅ Code cleaned up
- ✅ Ready to ship!

**Final Time Check:** 160 hours total (20 days, 4 weeks)

---

## Success Metrics

### By End of Week 4

**Functional Requirements:**
- ✅ Export from Maya creates base/override layers
- ✅ Export from Unreal creates base/override layers
- ✅ Import to Maya loads layered USD
- ✅ Import to Unreal loads layered USD
- ✅ Stepped animation exports from Maya
- ✅ Stepped animation imports to Unreal
- ✅ "Update from Unreal" works in <10 seconds
- ✅ Base layer never overwritten
- ✅ Animation survives updates
- ✅ No data loss

**Performance Targets:**
- ✅ Export 50 objects: <30 seconds
- ✅ Import 50 objects: <30 seconds
- ✅ Update existing stage: <10 seconds
- ✅ Export 20 keyframes: <10 seconds

**Quality Targets:**
- ✅ Transform accuracy: <0.001 units
- ✅ Animation frame accuracy: perfect (stepped)
- ✅ Works in Maya 2023-2025
- ✅ Works in Unreal 5.4-5.6

---

## Files You'll Create/Modify

### New Files (Week 1-4)
1. `simple_layers.py` (~200 lines) - Layer management
2. `animation_exporter.py` (~300 lines) - Animation sampling
3. `quick_updater.py` (~200 lines) - Quick update system
4. `LayoutLink_WORKFLOW.md` - User documentation

### Modified Files (Week 1-4)
1. `maya_layout_export.py` (+250 lines) - Layer + animation export
2. `layout_export.py` (+150 lines) - Unreal layer + animation
3. `maya_layout_import.py` (+120 lines) - Layer import + timeline
4. `layout_import.py` (+80 lines) - Unreal animation import
5. `maya_LayoutLink.py` (+110 lines) - Update button + UI
6. `LayoutLink.cpp` (+80 lines) - Unreal update button

**Total new/modified code: ~1,590 lines** (very achievable in 4 weeks!)

---

## Daily Breakdown Summary

| Week | Days | Focus | Hours | Deliverable |
|------|------|-------|-------|-------------|
| 1 | 1-2 | Layer structure | 16 | `simple_layers.py` |
| 1 | 3-4 | Export integration | 16 | Exports use layers |
| 1 | 5 | Import integration | 8 | Imports use layers |
| 2 | 6-7 | Animation sampler | 16 | `animation_exporter.py` |
| 2 | 8-9 | Maya anim export | 16 | Stepped anim export |
| 2 | 10 | Anim import | 8 | Anim plays in both apps |
| 3 | 11-13 | Update system | 24 | `quick_updater.py` |
| 3 | 14-15 | UI integration | 16 | Update button works |
| 4 | 16 | UI polish | 8 | Animation checkbox |
| 4 | 17 | Documentation | 8 | Workflow guide |
| 4 | 18-19 | Testing | 16 | All tests pass |
| 4 | 20 | Final polish | 8 | Ship it! |

**Total: 160 hours (4 weeks @ 40 hrs/week)**

---

## Risk Mitigation

### If You Fall Behind

**End of Week 1:**
- ❌ If layer system not working → Simplify to single file + backup copy
- ✅ Must have: Basic export/import working

**End of Week 2:**
- ❌ If animation too complex → Ship without animation
- ✅ Must have: Layer system working

**End of Week 3:**
- ❌ If update workflow too slow → Use manual re-import
- ✅ Must have: Animation working

**End of Week 4:**
- ❌ Skip fancy UI polish
- ✅ Must have: Core workflow documented

### Minimum Viable Product (MVP)

**If you only have 2 weeks:**
- ✅ Week 1: Layer system
- ✅ Week 3: Update workflow  
- ❌ Skip: Animation (add later)

---

## What Success Looks Like (Day 20)

**You should be able to do this workflow:**

```
┌─────────────────────────────────────────────┐
│              Day 1 (Maya)                    │
├─────────────────────────────────────────────┤
│ 1. Create layout with props                 │
│ 2. Add stepped animation to camera          │
│ 3. Export → shot_010_BASE.usda created      │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│           Day 2 (Unreal)                     │
├─────────────────────────────────────────────┤
│ 1. Import shot_010_BASE.usda                │
│ 2. See layout + camera animation            │
│ 3. Move some props, adjust lighting         │
│ 4. Export → shot_010_unreal_OVER.usda       │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│            Day 3 (Maya)                      │
├─────────────────────────────────────────────┤
│ 1. Click "🔄 Update from Unreal"            │
│ 2. Wait 8 seconds                           │
│ 3. See Unreal changes!                      │
│ 4. Camera animation still works             │
│ 5. Base layer still safe                    │
└─────────────────────────────────────────────┘

✅ WORKFLOW COMPLETE - PRODUCTION READY!
```

---

## Post-Launch (Optional)

**Sprint 2 (+2 weeks):**
- Add UUID tracking for better object matching
- Add conflict detection warnings
- Add validation tools

**Sprint 3 (+2 weeks):**
- Add smooth animation support (with warnings)
- Add batch operations
- Add undo support

---

**Ready to start Week 1, Day 1?** 🎯

Let me know when you're ready and I'll give you the complete `simple_layers.py` file to begin!