# Deadlock Soul Container Blender Addon

Turns a 3D model into a **Deadlock soul container mod**, from inside Blender.

日本語の説明は [README.md](README.md) にあります。

![A soul container mod in game](images/hero.png)

---

## What you need

| Requirement | Notes |
|---|---|
| Blender 4.2 or newer | A version with the Extensions system |
| Reduced CSDK 12 | Deadlock's compiler tools. Download it from the Google Drive link on [deadlockmodding.pages.dev](https://deadlockmodding.pages.dev/modding-tools/csdk-12) |
| Steam (with Deadlock installed) | The CSDK needs it. Keep Steam running and signed in |
| Deadlock Mod Manager | To put the finished mod into the game ([deadlockmods.app](https://deadlockmods.app/)) |

---

## Installing

1. Download `deadlock_soul_container-x.y.z.zip` from [Releases](../../releases)
2. In Blender, open **Edit → Preferences → Add-ons**, then choose **▼ → Install from Disk** at the top right
3. In the file browser, **pick the zip from step 1 as it is** (do not unpack it)
4. Tick the box next to "Deadlock Soul Container" in the list

### One time only: point the add-on at the CSDK

The add-on needs to know where you put Reduced CSDK 12. Without it, nothing can be built.

1. Open **Edit → Preferences → Add-ons** (if you have just installed it, you are already there)
2. Expand the **▸** on the left of the "**Deadlock Soul Container**" row
3. A field called **CSDK 12 folder** appears. Press the folder icon on its right
4. In the file browser, **select the `Reduced_CSDK_12` folder** and press "Accept"

```
e.g. C:\Users\<you>\Downloads\Reduced_CSDK_12
      ├─ game\        ← the folder where you can see these two
      └─ content\
```

> Pick the folder that has `game\` and `content\` **directly inside it**.
> Depending on the download, the name is sometimes doubled, as in
> `Reduced_CSDK_12\Reduced_CSDK_12\`. In that case the **inner** one is the right choice.

The path is stored in your Blender preferences, so it is remembered across .blend files.
While it is unset, the "3. Build the mod" box shows **"The CSDK 12 folder is not set yet"**.

---

## Using it

Press **N** in the 3D view and open the "**Soul Container**" tab on the right.

### 1. Pick a mesh and press

Load your model into Blender, select **one mesh**, and press **[Make it a soul container]**.

Everything the add-on makes goes into the `SoulContainer` collection.
**Pressing it again does not start over** — it keeps working on the copy you already have.
To start over, delete what it made and press again.

### Material (the look)

Open "Material (vmat)" in the panel to set the **Base Color** and the other images.
If the mesh has no material, one is created for you. Several materials are fine as well.

The numeric settings (roughness, metallic, self-illumination, saturation) are here too.

### 2. Check it

Press **[Check]** to see whether the mesh meets the requirements.

- ✓ … fine
- ⓘ … a note (you can carry on)
- ✗ … a problem (it cannot be built as it is)

### 3. Build the mod

Set the **mod name** and the **output folder**, then press **[Build the mod]**.
Export, compile and packing into a vpk all run in one go, and `<mod name>.vpk` appears in the output folder.

That is the mod file finished. All that is left is getting it into the game —
carry on to "**Using Deadlock Mod Manager**" below.

---

## Using Deadlock Mod Manager

Install Deadlock Mod Manager, then upload the vpk you built from
**Mods Library → Add local mod**.

![Choosing the vpk in Add local mod](images/modmanager-add-local-mod.png)

Go back one screen and enable the mod you just added.

![Enabling it in the list](images/modmanager-enable.png)

---

## When it does not work

**"over the compiler's limit of 524,288"**
Too many vertices to build. Bring the count down, for example with a Decimate modifier
(you do not have to apply it).

**"CSDK 12 not found"**
Check the folder in the preferences. The right folder is the one that contains
`game\bin_cs2\win64\resourcecompiler.exe`.

**The compiler returns an error**
Check that Steam is running. If that does not help, the compiler's raw output is in
`compile.log`, next to the exported files.

---

## What this add-on does not do

- **Soul containers only.** It cannot replace hero models (that needs a different pipeline)
- It handles **one mesh** at a time (join your meshes in Blender first if you need several)

---

## How it works

What runs when you press a button, and why. Use it as a map when you are chasing a problem,
changing the add-on yourself, or feeding it to an AI.

### [Make it a soul container]

1. **Copies the selected mesh.** The copy owns its own mesh data and its own materials, so
   nothing that follows (resizing, renaming materials for the export) reaches your original model
2. Puts a wireframe size guide (radius 6.325 units), an armature with the single bone `joint1`
   and the collision sphere into the `SoulContainer` collection
3. Clears the parent and applies location, rotation and scale to the mesh
4. **Scales it to radius 6.325 units** — the size of the original soul container
5. Moves the centre of the bounding box to the origin (that is where the character's hand is)
6. Adds an armature modifier and weighs every vertex to `joint1` at 100%

The original soul container is **1 unit = 1 inch, radius about 6.3 units (about 32cm across),
one bone called joint1, every vertex weighted to it at 100%, and a collision sphere of radius 7**.
Those six steps are what it takes to match that.

### [Build the mod]

1. Clears the files written by the previous build
   (file names come from material names, so a rename would leave old files behind and they
   would end up in the vpk)
2. Exports the mesh as FBX with **`global_scale=0.0254`** — Blender writes 1 BU as 100cm and
   Source 2 reads FBX centimetres as inches, so without it 1 BU becomes 39.37 units
   (a ball the size of the room)
3. Writes one `.vmat` per material and one line per material into the `remaps` table of the
   `.vmdl`. The template is a `pbr.vfx` NPR setup; only the values are swapped in
4. Compiles with `game\bin_cs2\win64\resourcecompiler.exe`
5. Collects the resulting `*_c` files into a vpk (along with the three rotation-fix particles)

> ⚠ Only the compiler in **`game\bin_cs2\win64\`** works. The ones in `bin\`, `bin_tools\`
> and `bin_server\` stop with `Schema mismatch: resourcecompiler.dll vs particles.dll`.

### Traps already hit

- **A `.001` suffix on a material name is read as a file extension and the material falls off**
  (you get a red wireframe ball). Material names are swapped for ASCII ones during the export
  only. Blender keeps names unique by itself, so anything holding the wanted name is parked
  aside first, the names go through temporary ones, and the result is verified before exporting
- **Textures whose sides are not powers of two fail mip generation for normal/roughness**
  (`Cannot filter non-power-of-two texture 1200x1024x1!`). The whole vmat then fails to compile,
  and the warning you see says the mesh is "referencing missing material" — **two steps away
  from the cause**. Textures are resized to the nearest power of two on export
  (the images inside Blender are left untouched)
- **The vertex ceiling is 524,288** (a skinned mesh uses the GPU animated vertex cache).
  The check counts the vertices that will be *exported*, so a Decimate modifier counts even
  when it has not been applied
- **`obj.bound_box` and `matrix_world` are stale until the dependency graph catches up.**
  `view_layer.update()` is called before measuring, and sizes are measured from the vertices

### The rotation-fix particles

A soul container is **drawn by particles, not by the model**
(`particles/generic/holding_gold_neutral_model.vpcf`).
Swapping the model alone therefore does not make it follow the character's facing — the
original particle locks rotation through `m_bLockRot` on `C_OP_PositionLock`.

Three fixed particles are bundled to solve this; the approach is borrowed from the author of
[mod 657811](https://gamebanana.com/mods/657811). You can leave them out in the settings.
It corrects yaw only, so crouch-walking still looks slightly off.

No Valve models or textures are bundled. The size guide sphere is generated at runtime.

---

## Support

This is a hobby project. It comes **with no warranty and no support**, and there is no place
to send questions (Issues are closed).

It is MIT licensed, so **you are free to change it and share it**. If something is quicker to
fix yourself, please go ahead.

---

## License

MIT. See [LICENSE](LICENSE).
