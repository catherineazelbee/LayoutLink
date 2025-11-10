"""
LayoutLink Simple Layer System
================================

Two-layer architecture:
- BASE layer: Immutable source of truth (first export)
- OVERRIDE layer: Application-specific changes (subsequent exports)

Usage:
    # First export
    base_path = create_base_layer("shot_001.usda")
    # Creates: shot_001_BASE.usda
    
    # Subsequent export
    over_path = create_override_layer(base_path, "maya")
    # Creates: shot_001_maya_OVER.usda
"""

from pxr import Usd, UsdGeom, Sdf
import os

# ============================================================================
# LAYER CREATION
# ============================================================================

def create_base_layer(export_path):
    """
    Create BASE layer from exported USD file.
    This becomes the immutable source of truth.
    
    Args:
        export_path: Path to the USD file you just exported
        
    Returns:
        Path to created BASE layer
        
    Example:
        >>> base = create_base_layer("C:/SharedUSD/layouts/shot_001.usda")
        >>> print(base)
        C:/SharedUSD/layouts/shot_001_BASE.usda
    """
    # Generate BASE filename
    base_path = export_path.replace(".usda", "_BASE.usda")
    
    print(f"Creating BASE layer from: {export_path}")
    
    # Open source file
    source_stage = Usd.Stage.Open(export_path)
    if not source_stage:
        raise RuntimeError(f"Could not open source file: {export_path}")
    
    # Export to BASE file (makes a copy)
    source_stage.Export(base_path)
    
    # Add metadata marking this as BASE
    base_layer = Sdf.Layer.FindOrOpen(base_path)
    if base_layer:
        custom_data = dict(base_layer.customLayerData or {})
        custom_data["layoutlink_layer_type"] = "base"
        custom_data["layoutlink_locked"] = True
        custom_data["layoutlink_created_from"] = os.path.basename(export_path)
        base_layer.customLayerData = custom_data
        base_layer.Save()
    
    print(f"✓ Created BASE layer: {base_path}")
    print("  This is your source of truth - it won't be modified")
    
    return base_path


def create_override_layer(base_path, app_name):
    """
    Create OVERRIDE layer that references BASE.
    
    Args:
        base_path: Path to BASE layer
        app_name: "maya" or "unreal"
        
    Returns:
        Path to created OVERRIDE layer
        
    Example:
        >>> over = create_override_layer("shot_001_BASE.usda", "maya")
        >>> print(over)
        shot_001_maya_OVER.usda
    """
    # Generate OVERRIDE filename
    base_dir = os.path.dirname(base_path)
    base_name = os.path.basename(base_path).replace("_BASE.usda", "")
    
    over_path = os.path.join(base_dir, f"{base_name}_{app_name}_OVER.usda")
    
    print(f"Creating OVERRIDE layer: {over_path}")
    print(f"  References: {base_path}")
    
    # Create new stage
    stage = Usd.Stage.CreateNew(over_path)
    
    # Get root layer and add BASE as sublayer
    root_layer = stage.GetRootLayer()
    root_layer.subLayerPaths.append(base_path)
    
    # Add metadata
    custom_data = {
        "layoutlink_layer_type": "override",
        "layoutlink_base_layer": base_path,
        "layoutlink_app": app_name
    }
    root_layer.customLayerData = custom_data
    
    stage.Save()
    
    print(f"✓ Created OVERRIDE layer: {over_path}")
    print(f"  Sublayers BASE: {base_path}")
    
    return over_path


# ============================================================================
# LAYER DETECTION
# ============================================================================

def is_base_layer(usd_path):
    """
    Check if USD file is a BASE layer.
    
    Args:
        usd_path: Path to USD file
        
    Returns:
        True if BASE layer, False otherwise
    """
    # Quick check: filename pattern
    if "_BASE.usda" in usd_path:
        return True
    
    # Thorough check: read metadata
    if not os.path.exists(usd_path):
        return False
    
    try:
        layer = Sdf.Layer.FindOrOpen(usd_path)
        if layer:
            custom_data = layer.customLayerData or {}
            return custom_data.get("layoutlink_layer_type") == "base"
    except:
        pass
    
    return False


