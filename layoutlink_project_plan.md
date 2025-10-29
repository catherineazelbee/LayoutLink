# LayoutLink Project Plan
## Professional USD Reference Pipeline

---

## Final UI Design

### 🎮 Unreal Engine UI

```
┌─────────────────────────────────┐
│      LayoutLink (Unreal)        │
├─────────────────────────────────┤
│                                 │
│  EXPORT TO MAYA                 │
│  ┌─────────────────────────┐   │
│  │ 📦 Export Mesh Library  │   │  ← One-time/when meshes change
│  │    (Selected Actors)    │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │ 📤 Export Layout        │   │  ← Regular use
│  │    (Selected Actors)    │   │
│  └─────────────────────────┘   │
│                                 │
│  IMPORT FROM MAYA               │
│  ┌─────────────────────────┐   │
│  │ 📥 Import Layout        │   │  ← Loads Maya layout + meshes
│  └─────────────────────────┘   │
│                                 │
│  Settings:                      │
│  Asset Library: [Browse...]     │
│  Layout Folder: [Browse...]     │
│                                 │
└─────────────────────────────────┘
```

**User workflow:**
1. **First time only**: Select some actors → Click "Export Mesh Library"
2. **Regular use**: Select actors → Click "Export Layout"
3. **Import from Maya**: Click "Import Layout" → File dialog

---

### 🎨 Maya UI

```
┌─────────────────────────────────┐
│      LayoutLink (Maya)          │
├─────────────────────────────────┤
│                                 │
│  EXPORT TO UNREAL               │
│  ┌─────────────────────────┐   │
│  │ 📦 Export Mesh Library  │   │  ← One-time/when meshes change
│  │    (Selected Objects)   │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │ 📤 Export Layout        │   │  ← Regular use
│  │    (Selected Objects)   │   │
│  └─────────────────────────┘   │
│                                 │
│  IMPORT FROM UNREAL             │
│  ┌─────────────────────────┐   │
│  │ 📥 Import Layout        │   │  ← Loads Unreal layout + meshes
│  └─────────────────────────┘   │
│                                 │
│  Settings:                      │
│  Asset Library: [Browse...]     │
│  Layout Folder: [Browse...]     │
│                                 │
│  ℹ️ Last Import Info            │
│  Artist: John                   │
│  Timestamp: 2025-01-15 14:30    │
│  From: Unreal Engine            │
│                                 │
└─────────────────────────────────┘
```

**User workflow:**
1. **First time only**: Select objects → Click "Export Mesh Library"
2. **Regular use**: Select objects → Click "Export Layout"
3. **Import from Unreal**: Click "Import Layout" → File dialog

---

## Shared Folder Structure

```
SharedUSD/
│
├── assets/                    ← Mesh library (shared by both apps)
│   ├── unreal/               ← Meshes exported from Unreal
│   │   ├── SM_Cube.usda
│   │   └── SM_Chair.usda
│   │
│   └── maya/                 ← Meshes exported from Maya
│       ├── pCube1.usda
│       └── chair_mesh.usda
│
└── layouts/                  ← Layout files (shared by both apps)
    ├── unreal_layouts/
    │   └── level_01.usda
    │
    └── maya_layouts/
        └── shot_001.usda
```

---

**Workflow:**
1. **Setup (once)**: Each app exports its mesh library to `assets/`
2. **Daily work**: Export layouts with references
3. **Collaboration**: Import other app's layouts, meshes load automatically

---

## Key Features

### What Users See

✅ **Full geometry** - No manual mesh assignment needed  
✅ **Correct transforms** - Position, rotation, scale preserved  
✅ **Artist info** - Who exported, when, from which app  
✅ **Fast** - Small files, quick exports/imports  
✅ **Updates propagate** - Change mesh once, all layouts update

### Technical Implementation

✅ **USD References** - Industry standard approach  
✅ **Relative paths** - Works on any machine  
✅ **Metadata tracking** - LayoutLink custom data  
✅ **PySide UI** - Clean, dockable panels  
✅ **Error handling** - Clear messages for missing meshes
---

## Success Criteria

**When complete, users can:**

1. ✅ Select objects in Maya → Export layout → Open in Unreal with full geometry
2. ✅ Select actors in Unreal → Export layout → Open in Maya with full geometry
3. ✅ Update a mesh in asset library → All layouts using it update automatically
4. ✅ See who exported what and when
5. ✅ Work without manual mesh assignment or copying files

---

## Notes

- Both apps share the same mesh library
- Layouts are app-specific (Unreal vs Maya conventions)
- USD handles the heavy lifting (references, transforms, metadata)
- File sizes stay small (layouts are just references + transforms)
