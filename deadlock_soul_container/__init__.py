# -*- coding: utf-8 -*-
"""Deadlock Soul Container — build a Deadlock soul container mod from Blender.

Press N in the 3D view and pick the "Soul Container" tab. The panel is three numbered steps:

  1. Pick a mesh and press … one button turns the selected mesh into a soul container:
                             the bone joint1, the weights, the size and the centre
  2. Check it              … size, origin, transforms, bones, weights, material
  3. Build the mod         … export FBX + vmat + vmdl, compile, pack into a vpk

The model is expected to come from outside — bought, downloaded, imported. Pick one mesh
out of it and press the button.

One bone (joint1), one mesh, one material: a soul container needs nothing else, and the
add-on does the rig and the weights itself. It is meant for people new to Blender.

Units: Source 2 uses 1 unit = 1 inch. The original ball has a radius of about 6.3 units.
One Blender unit is treated as one Source unit (the scene unit system is set to None).

Wording lives in i18n.py; the language follows Blender's own.
"""
import os
import shutil

import bmesh

import bpy
from mathutils import Vector, Matrix

from . import i18n
from .i18n import tr

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
# Everything this add-on makes goes in here, and nothing else does
GEN_COLLECTION = "SoulContainer"
# older scenes carry these names
OLD_NAMES = ("SoulContainer_Reference", "本家ソウルコンテナ（参考）", "本家_soul_container")
REF_MESH = "SoulContainer_SizeGuide"
REF_PREFIXES = ("SoulContainer_SizeGuide", "Reference_", "本家_")
ARMATURE_NAME = "SoulContainer_Rig"
BONE_NAME = "joint1"
PHYS_NAME = "SoulContainer_Collision_r7"
OLD_PHYS_NAME = "当たり判定（半径7）"
PHYS_RADIUS = 7.0
REF_RADIUS = 6.325          # the original ball's outline, measured once from Valve's model
# the compiler's own ceiling for a skinned mesh (it uses the GPU animated vertex cache).
# Past it the build dies with "Mesh is too large and uses GPU Animated Vertex Cache"
MAX_VERTS = 524288
MOD_PATH = "models/props_gameplay/soul_container/soul_container"
TAB = "\t"

# ---------- shared pieces ----------

def our_collection(ctx):
    """The one collection this add-on writes into. Nothing of the user's is moved in here."""
    col = bpy.data.collections.get(GEN_COLLECTION)
    if col is None:
        col = bpy.data.collections.new(GEN_COLLECTION)
        col.color_tag = "COLOR_04"
    if col.name not in {c.name for c in ctx.scene.collection.children}:
        ctx.scene.collection.children.link(col)
    return col


def put_in_our_collection(ctx, obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    our_collection(ctx).objects.link(obj)


def made_from(src):
    """The soul container we already made out of this mesh, if it is still around.

    Pressing the button twice must not throw away the work done on the copy — the
    materials above all, which the user sets after the first press (2026-09-21).
    """
    col = bpy.data.collections.get(GEN_COLLECTION)
    if col is None:
        return None
    for o in col.objects:
        try:
            if o.type == "MESH" and o.get("dlsc_source") is src:
                return o
        except (ReferenceError, AttributeError):
            continue
    return None


def reference_mesh():
    return bpy.data.objects.get(REF_MESH)


def is_reference(obj):
    """The size guide, the rig, the collision sphere — things to build against, not to export."""
    return (obj.hide_select or obj.name.startswith(REF_PREFIXES)
            or any(c.name in OLD_NAMES for c in obj.users_collection))


def ensure_rig(ctx):
    """The armature with the single bone joint1, plus the collision sphere. Made once."""
    scene = ctx.scene
    scene.unit_settings.system = "NONE"     # 1 Blender unit = 1 Source unit (inch)
    arm_obj = bpy.data.objects.get(ARMATURE_NAME)
    if arm_obj is None:
        arm = bpy.data.armatures.new(ARMATURE_NAME)
        arm_obj = bpy.data.objects.new(ARMATURE_NAME, arm)
        our_collection(ctx).objects.link(arm_obj)
        ctx.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="EDIT")
        b = arm.edit_bones.new(BONE_NAME)
        b.head = Vector((0, 0, 0))
        b.tail = Vector((0, 0, 4))     # the direction is decoration; Source only needs it at the origin
        bpy.ops.object.mode_set(mode="OBJECT")
        arm_obj.show_in_front = True
        arm.display_type = "STICK"
    if PHYS_NAME not in bpy.data.objects and OLD_PHYS_NAME not in bpy.data.objects:
        e = bpy.data.objects.new(PHYS_NAME, None)
        e.empty_display_type = "SPHERE"
        e.empty_display_size = PHYS_RADIUS
        e.parent = arm_obj
        e.hide_select = True
        our_collection(ctx).objects.link(e)
    return arm_obj


def bind_to_rig(ctx, obj, arm_obj):
    """Parent the mesh to the rig and weigh every vertex to joint1 at 100%."""
    obj.modifiers.clear()
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj
    obj.parent = arm_obj
    for vg in list(obj.vertex_groups):
        obj.vertex_groups.remove(vg)
    obj.vertex_groups.new(name=BONE_NAME).add(range(len(obj.data.vertices)), 1.0, "REPLACE")