def is_override_layer(usd_path):
    """
    Check if USD file is an OVERRIDE layer.
    
    Args:
        usd_path: Path to USD file
        
    Returns:
        True if OVERRIDE layer, False otherwise
    """
    # Quick check: filename pattern
    if "_OVER.usda" in usd_path:
        return True
    
    # Thorough check: read metadata
    if not os.path.exists(usd_path):
        return False
    
    try:
        layer = Sdf.Layer.FindOrOpen(usd_path)
        if layer:
            custom_data = layer.customLayerData or {}
            return custom_data.get("layoutlink_layer_type") == "override"
    except:
        pass
    
    return False


def get_layer_type(usd_path):
    """
    Get layer type: "base", "override", or "unknown".
    
    Args:
        usd_path: Path to USD file
        
    Returns:
        String: "base", "override", or "unknown"
    """
    if is_base_layer(usd_path):
        return "base"
    elif is_override_layer(usd_path):
        return "override"
    else:
        return "unknown"


# ============================================================================
# LAYER NAVIGATION
# ============================================================================

def find_override_layer(base_path, app_name):
    """
    Find OVERRIDE layer for given BASE and app.
    
    Args:
        base_path: Path to BASE layer
        app_name: "maya" or "unreal"
        
    Returns:
        Path to OVERRIDE if exists, None otherwise
        
    Example:
        >>> over = find_override_layer("shot_001_BASE.usda", "unreal")
        >>> if over:
        >>>     print(f"Found: {over}")
    """
    base_dir = os.path.dirname(base_path)
    base_name = os.path.basename(base_path).replace("_BASE.usda", "")
    
    over_path = os.path.join(base_dir, f"{base_name}_{app_name}_OVER.usda")
    
    return over_path if os.path.exists(over_path) else None


def get_base_from_override(over_path):
    """
    Get BASE layer path from OVERRIDE layer.
    
    Args:
        over_path: Path to OVERRIDE layer
        
    Returns:
        Path to BASE layer, or None if not found
    """
    # Try reading from metadata
    try:
        layer = Sdf.Layer.FindOrOpen(over_path)
        if layer:
            custom_data = layer.customLayerData or {}
            base_path = custom_data.get("layoutlink_base_layer")
            
            if base_path and os.path.exists(base_path):
                return base_path
    except:
        pass
    
    # Try filename pattern
    if "_maya_OVER.usda" in over_path:
        base_path = over_path.replace("_maya_OVER.usda", "_BASE.usda")
    elif "_unreal_OVER.usda" in over_path:
        base_path = over_path.replace("_unreal_OVER.usda", "_BASE.usda")
    else:
        return None
    
    return base_path if os.path.exists(base_path) else None


def find_base_layer_for_file(file_path):
    """
    Find BASE layer for any USD file.
    
    Args:
        file_path: Path to any USD file
        
    Returns:
        Path to BASE layer, or None
    """
    # If already BASE, return itself
    if is_base_layer(file_path):
        return file_path
    
    # If OVERRIDE, find its BASE
    if is_override_layer(file_path):
        return get_base_from_override(file_path)
    
    # Try filename pattern matching
    base_path = file_path.replace(".usda", "_BASE.usda")
    return base_path if os.path.exists(base_path) else None


# ============================================================================
# LAYER INFO
# ============================================================================

def get_layer_info(usd_path):
    """
    Get complete information about a layer.
    
    Args:
        usd_path: Path to USD file
        
    Returns:
        Dict with layer information
    """
    info = {
        "path": usd_path,
        "exists": os.path.exists(usd_path),
        "layer_type": "unknown",
        "base_layer": None,
        "override_layers": []
    }
    
    if not info["exists"]:
        return info
    
    # Detect type
    info["layer_type"] = get_layer_type(usd_path)
    
    # If BASE, find overrides
    if info["layer_type"] == "base":
        maya_over = find_override_layer(usd_path, "maya")
        unreal_over = find_override_layer(usd_path, "unreal")
        
        if maya_over:
            info["override_layers"].append(maya_over)
        if unreal_over:
            info["override_layers"].append(unreal_over)
    
    # If OVERRIDE, find base
    elif info["layer_type"] == "override":
        info["base_layer"] = get_base_from_override(usd_path)
    
    return info


def print_layer_info(usd_path):
    """Print layer information (for debugging)"""
    info = get_layer_info(usd_path)
    
    print("=" * 60)
    print(f"Layer Info: {os.path.basename(info['path'])}")
    print("=" * 60)
    print(f"Type: {info['layer_type']}")
    
    if info["base_layer"]:
        print(f"Base: {info['base_layer']}")
    
    if info["override_layers"]:
        print(f"Overrides:")
        for over in info["override_layers"]:
            print(f"  - {over}")
    
    print("=" * 60)