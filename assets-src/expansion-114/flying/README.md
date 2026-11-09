# Dragonfly and honeybee source

The approved 2026-11-04 paper board supplies the silhouette and anatomical divisions. `pattern.py` specifies these in board-pixel coordinates. `build_paper.py` produces the 1024 px transparent line sheets, red-channel masks, optical icons, default crayon pigments and compound-eye texture. The generated files in each species directory include the compressed, editable Blender master with packed textures.

Run from the BugWorld project root in PowerShell with Python, NumPy and Pillow available.

```powershell
$python = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
$src = 'assets-src/expansion-114/flying'
& $python "$src/build_paper.py"
foreach ($species in 'dragonfly','honeybee') {
    & $blender -b -t 3 --factory-startup --python-exit-code 9 --python "$src/build_model.py" -- $species
    & $blender -b -t 3 --factory-startup --python-exit-code 9 --python "$src/review_glb.py" -- $species
}
& $python "$src/verify_paper_uv.py"
& $python "$src/pose_sheet.py"
```

Both insects face +X in glTF. `PaperSurface` uses one skinned draw primitive with a single `Paper_<species>` material. Its glTF UV origin is at the top left of the actual full sheet. `COLOR_0` carries wing opacity and leaves the chitin opaque. The separate `Anatomy` mesh contains the legs, eyes, veins and other fixed details. The six named actions animate one anatomical skeleton.

`roundtrip.png` is a clean import and render of the packaged GLB. `animation-contact.png` contains individual rendered frames from that import. `roundtrip.json` includes full-clip pivot and geometry checks. `uv-check.json` records how much of each mask region is sampled by exported UV triangles. The color paper example shows the registered default pigments. No source concept raster, camera, floor or light is embedded in either runtime model.