def make_active(ctx, obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    ctx.view_layer.objects.active = obj


def world_radius(obj):
    """(radius, centre) in world space, measured from the vertices.

    Not from obj.bound_box: that is cached, so straight after mesh.transform() it still
    reports the old size and a resize lands on the wrong number (2026-09-21).
    """
    mw = obj.matrix_world
    pts = [mw @ v.co for v in obj.data.vertices]
    if not pts:
        return 0.0, Vector()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return max(hi - lo) / 2, (lo + hi) / 2


def ascii_name(text, fallback):
    """A name the compiler can read. "Material.001" makes it read ".001" as an extension
    and the material falls off (2026-09-16: the ball came back as a red wireframe)."""
    out = "".join(ch if (ch.isascii() and ch.isalnum()) or ch in "_-" else "_" for ch in text)
    out = out.strip("_").lower()
    # a Japanese name leaves nothing behind but the digits of a ".001" suffix
    if not out or out[0].isdigit():
        out = f"{fallback}_{out}".strip("_")
    return out


def exported_vertex_count(obj):
    """How many vertices the FBX will carry.

    The exporter writes the evaluated mesh (use_mesh_modifiers), so a Decimate modifier
    counts even when it has not been applied. Counting obj.data.vertices instead would
    fail a mesh that is actually fine (2026-09-21).
    """
    try:
        dg = bpy.context.evaluated_depsgraph_get()
        return len(obj.evaluated_get(dg).to_mesh().vertices)
    except (RuntimeError, AttributeError, ReferenceError):
        return len(obj.data.vertices)


def helper_mesh(obj):
    """The glTF importer parks bone-shape Icospheres in a "glTF_not_exported" collection.
    Grabbing one of those together with the model makes a 42-vertex mod (2026-09-21)."""
    return any(c.name.startswith("glTF") for c in obj.users_collection)


def _real(img):
    """A texture worth using. Source 2 Viewer writes 1x1 placeholders for flat values."""
    if img is None:
        return None
    w, h = tuple(img.size)
    return None if (w <= 1 and h <= 1) else img


def weights_ok(obj, bones):
    """Every vertex weighs a total of 100% on the rig's bones."""
    groups = {vg.index for vg in obj.vertex_groups if vg.name in bones}
    if BONE_NAME not in obj.vertex_groups:
        return False
    return all(abs(sum(g.weight for g in v.groups if g.group in groups) - 1.0) <= 0.01
               for v in obj.data.vertices)


def auto_bind(ctx, obj):
    """Do the weighting for the user.

    Weight painting is a craft of its own, and a soul container does not need it: there is
    one bone, so every vertex belongs to joint1 at 100%. So we just do it (2026-09-21).
    The one rig we keep our hands off is one with bones we did not make: those weights
    belong to whoever painted them. Returns True when it changed something.
    """
    arm = next((m.object for m in obj.modifiers if m.type == "ARMATURE" and m.object), None)
    if arm is not None:
        bones = arm.data.bones
        if BONE_NAME in bones and len(bones) > 1:
            return False
        if (arm.name == ARMATURE_NAME and BONE_NAME in bones
                and obj.parent is arm and weights_ok(obj, bones)):
            return False
    if ctx.object is not None and ctx.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bind_to_rig(ctx, obj, ensure_rig(ctx))
    make_active(ctx, obj)
    return True


# ---------- 1. the rig and the reference ball ----------

def place_reference(ctx):
    """A wireframe ball the size of the original, plus the rig. Made once.

    Until 0.7.0 this was Valve's own soul container, shipped inside the add-on (2.3MB of
    the 2.4MB zip). It was only ever something to eyeball the size against, and the fit
    uses the number REF_RADIUS, not the model — so it is a plain sphere now and nothing
    borrowed rides along (2026-09-21).
    """
    ctx.scene.unit_settings.system = "NONE"     # 1 Blender unit = 1 Source unit (inch)
    if reference_mesh() is None:
        me = bpy.data.meshes.new(REF_MESH)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=REF_RADIUS)
        bm.to_mesh(me)
        bm.free()
        guide = bpy.data.objects.new(REF_MESH, me)
        guide.display_type = "WIRE"
        guide.hide_select = True
        guide.hide_render = True
        put_in_our_collection(ctx, guide)
    return ensure_rig(ctx)


# ---------- 1. make the selected mesh into a soul container ----------

class DLSC_OT_make(bpy.types.Operator):
    bl_idname = "dlsc.make"
    bl_label = "Make it a soul container"
    bl_description = ("Take the selected mesh and make it a soul container: copy it, summon the bone "
                      "joint1, weigh every vertex to it, match the original's size and put its centre "
                      "on the origin. Pressing it again keeps the copy you have been working on")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, ctx):
        obj = ctx.active_object
        if obj is None or obj.type != "MESH" or is_reference(obj) or helper_mesh(obj):
            self.report({"ERROR"}, tr("Select one mesh of your model, then press"))
            return {"CANCELLED"}
        if not obj.data.polygons:
            self.report({"ERROR"}, tr("The mesh has no faces"))
            return {"CANCELLED"}
        if ctx.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        place_reference(ctx)
        notes = []

        # Work on a copy. The bought model stays exactly as it came — untouched and
        # unreferenced: its own mesh data and its own materials, so nothing we do here
        # (resizing, renaming a material for the export) can reach back into it
        # (2026-09-21, the user's call).
        again = made_from(obj)
        if any(c.name == GEN_COLLECTION for c in obj.users_collection):
            notes.append(tr("this one is already ours — worked on it in place"))
        elif again is not None:
            # keep the one being worked on: the material set on it stays
            obj = again
            notes.append(tr("kept {name} and fixed it up (delete it to start over)", name=again.name))
        else:
            src = obj
            obj = src.copy()
            obj.data = src.data.copy()
            obj.name = f"SoulContainer_{src.name}"
            obj.data.name = obj.name
            for i, m in enumerate(obj.data.materials):
                if m is not None:
                    obj.data.materials[i] = m.copy()
            obj.hide_select = False
            obj.hide_viewport = False
            obj.display_type = "TEXTURED"
            obj["dlsc_source"] = src
            put_in_our_collection(ctx, obj)
            src.select_set(False)
            notes.append(tr("copied {src} (the original is untouched)", src=src.name))
        make_active(ctx, obj)
        # bake the object's own location / rotation / scale into the mesh
        if obj.parent is not None:
            bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
        if (obj.location.length > 1e-6 or any(abs(a) > 1e-6 for a in obj.rotation_euler)
                or any(abs(v - 1) > 1e-6 for v in obj.scale)):
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            notes.append(tr("applied the transforms"))

        # size: a bought model is usually in metres, so it lands about 40x too big
        ctx.view_layer.update()   # matrix_world is stale until the depsgraph catches up
        r, _ = world_radius(obj)
        if r > 1e-6 and abs(r - REF_RADIUS) > 0.01:
            f = REF_RADIUS / r
            obj.data.transform(Matrix.Scale(f, 4))
            notes.append(tr("scaled {f}x to the size guide", f=f"{f:.3f}"))
        # centre: that is where the character's hand is. Measure again — bound_box is stale
        _, centre = world_radius(obj)
        if centre.length > 1e-6:
            obj.data.transform(Matrix.Translation(-centre))
            notes.append(tr("moved the centre to the origin"))

        auto_bind(ctx, obj)
        notes.append(tr("bound to {bone} at 100%", bone=BONE_NAME))
        _, made_mat = ensure_material(obj)     # a mesh with no material cannot be compiled
        if made_mat:
            notes.append(tr("added a material (it had none)"))
        self.report({"INFO"}, tr("{name} is a soul container now: {notes}", name=obj.name,
                                 notes=" / ".join(notes)))
        return {"FINISHED"}


# ---------- 2b. set the material up ----------

