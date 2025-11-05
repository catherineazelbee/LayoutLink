"""
Shared metadata utilities for LayoutLink (Maya)
Used by both import and export scripts
Matches the format used by Unreal
"""

from datetime import datetime
import os
import getpass

def add_layoutlink_metadata(layer, operation="export", app="Maya"):
    """
    Add LayoutLink metadata to a USD layer.
    Matches the format used by Unreal.
    
    Args:
        layer: pxr.Sdf.Layer object
        operation: What operation is being performed
        app: Which app is creating the file
    """
    custom_data = {
        "layoutlink_timestamp": datetime.utcnow().isoformat() + 'Z',
        "layoutlink_artist": getpass.getuser(),
        "layoutlink_app": app,
        "layoutlink_operation": operation,
        "layoutlink_version": "0.1.0"
    }
    
    layer.customLayerData = custom_data
    print("Added LayoutLink metadata to USD layer")
    
def read_layoutlink_metadata(layer):
    """
    Read LayoutLink metadata from a USD layer.
    
    Args:
        layer: pxr.Sdf.Layer object
        
    Returns:
        dict: Metadata dictionary or None
    """
    custom_data = layer.customLayerData
    
    if not custom_data:
        return None
    
    # Extract LayoutLink-specific keys
    metadata = {}
    keys = ["layoutlink_timestamp", "layoutlink_artist", 
            "layoutlink_app", "layoutlink_operation", "layoutlink_version"]
    
    for key in keys:
        if key in custom_data:
            metadata[key] = custom_data[key]
    
    return metadata if metadata else None

def format_metadata_string(metadata):
    """
    Format metadata dict into readable string for UI display.
    
    Args:
        metadata: Dict of metadata
        
    Returns:
        str: Formatted string
    """
    if not metadata:
        return "No LayoutLink metadata found"
    
    lines = ["=== Import Info ==="]
    lines.append(f"Artist: {metadata.get('layoutlink_artist', 'N/A')}")
    lines.append(f"Timestamp: {metadata.get('layoutlink_timestamp', 'N/A')}")
    lines.append(f"From: {metadata.get('layoutlink_app', 'N/A')}")
    lines.append(f"Operation: {metadata.get('layoutlink_operation', 'N/A')}")
    lines.append(f"Version: {metadata.get('layoutlink_version', 'N/A')}")
    
    return "\n".join(lines)