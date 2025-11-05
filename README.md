# LayoutLink

**Bidirectional USD pipeline for layout artists working between Maya and Unreal Engine**

LayoutLink enables scene data exchange using industry-standard USD (Universal Scene Description) composition, following professional studio workflows where geometry is stored once in an asset library and referenced by multiple layout files.

---

## Current Features (v0.1.0)

### ✅ **Version 1 Functionality**

**Mesh Library Export:**
- Export static meshes as individual USD assets (Maya & Unreal)
- Custom USD exporter using pxr Python API
- Z-up (Unreal) and Y-up (Maya) coordinate systems

**Layout Export:**
- Export scene layouts with USD references (prevent geometry duplication)
- Lightweight layout files reference mesh library assets
- Metadata tracking (artist, timestamp, source application)
- Camera export with full lens parameters (focal length, sensor size, clipping)

**Layout Import:**
- Import layouts as USD Stages (preserves composition)
- Automatic coordinate system conversion (Z-up ↔ Y-up)
- Mesh references automatically resolved from asset library
- Camera import with accurate lens data

---

## Demo Videos

**Maya → Unreal Workflow:**

https://github.com/user-attachments/assets/d9bb1434-174d-4b47-9ef8-37e12042c809

**Unreal → Maya Workflow:**

https://github.com/user-attachments/assets/ff80a0a3-8b9d-4a3c-b25a-d3b0528ba597

---

## Installation

### Maya
1. Copy all `maya_*.py` files to Maya scripts directory
2. Run in Maya Script Editor:
   ```python
   import maya_LayoutLink
   maya_LayoutLink.show_ui()
   ```

### Unreal Engine
1. Copy `LayoutLink` plugin folder to `Plugins/`
2. Regenerate project files (Right click .uproject file → Show more options)
3. Compile plugin
4. Open LayoutLink from: **Window → LayoutLink** or toolbar button

---

## Quick Start

### First Time Setup

**In Both Apps:**
1. Set **Asset Library** path (e.g., `C:/SharedUSD/assets/maya` or `assets/unreal`)
2. Set **Layout Export** path (e.g., `C:/SharedUSD/layouts/maya_layouts`)

### Basic Workflow

**Export Mesh Library (One Time Operation):**
1. Maya/Unreal: Select mesh objects
2. Click "📦 Export Mesh Library (Selected)"
3. Individual `.usda` files created in asset library

**Export Layout from Maya:**
1. Select objects to export (meshes, cameras)
2. Click "📤 Export Layout (Selected)"
3. Save as `my_shot.usda`
4. Layout file references mesh library (no geometry duplication)

**Import to Unreal:**
1. Click "Import Layout from Maya"
2. Select the `.usda` file
3. USD Stage Actor spawns in level with full scene

**Round-Trip (Unreal → Maya):**
1. Unreal: Select objects, export layout
2. Maya: Click "📥 Import Layout from Unreal"
3. mayaUsdProxyShape created with automatic Z-up → Y-up rotation

---

### File Structure

```
SharedUSD/
├── assets/
│   ├── maya/              # Maya mesh library
│   │   ├── Cube.usda     (5MB - full geometry)
│   │   └── Camera.usda   (2KB - camera definition)
│   └── unreal/            # Unreal mesh library
│       ├── SM_Chair.usda
│       └── SM_Prop.usda
└── layouts/
    ├── maya_layouts/      # Maya scene exports
    │   └── shot_010.usda
    └── unreal_layouts/    # Unreal scene exports
        └── shot_020.usda 
```

### USD Composition

**Mesh Files (Asset Library):**
- Full geometry, normals, UVs
- Subdivision scheme: none (preserves topology)
- Coordinate system: Native to source app
- Reusable across multiple layouts

**Layout Files:**
- USD references to mesh assets (no geometry)
- Transform data only (translate, rotate, scale)
- Camera definitions with lens parameters
- Metadata (artist, timestamp, source app)

---

## Current Limitations

**What Doesn't Work Yet:**
- ❌ Animation transfer (no time-varying data)
- ❌ Round-trip updates (must delete and re-import)
- ❌ Material transfer (USD materials require manual recreation)
- ❌ Lighting transfer
- ❌ Dockable UI panels in both Maya and Unreal

---

## File Reference

### Maya Scripts
- `maya_LayoutLink.py` - Main UI 
- `maya_mesh_export.py` - Mesh library exporter
- `maya_layout_export.py` - Layout exporter with references
- `maya_layout_import.py` - Layout importer (spawns USD Stage, USD Proxy Shape, World transform parent)
- `maya_metadata_utils.py` - Metadata reading/writing

### Unreal Plugin (C++)
- `LayoutLink.h/cpp` - Main plugin module with Slate UI
- `LayoutLinkCommands.h/cpp` - UI command registration
- `LayoutLinkStyle.h/cpp` - UI styling

### Unreal Scripts (Python)
- `mesh_export.py` - Static mesh exporter to USD
- `layout_export.py` - Layout exporter with references
- `layout_import.py` - Layout importer (spawns USD Stage Actor)
- `metadata_utils.py` - Metadata utilities

---

## Development Timeline

**Completed:**
- ✅ Unreal C++ plugin with Slate UI
- ✅ Custom mesh exporter
- ✅ Layout export with USD composition
- ✅ Metadata system
- ✅ Coordinate system conversion
- ✅ Camera export/import with full parameters

**In Progress:**
- 🔄 Layer-based system (BASE + OVER)
- 🔄 Animation pipeline (stepped interpolation)
- 🔄 Quick update workflow

**Planned:**
- ⏳ Conflict detection
- ⏳ Payload support 

---

## Requirements

**Maya:**
- Maya 2025
- mayaUsd plugin installed

**Unreal Engine:**
- Unreal 5.6
- USDImporter plugin enabled
- USDCore plugin enabled
- Python plugin enabled
- Visual Studio 2022 (for compilation)

---

## Contributing

This is a personal project for production pipeline development. Feel free to reference or adapt for your own pipeline needs.

---

## Credits

Built following professional USD workflows as documented by:
- Pixar Animation Studios (USD creators)
- Alliance for OpenUSD
- Autodesk Maya USD documentation
- Epic Games USD integration guides

---

**Version:** 0.1.0  
**Last Updated:** November 4, 2025  
**Status:** Production Alpha