class DLSC_OT_material(bpy.types.Operator):
    bl_idname = "dlsc.material"
    bl_label = "Set up the material"
    bl_description = ("Give the mesh a material with a Principled BSDF if it has none, and plug the "
                      "images picked above into Base Color / Roughness / Normal")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, ctx):
        obj = ctx.active_object
        if obj is None or obj.type != "MESH" or is_reference(obj):
            self.report({"ERROR"}, tr("Select one mesh object, then press"))
            return {"CANCELLED"}
        p = _props(ctx.scene)
        mat, made = ensure_material(obj)
        notes = []
        if made:
            notes.append(tr("added the material {name}", name=mat.name))
        for image, socket in ((p.tex_color, "Base Color"), (p.tex_rough, "Roughness"),
                              (p.tex_normal, "Normal")):
            if image is not None:
                wire_texture(mat, image, socket)
                notes.append(tr("{socket} <- {img}", socket=socket, img=image.name))
        if not notes:
            notes.append(tr("nothing to do (it already has a material)"))
        self.report({"INFO"}, " / ".join(notes))
        return {"FINISHED"}


# ---------- 3. the check ----------

def inspect(obj):
    """(passed?, [(mark, line)]). The mark is OK / NG / NOTE"""
    out = []
    if obj is None or obj.type != "MESH":
        return False, [("NG", tr("Select one mesh, then press"))]
    if is_reference(obj):
        return False, [("NG", tr("This is the size guide, not a model. Select a mesh of your own"))]

    r, centre = world_radius(obj)
    if 0.6 * REF_RADIUS <= r <= 1.6 * REF_RADIUS:
        out.append(("OK", tr("Size: radius about {r} (original {ref})", r=f"{r:.1f}", ref=f"{REF_RADIUS:.1f}")))
    else:
        out.append(("NG", tr("Size: radius about {r} — too far from the original {ref} "
                             "(the unit is inch; built in metres?)", r=f"{r:.1f}", ref=f"{REF_RADIUS:.1f}")))

    if centre.length <= 1.5:
        out.append(("OK", tr("Centre is near the origin (off by {d})", d=f"{centre.length:.2f}")))
    else:
        out.append(("NG", tr("Centre is {d} away from the origin — the hand position will be off",
                             d=f"{centre.length:.1f}")))
    if obj.location.length > 0.01 or any(abs(a) > 1e-4 for a in obj.rotation_euler) or any(abs(s - 1) > 1e-4 for s in obj.scale):
        out.append(("NOTE", tr("Location / rotation / scale are not applied (Ctrl+A > All Transforms)")))

    arm_mod = next((m for m in obj.modifiers if m.type == "ARMATURE" and m.object), None)
    if arm_mod is None:
        # not a fault: building the mod binds it to joint1 on its own
        out.append(("NOTE", tr("Not bound to a rig yet — {bone} at 100% is done for you when you build",
                               bone=BONE_NAME)))
    else:
        bones = arm_mod.object.data.bones
        root = bones.get(BONE_NAME)
        extra = [b.name for b in bones if b.name != BONE_NAME]
        if root is None:
            out.append(("NG", tr("The bone {bone} is missing (the root must be {bone})", bone=BONE_NAME)))
        elif root.parent is not None:
            out.append(("NG", tr("{bone} is not the root (clear its parent)", bone=BONE_NAME)))
        elif not extra:
            out.append(("OK", tr("One bone: {bone}", bone=BONE_NAME)))
        else:
            out.append(("NG", tr("The soul container has only {bone}. Extra bones: {names}", bone=BONE_NAME,
                                 names=", ".join(extra[:4]) + ("…" if len(extra) > 4 else ""))))
        bone_groups = {vg.index for vg in obj.vertex_groups if vg.name in bones}
        if BONE_NAME not in obj.vertex_groups:
            out.append(("NOTE", tr("No vertex group {bone} — it is made for you when you build",
                                   bone=BONE_NAME)))
        else:
            bad = 0
            for v in obj.data.vertices:
                total = sum(g.weight for g in v.groups if g.group in bone_groups)
                if abs(total - 1.0) > 0.01:
                    bad += 1
            if bad == 0:
                out.append(("OK", tr("All {n} vertices weigh 100%", n=f"{len(obj.data.vertices):,}")))
            else:
                out.append(("NOTE", tr("{n} vertices are not at 100% — they are weighted for you "
                                       "when you build", n=bad)))

    mats = [m for m in obj.data.materials if m]
    if not mats:
        out.append(("NG", tr("No material")))
    elif len(mats) == 1:
        out.append(("OK", tr("One material ({name})", name=mats[0].name)))
    else:
        out.append(("OK", tr("{n} materials — each one becomes a vmat", n=len(mats))))
    plain = [m.name for m in mats if _real(_linked_image(m, "Base Color")) is None]
    if plain:
        out.append(("NOTE", tr("No colour texture on: {names} (the material's own colour is used)",
                               names=", ".join(plain[:4]) + ("…" if len(plain) > 4 else ""))))

    n = exported_vertex_count(obj)
    raw = len(obj.data.vertices)
    if n != raw:
        out.append(("NOTE", tr("Modifiers bring {raw} vertices down to {n} on export",
                               raw=f"{raw:,}", n=f"{n:,}")))
    if n > MAX_VERTS:
        out.append(("NG", tr("{n} vertices — over the compiler's limit of {max}. "
                             "Add a Decimate modifier (Ratio) to bring it down",
                             n=f"{n:,}", max=f"{MAX_VERTS:,}")))
    else:
        out.append(("OK" if n <= 60000 else "NOTE", tr("{n} vertices (original 29,964)", n=f"{n:,}")))

    ok = not any(k == "NG" for k, _ in out)
    return ok, out


class DLSC_OT_inspect(bpy.types.Operator):
    bl_idname = "dlsc.inspect"
    bl_label = "Check"
    bl_description = "Check the selected mesh against the soul container rules"

    def execute(self, ctx):
        ok, rows = inspect(ctx.active_object)
        ctx.scene["dlsc_inspect"] = [f"{k}｜{t}" for k, t in rows]
        ctx.scene["dlsc_inspect_ok"] = ok
        self.report({"INFO"} if ok else {"WARNING"},
                    tr("Check passed") if ok else tr("Check found something to fix (see the panel)"))
        return {"FINISHED"}


# ---------- settings ----------



def _props(scene):
    return scene.dlsc


