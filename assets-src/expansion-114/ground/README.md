# Worker ant and grasshopper source

The contours in `profiles.py` follow the approved side profiles in `docs/visual-redesign/2026-11-04/four-insect-paper-concept.png`. The second approved image, `four-insect-form-concept.png`, guides the volume, palette, joint placement and finish. All geometry, pigment and rigs are authored in this repository.

## Rebuild from the repository root

```powershell
python assets-src/expansion-114/ground/draw_paper.py
$blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
foreach ($species in @('ant','grasshopper')) {
  & $blender -b -t 3 --factory-startup --disable-autoexec --python-exit-code 1 -P assets-src/expansion-114/ground/build_ground.py -- --species $species
  & $blender -b -t 3 --factory-startup --disable-autoexec --python-exit-code 1 -P assets-src/expansion-114/ground/check_ground.py -- --species $species
}
python assets-src/expansion-114/ground/check_uv.py
& $blender -b -t 3 --factory-startup --disable-autoexec --python-exit-code 1 -P assets-src/expansion-114/ground/check_clearance.py
```

`draw_paper.py` uses Pillow and NumPy. The two compressed editable masters, source pigment and paper examples are in the sibling species folders. Each exported animal faces +X, with its resting tarsi on the ground. Both eyes, antennae, joints and feet have locked natural materials. The grasshopper's enlarged hind femora are paintable. Its separate fan membrane opens beneath the tegmina.

## Verification outputs

Each species folder contains a clean-import `rest.png`, sampled action renders, `roundtrip.json` with evaluated bounds and durations, and `paint-check.json` with GLB skin, triangle, UV and integer mask measurements. `grasshopper/wing-leg-clearance.json` records wing versus hind-leg intersection checks and the minimum vertex height at every integer frame of every clip. Headset rendering and measured device performance belong to runtime verification.

The first studio render had overexposed pigment and cropped the deployed wing. The revised lighting and camera reveal the cuticle profile, the pigment marks and the complete wings. Initial skin UVs could interpolate over locked foreground details. Per-triangle UV correction kept all four tested interior samples inside paintable regions. The first grasshopper geometry had intersecting folded tegmina and hind femora. Moving the hind legs outboard and delaying wing deployment removed those sampled intersections. The first spring pose reached 26 mm below the rest plane. The revised kick opens the tibia farther aft and gives the airborne tarsi clearance.