class DLSC_Prefs(bpy.types.AddonPreferences):
    """Where this machine keeps the CSDK.

    It used to be a scene property, which meant every new .blend started with whatever
    path was compiled in — mine (2026-09-21). A path that belongs to the computer, not to
    the file, belongs in the add-on preferences: set once, remembered everywhere.
    """
    bl_idname = __package__

    csdk_root: bpy.props.StringProperty(name="CSDK 12 folder", subtype="DIR_PATH", default="",
                                        description="The Reduced_CSDK_12 folder (it holds game and content)")

    def draw(self, ctx):
        col = self.layout.column()
        col.prop(self, "csdk_root", text=tr("CSDK 12 folder"))
        col.label(text=tr("The folder that holds game\\ and content\\ (Reduced_CSDK_12)"))


def prefs():
    try:
        return bpy.context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        return None


def csdk_root():
    p = prefs()
    return bpy.path.abspath(p.csdk_root) if p and p.csdk_root else ""


def _texture_picked(socket_name):
    """Wire the image the moment it is picked.

    The panel uses Blender's own image widget (browse / New / Open), so "Open" only loads
    the file and parks it in this property. Someone new to Blender should not then have to
    find the shader editor, so the update hook does the node work (2026-09-21).
    """
    def update(self, ctx):
        image = getattr(self, {"Base Color": "tex_color", "Roughness": "tex_rough",
                               "Normal": "tex_normal"}[socket_name])
        obj = ctx.active_object
        if image is None or obj is None or obj.type != "MESH" or is_reference(obj):
            return
        mat, _ = ensure_material(obj)
        wire_texture(mat, image, socket_name)
    return update


class DLSC_Props(bpy.types.PropertyGroup):
    addon_name: bpy.props.StringProperty(name="Addon name", default="soulcontainer",
                                         description="Written to content/citadel_addons/<this name>/. ASCII only")
    mod_name: bpy.props.StringProperty(name="Mod name", default="SoulContainer_Mine",
                                       description="The name of the vpk that comes out")
    out_dir: bpy.props.StringProperty(name="vpk goes to", subtype="DIR_PATH", default=r"C:\Users\mousi\デスクトップ")
    include_fix: bpy.props.BoolProperty(name="Include the rotation fix particles", default=True,
                                        description="Put the three particles that make the model follow the character "
                                                    "(proven on cinna) into the vpk")
    # vmat. Images are picked up from the Blender material nodes; choosing one here wins
    tex_color: bpy.props.PointerProperty(type=bpy.types.Image, name="Base Color",
                                         update=_texture_picked("Base Color"),
                                         description="Colour texture. Empty means the image plugged into Base Color is used")
    tex_normal: bpy.props.PointerProperty(type=bpy.types.Image, name="Normal",
                                          update=_texture_picked("Normal"),
                                          description="Normal map. Empty means the image behind the Normal Map node, or flat")
    tex_rough: bpy.props.PointerProperty(type=bpy.types.Image, name="Roughness",
                                         update=_texture_picked("Roughness"),
                                         description="Roughness texture. Empty means the image plugged into Roughness, or a flat value")
    roughness: bpy.props.FloatProperty(name="Roughness (flat)", default=0.5, min=0.0, max=1.0,
                                       description="Used when there is no roughness texture. 0 = smooth, 1 = rough")
    metalness: bpy.props.FloatProperty(name="Metallic", default=0.0, min=0.0, max=1.0)
    self_illum: bpy.props.FloatProperty(name="Self-illumination", default=0.0, min=0.0, max=4.0,
                                        description="0 is off. The base colour texture glows as it is")
    saturation: bpy.props.FloatProperty(name="Saturation", default=1.25, min=0.0, max=3.0,
                                        description="How strong the colours are in game. cinna used 1.25")
    # which boxes of the panel are open
    show_material: bpy.props.BoolProperty(default=True)
    show_settings: bpy.props.BoolProperty(default=False)


def content_dir(scene):
    p = _props(scene)
    return os.path.join(csdk_root(), "content", "citadel_addons", p.addon_name, *MOD_PATH.split("/")[:-1])


def game_dir(scene):
    p = _props(scene)
    return os.path.join(csdk_root(), "game", "citadel_addons", p.addon_name)


def wipe_build_dir(path, csdk_root):
    """Empty a folder this add-on writes into, so the last build does not ride along.

    Material files are named after the Blender material (Material.001 -> material_001), so
    building again under a different name leaves the old vmat_c and its colour texture
    behind — and the vpk takes everything under models/. On 2026-09-21 that made a 4.3 MB
    vpk of which two thirds were textures nobody used.

    Only ever inside <csdk>/{content,game}/citadel_addons/<addon>/models/props_gameplay/
    soul_container: the path is checked against the root and the tail before anything goes.
    Returns how many files it removed.
    """
    tail = tuple(MOD_PATH.split("/")[:-1])
    path = os.path.normpath(path)
    root = os.path.normpath(csdk_root)
    parts = path.split(os.sep)
    if not path.startswith(root + os.sep) or "citadel_addons" not in parts:
        return 0
    if tuple(parts[-len(tail):]) != tail or not os.path.isdir(path):
        return 0
    n = 0
    for name in os.listdir(path):
        full = os.path.join(path, name)
        if os.path.isdir(full):
            n += sum(len(f) for _, _, f in os.walk(full))
            shutil.rmtree(full, ignore_errors=True)
        else:
            os.remove(full)
            n += 1
    return n


def compiler_exe(scene):
    return os.path.join(csdk_root(), "game", "bin_cs2", "win64", "resourcecompiler.exe")


# ---------- 4a. export (FBX + vmat + vmdl into the CSDK addon) ----------

def _upstream_image(socket, depth=4):
    """Follow a socket back until an image turns up.

    Not just one hop: a bought model (and the glTF importer) often puts a Normal Map, a
    Mix or a Separate node between the texture and the Principled BSDF, and stopping at
    the first node called that "no texture" when there is one (2026-09-21).
    """
    if socket is None or not socket.is_linked or depth <= 0:
        return None
    node = socket.links[0].from_node
    if node.type == "TEX_IMAGE":
        return node.image
    for inp in node.inputs:
        img = _upstream_image(inp, depth - 1)
        if img is not None:
            return img
    return None


def _linked_image(mat, socket_name):
    """The image behind a Principled BSDF socket"""
    if not mat or not mat.use_nodes:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return _upstream_image(n.inputs.get(socket_name))
    return None


def ensure_material(obj):
    """A material with a Principled BSDF on the mesh. Made if there is none.

    Someone new to Blender cannot be asked to add a material slot and wire a node tree,
    and a mesh with no material fails the check (2026-09-21, the user's call). So the
    add-on does it. Returns (material, made it?).
    """
    made = False
    mat = next((m for m in obj.data.materials if m), None)
    if mat is None:
        mat = bpy.data.materials.new(f"{obj.name}_Material")
        mat.use_nodes = True
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
        made = True
    if not mat.use_nodes:
        mat.use_nodes = True
    if not any(n.type == "BSDF_PRINCIPLED" for n in mat.node_tree.nodes):
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (-200, 0)
        out = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None) or nodes.new("ShaderNodeOutputMaterial")
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, made


def wire_texture(mat, image, socket_name):
    """Plug an image into a Principled BSDF socket the way Blender expects.

    Base Color takes the image straight, Normal goes through a Normal Map node, and
    anything that is not colour is read as Non-Color data.
    """
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    socket = bsdf.inputs[socket_name]
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.label = socket_name
    tex.location = (-700, {"Base Color": 300, "Roughness": 0, "Normal": -300}.get(socket_name, 0))
    image.colorspace_settings.name = "sRGB" if socket_name == "Base Color" else "Non-Color"
    # take the old texture node with it, or swapping the image piles up dead nodes
    for link in list(socket.links):
        old = link.from_node
        links.remove(link)
        for node in ([old] + [i.links[0].from_node for i in old.inputs if i.is_linked]
                     if old.type == "NORMAL_MAP" else [old]):
            if node.type in {"TEX_IMAGE", "NORMAL_MAP"} and not node.outputs[0].is_linked:
                nodes.remove(node)
    if socket_name == "Normal":
        nm = nodes.new("ShaderNodeNormalMap")
        nm.location = (-420, -300)
        links.new(tex.outputs["Color"], nm.inputs["Color"])
        links.new(nm.outputs["Normal"], socket)
    else:
        links.new(tex.outputs["Color"], socket)


def material_images(mat, p, manual=True):
    """(colour, normal, roughness) for one material.

    What the panel points at wins — but only when the mesh has a single material. With
    several (a bought model: body, eyes, clothes) one picked image cannot mean all of
    them, so every material reads its own nodes.
    """
    return ((p.tex_color if manual else None) or _real(_linked_image(mat, "Base Color")),
            (p.tex_normal if manual else None) or _real(_linked_image(mat, "Normal")),
            (p.tex_rough if manual else None) or _real(_linked_image(mat, "Roughness")))


def _nearest_pot(n):
    """The closest power of two, kept inside what the compiler will take."""
    n = max(4, min(4096, int(n)))
    lo = 1 << (n.bit_length() - 1)
    hi = lo << 1
    best = lo if (n - lo) <= (hi - n) else hi
    return max(4, min(4096, best))


def _save_image(img, path):
    """Write the texture where the compiler will read it.

    Source 2 cannot make mips for a normal/roughness texture whose sides are not powers of
    two — "Cannot filter non-power-of-two texture 1200x1024x1!", and then the whole vmat
    fails and the mesh reports a missing material (2026-09-21, a bought model's normal
    map). Bought textures are often 1200 or 1536 wide, so resize rather than refuse.
    Returns a note when the size had to change.
    """
    w, h = tuple(img.size)
    pw, ph = _nearest_pot(w), _nearest_pot(h)
    if (w, h) != (pw, ph) and w and h:
        tmp = img.copy()
        try:
            tmp.scale(pw, ph)
            tmp.save_render(path)
        finally:
            bpy.data.images.remove(tmp)
        return tr("{name}: {w}x{h} -> {pw}x{ph} (Source needs powers of two)",
                  name=img.name, w=w, h=h, pw=pw, ph=ph)
    if img.packed_file or not img.filepath or img.is_dirty:
        img.save_render(path)
        return None
    src = bpy.path.abspath(img.filepath)
    if os.path.abspath(src) != os.path.abspath(path):
        import shutil
        shutil.copyfile(src, path)
    return None


def _write_vmat(mat, out_dir, mat_name, p, manual=True):
    """template.vmat (cinna's settings) with the textures and numbers swapped in.

    Returns (in-game path, found a colour texture?). No colour texture is not an error:
    the material's own colour is written instead and the build only warns (2026-09-21).
    """
    import re
    mats_dir = os.path.join(out_dir, "materials")
    os.makedirs(mats_dir, exist_ok=True)
    with open(os.path.join(ASSETS, "template.vmat"), encoding="utf-8") as f:
        txt = f.read()
    base = MOD_PATH.rsplit("/", 1)[0] + "/materials"
    color, normal, rough = material_images(mat, p, manual)
    resized = []

    def put(key, value):
        nonlocal txt
        txt = re.sub(rf'{key} "[^"]*"', f'{key} "{value}"', txt, count=1)

    if color is not None:
        note = _save_image(color, os.path.join(mats_dir, f"{mat_name}_color.png"))
        if note:
            resized.append(note)
        put("TextureColor1", f"{base}/{mat_name}_color.png")
    else:
        c = mat.diffuse_color if mat else (0.8, 0.8, 0.8, 1)
        put("TextureColor1", f"[{c[0]:.6f} {c[1]:.6f} {c[2]:.6f} 0.000000]")
    if normal is not None:
        note = _save_image(normal, os.path.join(mats_dir, f"{mat_name}_normal.png"))
        if note:
            resized.append(note)
        put("TextureNormal1", f"{base}/{mat_name}_normal.png")
    if rough is not None:
        note = _save_image(rough, os.path.join(mats_dir, f"{mat_name}_rough.png"))
        if note:
            resized.append(note)
        put("TextureRoughness1", f"{base}/{mat_name}_rough.png")
    else:
        put("TextureRoughness1", f"[{p.roughness:.6f} {p.roughness:.6f} {p.roughness:.6f} 0.000000]")
    put("TextureMetalness1", f"[{p.metalness:.6f} {p.metalness:.6f} {p.metalness:.6f} 0.000000]")
    put("g_flSelfIllumScale1", f"{p.self_illum:.3f}")
    if p.self_illum > 0:
        put("TextureSelfIllumMask1", "[1.000000 1.000000 1.000000 0.000000]")
    put("g_vAlbedoContrastSaturationBrightness1", f"[1.000 {p.saturation:.3f} 1.000]")
    # the outline is left exactly as the template has it: cinna's vmat (and the template)
    # have no F_SOLID_COLOR_OUTLINE, so the tint never reaches the shader anyway, and
    # cinna looked right in game without it (2026-09-21, the user's call: do not touch it)
    with open(os.path.join(mats_dir, f"{mat_name}.vmat"), "w", encoding="utf-8") as f:
        f.write(txt)
    return f"{base}/{mat_name}.vmat", color is not None, resized


class DLSC_OT_export(bpy.types.Operator):
    bl_idname = "dlsc.export"
    bl_label = "Export"
    bl_description = "Export the selected mesh as FBX + vmat + vmdl into the CSDK 12 addon folder"

    def execute(self, ctx):
        obj = ctx.active_object
        if obj is not None and obj.type == "MESH" and not is_reference(obj):
            auto_bind(ctx, obj)      # the user should not have to know weight painting
        ok, rows = inspect(obj)
        if not ok:
            self.report({"ERROR"}, tr("The check has not passed. Fix it first"))
            return {"CANCELLED"}
        if not csdk_root():
            self.report({"ERROR"}, tr("Set the CSDK 12 folder first: Edit > Preferences > Add-ons > "
                                      "Deadlock Soul Container"))
            return {"CANCELLED"}
        if not os.path.exists(compiler_exe(ctx.scene)):
            self.report({"ERROR"}, tr("CSDK 12 not found: {path} (fix it in the add-on preferences)",
                                      path=compiler_exe(ctx.scene)))
            return {"CANCELLED"}
        arm = next(m.object for m in obj.modifiers if m.type == "ARMATURE" and m.object)
        out_dir = content_dir(ctx.scene)
        # last build's files first — they would be packed into the vpk as well
        csdk = csdk_root()
        old = (wipe_build_dir(out_dir, csdk)
               + wipe_build_dir(os.path.join(game_dir(ctx.scene), *MOD_PATH.split("/")[:-1]), csdk))
        if old:
            self.report({"INFO"}, tr("Cleared {n} file(s) left by the last build", n=old))
        os.makedirs(out_dir, exist_ok=True)

        # FBX, the same way cinna went: selection only, no animation, units untouched.
        # ASCII file names only (a Japanese name never reaches the compiler)
        fbx_name = ascii_name(obj.name, "mesh")
        fbx = os.path.join(out_dir, fbx_name + ".fbx")
        bpy.ops.object.select_all(action="DESELECT")
        obj.hide_select = False
        arm.hide_select = False
        obj.hide_viewport = False
        arm.hide_viewport = False
        obj.select_set(True)
        arm.select_set(True)
        ctx.view_layer.objects.active = obj
        if not (obj.select_get() and arm.select_get()):
            self.report({"ERROR"}, tr("The mesh or the rig cannot be selected (hidden, or on another view layer)"))
            return {"CANCELLED"}
        # Every material on the mesh gets its own vmat and its own line in the vmdl remap
        # table — a bought model usually has several (body, eyes, clothes) and the table is
        # just a list of {from, to} pairs (2026-09-21).
        # The material name goes into the FBX as is, so it has to be ASCII for the export.
        plan, taken = [], set()
        for m in [m for m in obj.data.materials if m]:
            base = ascii_name(m.name, "material")
            name, i = base, 2
            while name in taken:
                name, i = f"{base}_{i}", i + 1
            taken.add(name)
            plan.append([m, name, m.name])       # material, ascii name, the name to put back
        # Units: Blender writes 1 BU as 100 cm, Source 2 reads FBX cm as inch (×0.3937).
        # Left alone, 1 BU becomes 39.37 units and the ball fills the room (it did, 2026-09-16).
        # global_scale=0.0254 makes 1 BU → 2.54 cm → 1 inch = 1 unit.
        # Blender keeps material names unique by itself: renaming the second "Eyes" to
        # "eyes" while "eyes" is taken gives "eyes.001" — and the compiler reads ".001" as
        # an extension again (caught in the headless check, 2026-09-21). So park whatever
        # holds the name, rename through temporary names, and make sure the name stuck.
        parked = []
        wanted = {name for _, name, _ in plan}
        mine = {m for m, _, _ in plan}
        for m in bpy.data.materials:
            if m not in mine and m.name in wanted:
                parked.append([m, m.name])
                m.name = m.name + "__dlsc_parked"
        for i, (m, _, _) in enumerate(plan):
            m.name = f"__dlsc_tmp_{i}"
        for m, name, _ in plan:
            m.name = name
        try:
            wrong = [m.name for m, name, _ in plan if m.name != name]
            if wrong:
                self.report({"ERROR"}, tr("Could not rename the materials for the export: {names}",
                                          names=", ".join(wrong)))
                return {"CANCELLED"}
            bpy.ops.export_scene.fbx(
                filepath=fbx, use_selection=True, apply_unit_scale=True, global_scale=0.0254,
                object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, bake_anim=False,
                mesh_smooth_type="FACE", path_mode="COPY", embed_textures=False)
        finally:
            for m, _, was in plan:
                m.name = was
            for m, was in parked:
                m.name = was
        if len(obj.data.polygons) == 0:
            self.report({"ERROR"}, tr("The mesh has no faces"))
            return {"CANCELLED"}

        p = _props(ctx.scene)
        remaps, plain = [], []
        for m, name, _ in plan:
            path, has_color, resized = _write_vmat(m, out_dir, name, p, manual=len(plan) == 1)
            remaps.append((name, path))
            if not has_color:
                plain.append(m.name)
            for note in resized:
                self.report({"INFO"}, note)
        if plain:
            # not a failure: the material's own colour is used. Just say so
            self.report({"WARNING"}, tr("No colour texture on: {names} (the material's own colour is used)",
                                        names=", ".join(plain[:4]) + ("…" if len(plain) > 4 else "")))

        # vmdl from cinna's template: swap the FBX name and rewrite the remap table
        with open(os.path.join(ASSETS, "template.vmdl"), encoding="utf-8") as f:
            txt = f.read()
        txt = txt.replace("models/props_gameplay/soul_container/cinnamon2s.fbx", f"{MOD_PATH.rsplit('/', 1)[0]}/{fbx_name}.fbx")
        t = TAB * 7
        table = "".join(f'{t}{{\n{t}{TAB}from = "{n}.vmat"\n{t}{TAB}to = "{path}"\n{t}}},\n'
                        for n, path in remaps)
        one = (f'{t}{{\n{t}{TAB}from = "cinnamoroll.vmat"\n'
               f'{t}{TAB}to = "models/props_gameplay/soul_container/materials/cinna.vmat"\n{t}}},\n')
        assert txt.count(one) == 1, "template.vmdl's remap table is not where it was"
        txt = txt.replace(one, table)
        vmdl = os.path.join(out_dir, "soul_container.vmdl")
        with open(vmdl, "w", encoding="utf-8") as f:
            f.write(txt)

        ctx.scene["dlsc_last_export"] = out_dir
        ctx.scene["dlsc_vmdl"] = vmdl
        self.report({"INFO"}, tr("Exported: {path}", path=out_dir))
        return {"FINISHED"}


# ---------- 4b. compile ----------

class DLSC_OT_compile(bpy.types.Operator):
    bl_idname = "dlsc.compile"
    bl_label = "Compile"
    bl_description = "Turn the vmdl and vmat into vmdl_c / vmat_c with the CSDK 12 resourcecompiler (Steam must be running)"

    def execute(self, ctx):
        import subprocess
        vmdl = ctx.scene.get("dlsc_vmdl") or os.path.join(content_dir(ctx.scene), "soul_container.vmdl")
        if not os.path.exists(vmdl):
            self.report({"ERROR"}, tr("Press \"Export\" first"))
            return {"CANCELLED"}
        exe = compiler_exe(ctx.scene)
        if not os.path.exists(exe):
            self.report({"ERROR"}, tr("resourcecompiler is missing: {path}", path=exe))
            return {"CANCELLED"}
        log_path = os.path.join(content_dir(ctx.scene), "compile.log")
        try:
            r = subprocess.run([exe, "-i", vmdl, "-f", "-nop4"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600, cwd=os.path.dirname(exe))
            out = (r.stdout or "") + (r.stderr or "")
        except Exception as e:
            self.report({"ERROR"}, tr("The compiler did not run: {err}", err=str(e)[:200]))
            return {"CANCELLED"}
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(out)
        vmdl_c = os.path.join(game_dir(ctx.scene), *MOD_PATH.split("/")[:-1], "soul_container.vmdl_c")
        warns = [l.strip() for l in out.splitlines() if "COMPILE WARNING" in l or "ERROR:" in l]
        if warns:
            self.report({"ERROR"}, tr("The compiler complains: {msg}", msg=" / ".join(warns)[:300]))
            return {"CANCELLED"}
        if os.path.exists(vmdl_c):
            ctx.scene["dlsc_vmdl_c"] = vmdl_c
            self.report({"INFO"}, tr("Compiled: {path}", path=vmdl_c))
            return {"FINISHED"}
        tail = [l for l in out.splitlines() if l.strip()][-3:]
        self.report({"ERROR"}, tr("No vmdl_c came out. See compile.log: {tail}", tail=" / ".join(tail)[:300]))
        return {"CANCELLED"}


# ---------- 4c. pack into a vpk ----------

def _vpk_write(entries, out):
    """entries: [(in-game path, bytes)] → VPK v2 (written the same way as the sound mod's tools/pack.py)"""
    import struct, zlib, hashlib
    tree = b""
    blob = b""
    by_ext = {}
    for path, data in entries:
        d, name = path.rsplit("/", 1)
        name, ext = name.rsplit(".", 1)
        by_ext.setdefault(ext, {}).setdefault(d, []).append((name, data))
    for ext, dirs in by_ext.items():
        tree += ext.encode() + b"\x00"
        for d, files in dirs.items():
            tree += d.encode() + b"\x00"
            for name, data in files:
                tree += name.encode() + b"\x00"
                tree += struct.pack("<IHHII", zlib.crc32(data) & 0xFFFFFFFF, 0, 0x7FFF, len(blob), len(data)) + b"\xff\xff"
                blob += data
            tree += b"\x00"
        tree += b"\x00"
    tree += b"\x00"
    header = struct.pack("<IIIIIII", 0x55AA1234, 2, len(tree), len(blob), 0, 48, 0)
    body = header + tree + blob
    other = hashlib.md5(tree).digest() + hashlib.md5(b"").digest()
    with open(out, "wb") as f:
        f.write(body + other + hashlib.md5(body + other).digest())


def _vpk_read(path):
    """VPK v2 (single file, archive 0x7fff) → [(in-game path, bytes)]"""
    import struct
    with open(path, "rb") as f:
        sig, ver, treelen = struct.unpack("<III", f.read(12))
        assert sig == 0x55AA1234
        if ver == 2:
            f.read(16)
        tree_start = f.tell()
        entries = []

        def cstr():
            b = bytearray()
            while True:
                c = f.read(1)
                if c in (b"\x00", b""):
                    return b.decode("utf-8")
                b += c
        while True:
            ext = cstr()
            if not ext:
                break
            while True:
                d = cstr()
                if not d:
                    break
                while True:
                    name = cstr()
                    if not name:
                        break
                    crc, pre, aidx, aoff, alen = struct.unpack("<IHHII", f.read(16))
                    f.read(pre)
                    f.read(2)
                    entries.append(((d + "/" if d != " " else "") + name + "." + ext, aoff, alen))
        data_start = tree_start + treelen
        out = []
        for p, off, ln in entries:
            f.seek(data_start + off)
            out.append((p, f.read(ln)))
    return out


class DLSC_OT_pack(bpy.types.Operator):
    bl_idname = "dlsc.pack"
    bl_label = "Pack into vpk"
    bl_description = "Collect the compiled models/ into a vpk (the shape Deadlock Mod Manager takes)"

    def execute(self, ctx):
        p = _props(ctx.scene)
        gd = game_dir(ctx.scene)
        root = os.path.join(gd, "models")
        if not os.path.exists(os.path.join(gd, *MOD_PATH.split("/")[:-1], "soul_container.vmdl_c")):
            self.report({"ERROR"}, tr("Compile it first"))
            return {"CANCELLED"}
        entries = []
        for r, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith("_c"):
                    continue
                full = os.path.join(r, fn)
                rel = os.path.relpath(full, gd).replace("\\", "/")
                with open(full, "rb") as f:
                    entries.append((rel, f.read()))
        if p.include_fix:
            entries += _vpk_read(os.path.join(ASSETS, "rotation_fix.vpk"))
        out_dir = bpy.path.abspath(p.out_dir) or os.path.expanduser("~")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, f"{p.mod_name}.vpk")
        _vpk_write(entries, out)
        ctx.scene["dlsc_vpk"] = out
        self.report({"INFO"}, tr("Packed: {path} ({n} files)", path=out, n=len(entries)))
        return {"FINISHED"}


# ---------- 4. build the mod (export → compile → pack) ----------

class DLSC_OT_build(bpy.types.Operator):
    bl_idname = "dlsc.build"
    bl_label = "Build the mod"
    bl_description = "Export, compile and pack in one go. If it stops, it says why"

    def execute(self, ctx):
        for op, name in ((bpy.ops.dlsc.export, "export"), (bpy.ops.dlsc.compile, "compile"), (bpy.ops.dlsc.pack, "pack")):
            try:
                r = op()
            except RuntimeError as e:
                self.report({"ERROR"}, tr("Stopped at {step}: {err}", step=tr(name),
                                          err=str(e).replace("Error: ", "")[:300]))
                return {"CANCELLED"}
            if "FINISHED" not in r:
                self.report({"ERROR"}, tr("Stopped at {step}", step=tr(name)))
                return {"CANCELLED"}
        self.report({"INFO"}, tr("The mod is ready: {path}", path=ctx.scene.get("dlsc_vpk")))
        return {"FINISHED"}


# ---------- the panel ----------

def _fold(layout, p, prop, label, icon="NONE"):
    """A box with a header you can click to open and close. Returns the box only when open."""
    box = layout.box()
    row = box.row(align=True)
    row.prop(p, prop, text="", emboss=False,
             icon="TRIA_DOWN" if getattr(p, prop) else "TRIA_RIGHT")
    row.label(text=label, icon=icon)
    return box if getattr(p, prop) else None


class DLSC_PT_panel(bpy.types.Panel):
    bl_label = "Deadlock Soul Container"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Soul Container"

    def draw(self, ctx):
        lay = self.layout
        p = _props(ctx.scene)
        obj = ctx.active_object
        mesh = obj if (obj and obj.type == "MESH" and not is_reference(obj)) else None

        # 1. pick a mesh and make it a soul container
        box = lay.box()
        box.label(text=tr("1. Pick a mesh and press"), icon="MESH_DATA")
        col = box.column(align=True)
        col.label(text=(tr("Selected: {name}", name=mesh.name) if mesh else tr("Nothing selected")),
                  icon="OBJECT_DATA" if mesh else "BLANK1")
        col.operator(DLSC_OT_make.bl_idname, text=tr("Make it a soul container"), icon="SHADERFX")
        col.label(text=tr("Summons joint1, binds it, matches the size and centres it."))
        # where am I? The made copy, if there is one for what is selected
        made = mesh if (mesh and any(c.name == GEN_COLLECTION for c in mesh.users_collection)) else None
        if made is None and mesh is not None:
            made = made_from(mesh)
        if made is not None:
            col.label(text=tr("Made: {name}", name=made.name), icon="CHECKMARK")
            col.label(text=tr("The look can be set any time — it is kept when you press again."),
                      icon="INFO")

        # 2. check it
        box = lay.box()
        box.label(text=tr("2. Check it"), icon="VIEWZOOM")
        box.operator(DLSC_OT_inspect.bl_idname, text=tr("Check"), icon="CHECKMARK")
        rows = ctx.scene.get("dlsc_inspect")
        if rows:
            col = box.column(align=True)
            for r in rows:
                k, _, t = r.partition("｜")
                # NOTE is not a fault — the exclamation mark made it look like one
                col.label(text=t, icon={"OK": "CHECKMARK", "NG": "CANCEL"}.get(k, "INFO"))

        # 3. build the mod
        box = lay.box()
        box.label(text=tr("3. Build the mod"), icon="PLAY")
        box.prop(p, "mod_name", text=tr("Mod name"))
        box.prop(p, "out_dir", text=tr("vpk goes to"))
        if not csdk_root():
            warn = box.column(align=True)
            warn.label(text=tr("The CSDK 12 folder is not set yet"), icon="ERROR")
            warn.label(text=tr("Edit > Preferences > Add-ons > Deadlock Soul Container"))
        box.operator(DLSC_OT_build.bl_idname, text=tr("Build the mod"), icon="PLAY")
        vpk = ctx.scene.get("dlsc_vpk")
        if vpk:
            box.label(text=os.path.basename(vpk), icon="CHECKMARK")

        lay.separator()

        # material
        box = _fold(lay, p, "show_material", tr("Material (vmat)"), icon="MATERIAL")
        if box:
            mats = [m for m in mesh.data.materials if m] if mesh else []
            mat = mats[0] if mats else None
            auto = material_images(mat, p, manual=len(mats) == 1) if mat else (None, None, None)
            if len(mats) > 1:
                box.label(text=tr("{n} materials — each one reads its own image", n=len(mats)), icon="MATERIAL")
                for m in mats[:6]:
                    img = _real(_linked_image(m, "Base Color"))
                    box.label(text=f"{m.name}: {img.name if img else tr('none')}",
                              icon="CHECKMARK" if img else "INFO")
            if mat is None:
                box.label(text=tr("No material on this mesh — the button below adds one"), icon="INFO")
            box.label(text=tr("Open an image file. It is wired into the material for you."),
                      icon="INFO")
            for prop, label, img in (("tex_color", tr("Base Color"), auto[0]),
                                     ("tex_normal", tr("Normal"), auto[1]),
                                     ("tex_rough", tr("Roughness"), auto[2])):
                if len(mats) > 1:
                    break
                col = box.column(align=True)
                col.label(text=f"{label}: " + (img.name if img else tr("none")),
                          icon="CHECKMARK" if img else "BLANK1")
                col.template_ID(p, prop, new="image.new", open="image.open")
            if len(mats) <= 1:
                box.operator(DLSC_OT_material.bl_idname, text=tr("Re-apply the picked images"),
                             icon="NODE_MATERIAL")
            if auto[2] is None and p.tex_rough is None:
                box.prop(p, "roughness", text=tr("Roughness (flat)"))
            box.prop(p, "metalness", text=tr("Metallic"))
            box.prop(p, "self_illum", text=tr("Self-illumination"))
            box.prop(p, "saturation", text=tr("Saturation"))

        # settings
        box = _fold(lay, p, "show_settings", tr("Settings"), icon="PREFERENCES")
        if box:
            box.prop(p, "include_fix", text=tr("Include the rotation fix particles"))
            pr = prefs()
            if pr is not None:
                box.prop(pr, "csdk_root", text=tr("CSDK 12 folder"))
            box.prop(p, "addon_name", text=tr("Addon name"))
            row = box.row(align=True)
            row.label(text=tr("One at a time:"))
            row.operator(DLSC_OT_export.bl_idname, text=tr("Export"))
            row.operator(DLSC_OT_compile.bl_idname, text=tr("Compile"))
            row.operator(DLSC_OT_pack.bl_idname, text=tr("vpk"))


CLASSES = (DLSC_Prefs, DLSC_Props, DLSC_OT_make, DLSC_OT_material, DLSC_OT_inspect,
           DLSC_OT_export, DLSC_OT_compile, DLSC_OT_pack, DLSC_OT_build, DLSC_PT_panel)


def register():
    i18n.register()
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.dlsc = bpy.props.PointerProperty(type=DLSC_Props)


def unregister():
    del bpy.types.Scene.dlsc
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
    i18n.unregister()
