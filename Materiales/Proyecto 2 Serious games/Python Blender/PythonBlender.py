import bpy
import bmesh
import math
from mathutils import Vector, Euler
from mathutils.noise import noise as perlin_noise

# =====================================================
# FULL SCENE WIPE (objects + datablocks)
# =====================================================
def full_wipe_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False, confirm=False)

    for col in list(bpy.data.collections):
        try:
            bpy.data.collections.remove(col)
        except:
            pass

    for block in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.textures,
        bpy.data.images,
        bpy.data.lights,
        bpy.data.cameras,
        bpy.data.curves,
        bpy.data.worlds,
    ):
        for datablock in list(block):
            try:
                block.remove(datablock)
            except:
                pass

    for _ in range(5):
        try:
            bpy.ops.outliner.orphans_purge(do_recursive=True, do_local_ids=True, do_linked_ids=True)
        except:
            try:
                bpy.ops.outliner.orphans_purge(do_recursive=True)
            except:
                break


# =====================================================
# TERRAIN CONFIG
# =====================================================
GRID_X = 200
GRID_Y = 200
CELL_SIZE = 1.0

NOISE_SCALE = 0.035
HEIGHT = 10.0
OCTAVES = 6
LACUNARITY = 2.0
GAIN = 0.5

CENTER_GRID = True

TERRAIN_NAME = "Terrain"
TERRAIN_COLLECTION = "Terrain"

SEA_LEVEL = 0.0

# Color bands (RGBA)
COLOR_DEEP_WATER  = (0.02, 0.08, 0.25, 1.0)
COLOR_SHALLOW     = (0.08, 0.25, 0.55, 1.0)
COLOR_SAND        = (0.78, 0.72, 0.52, 1.0)
COLOR_MOUNTAIN    = (0.22, 0.28, 0.20, 1.0)
COLOR_SNOW        = (0.95, 0.95, 0.95, 1.0)

SUBSURF_LEVEL = 1

# Camera
CAM_LOC = (100.0, 0.0, 3.5)
CAM_ROT_DEG = (90.0, 0.0, 90.0)

# Water volume box
WATER_MARGIN = 25.0
WATER_DEPTH = 20.0           # how deep the water volume goes below SEA_LEVEL
WATER_SURFACE_THICKNESS = 0.0  # set >0 if you want a "cap" slab; 0 uses only volume
WATER_IOR = 1.333
WATER_DENSITY = 0.08         # overall scattering density (inside-water look)
WATER_ANISOTROPY = 0.65      # forward scattering
WATER_ABS_COLOR = (0.02, 0.10, 0.16, 1.0)  # absorption tint
WATER_ABS_DENSITY = 0.35

# Clouds
CLOUD_ALTITUDE = 5.0
CLOUD_SIZE = 520.0
CLOUD_THICKNESS = 55.0

CLOUD_THIN_Z = CLOUD_ALTITUDE + 10.0
CLOUD_THIN_THICKNESS = 0.7
CLOUD_THIN_SUBDIV = 6
CLOUD_THIN_DISP_STRENGTH = 1.2
CLOUD_THIN_NOISE_SCALE = 30.0

CLOUD_DENSITY = 0.06
CLOUD_ANISOTROPY = 0.35
CLOUD_DETAIL_SCALE = 6.0
CLOUD_BASE_SCALE = 0.01
CLOUD_THRESHOLD = 0.52
CLOUD_SOFTNESS = 0.22


# =====================================================
# UTIL
# =====================================================
def lerp(a, b, t):
    return a + (b - a) * t

def lerp4(c1, c2, t):
    return (
        lerp(c1[0], c2[0], t),
        lerp(c1[1], c2[1], t),
        lerp(c1[2], c2[2], t),
        lerp(c1[3], c2[3], t),
    )

def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

def safe_set_input(bsdf, key_candidates, value):
    keys = set(bsdf.inputs.keys())
    for k in key_candidates:
        if k in keys and bsdf.inputs.get(k) is not None:
            bsdf.inputs[k].default_value = value
            return True
    return False

def fbm(x, y):
    amp = 1.0
    freq = 1.0
    total = 0.0
    norm = 0.0
    for _ in range(OCTAVES):
        n = perlin_noise(Vector((x * NOISE_SCALE * freq,
                                 y * NOISE_SCALE * freq,
                                 0.0)))
        total += n * amp
        norm += amp
        amp *= GAIN
        freq *= LACUNARITY
    return total / norm if norm else 0.0


# =====================================================
# HEIGHT -> COLOR
# =====================================================
def color_from_height(h, hmin, hmax):
    t_sea   = SEA_LEVEL
    t_shal  = lerp(hmin, t_sea, 0.55)
    t_deep  = hmin
    t_mtn   = lerp(t_sea, hmax, 0.55)
    t_snow  = lerp(t_sea, hmax, 0.82)

    if h <= t_shal:
        t = clamp01((h - t_deep) / (t_shal - t_deep + 1e-9))
        return lerp4(COLOR_DEEP_WATER, COLOR_SHALLOW, t)
    elif h <= t_sea:
        t = clamp01((h - t_shal) / (t_sea - t_shal + 1e-9))
        return lerp4(COLOR_SHALLOW, COLOR_SAND, t)
    elif h <= t_mtn:
        t = clamp01((h - t_sea) / (t_mtn - t_sea + 1e-9))
        return lerp4(COLOR_SAND, COLOR_MOUNTAIN, t)
    elif h <= t_snow:
        t = clamp01((h - t_mtn) / (t_snow - t_mtn + 1e-9))
        return lerp4(COLOR_MOUNTAIN, COLOR_SNOW, t)
    else:
        return COLOR_SNOW


# =====================================================
# MATERIALS
# =====================================================
def make_terrain_material(color_attr_name="terrain_col"):
    mat = bpy.data.materials.new("MAT_Terrain")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links

    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (520, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (240, 0)

    attr = nodes.new("ShaderNodeAttribute")
    attr.location = (-380, 40)
    attr.attribute_name = color_attr_name
    if attr.outputs.get("Color") and bsdf.inputs.get("Base Color"):
        links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])

    # subtle bump
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-900, -160)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-700, -160)
    mapping.inputs["Scale"].default_value = (2.0, 2.0, 2.0)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-500, -160)
    noise.inputs["Scale"].default_value = 10.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.55

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-140, -260)
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.2

    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    safe_set_input(bsdf, ["Roughness"], 0.9)
    safe_set_input(bsdf, ["Specular", "Specular IOR Level"], 0.12)
    return mat


def setup_world_sky(strength=0.5):
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True

    nt = world.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    out.location = (400, 0)

    bg = nodes.new("ShaderNodeBackground")
    bg.location = (150, 0)
    bg.inputs["Strength"].default_value = strength

    sky = nodes.new("ShaderNodeTexSky")
    sky.location = (-150, 0)

    for candidate in ("MULTIPLE_SCATTERING", "PREETHAM", "HOSEK_WILKIE", "SINGLE_SCATTERING"):
        try:
            sky.sky_type = candidate
            break
        except:
            continue

    links.new(sky.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], out.inputs["Surface"])


def make_water_volume_material():
    """
    Volume-only water material:
    - Surface: optional Principled BSDF (for refraction / surface response)
    - Volume: Volume Scatter + Volume Absorption (camera-inside-water friendly)
    """
    mat = bpy.data.materials.new("MAT_WaterVolume")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links

    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (650, 0)

    # Optional surface (helps when camera is outside / near surface)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (220, 140)

    safe_set_input(bsdf, ["Base Color"], (0.02, 0.07, 0.10, 1.0))
    safe_set_input(bsdf, ["Roughness"], 0.02)
    safe_set_input(bsdf, ["IOR"], WATER_IOR)
    safe_set_input(bsdf, ["Transmission", "Transmission Weight"], 1.0)
    safe_set_input(bsdf, ["Specular", "Specular IOR Level"], 0.5)

    # Small normal ripple for surface cue
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-900, 260)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-700, 260)
    mapping.inputs["Scale"].default_value = (2.0, 2.0, 2.0)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-500, 260)
    noise.inputs["Scale"].default_value = 10.0
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.5
    bump = nodes.new("ShaderNodeBump")
    bump.location = (-150, 120)
    bump.inputs["Strength"].default_value = 0.15
    bump.inputs["Distance"].default_value = 0.1

    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Volume scatter + absorption
    vscatter = nodes.new("ShaderNodeVolumeScatter")
    vscatter.location = (220, -120)
    vscatter.inputs["Density"].default_value = WATER_DENSITY
    vscatter.inputs["Anisotropy"].default_value = WATER_ANISOTROPY

    vabs = nodes.new("ShaderNodeVolumeAbsorption")
    vabs.location = (220, -300)
    vabs.inputs["Density"].default_value = WATER_ABS_DENSITY
    vabs.inputs["Color"].default_value = WATER_ABS_COLOR

    addv = nodes.new("ShaderNodeAddShader")
    addv.location = (460, -210)
    links.new(vscatter.outputs["Volume"], addv.inputs[0])
    links.new(vabs.outputs["Volume"], addv.inputs[1])

    # Hook outputs
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    links.new(addv.outputs["Shader"], out.inputs["Volume"])

    # Eevee refraction friendliness
    try:
        mat.use_screen_refraction = True
    except:
        pass
    try:
        mat.blend_method = 'BLEND'
    except:
        pass

    return mat


def make_cloud_volume_material():
    """
    Procedural cloud volume:
    - Noise-based density (thin & thick in one material)
    - Volume Scatter for "scattering"
    """
    mat = bpy.data.materials.new("MAT_Clouds")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (760, 0)

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-980, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-780, 0)
    mapping.inputs["Scale"].default_value = (CLOUD_BASE_SCALE, CLOUD_BASE_SCALE, CLOUD_BASE_SCALE)

    # Big shapes
    noise_big = nodes.new("ShaderNodeTexNoise")
    noise_big.location = (-560, 80)
    noise_big.inputs["Scale"].default_value = 0.9
    noise_big.inputs["Detail"].default_value = 2.0
    noise_big.inputs["Roughness"].default_value = 0.55

    # Fine details
    noise_small = nodes.new("ShaderNodeTexNoise")
    noise_small.location = (-560, -120)
    noise_small.inputs["Scale"].default_value = CLOUD_DETAIL_SCALE
    noise_small.inputs["Detail"].default_value = 8.0
    noise_small.inputs["Roughness"].default_value = 0.6

    # Combine + remap to density
    mult = nodes.new("ShaderNodeMath")
    mult.location = (-300, -40)
    mult.operation = 'MULTIPLY'
    mult.inputs[1].default_value = 1.0

    # Threshold (controls thick vs thin)
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-80, -40)
    # Smooth-ish ramp
    try:
        ramp.color_ramp.elements[0].position = max(0.0, min(1.0, CLOUD_THRESHOLD - CLOUD_SOFTNESS))
        ramp.color_ramp.elements[1].position = max(0.0, min(1.0, CLOUD_THRESHOLD + CLOUD_SOFTNESS))
        ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    except:
        pass

    dens_mul = nodes.new("ShaderNodeMath")
    dens_mul.location = (160, -40)
    dens_mul.operation = 'MULTIPLY'
    dens_mul.inputs[1].default_value = CLOUD_DENSITY

    vscatter = nodes.new("ShaderNodeVolumeScatter")
    vscatter.location = (420, -40)
    vscatter.inputs["Density"].default_value = 1.0  # driven
    vscatter.inputs["Anisotropy"].default_value = CLOUD_ANISOTROPY
    vscatter.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    vabs = nodes.new("ShaderNodeVolumeAbsorption")
    vabs.location = (420, -220)
    vabs.inputs["Density"].default_value = 0.02
    vabs.inputs["Color"].default_value = (0.95, 0.97, 1.0, 1.0)

    addv = nodes.new("ShaderNodeAddShader")
    addv.location = (620, -120)

    # Wiring
    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_big.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_small.inputs["Vector"])

    # multiply big * small
    links.new(noise_big.outputs["Fac"], mult.inputs[0])
    links.new(noise_small.outputs["Fac"], mult.inputs[1])

    links.new(mult.outputs["Value"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], dens_mul.inputs[0])

    # drive scatter density
    links.new(dens_mul.outputs["Value"], vscatter.inputs["Density"])

    links.new(vscatter.outputs["Volume"], addv.inputs[0])
    links.new(vabs.outputs["Volume"], addv.inputs[1])

    links.new(addv.outputs["Shader"], out.inputs["Volume"])

    return mat


# =====================================================
# RENDER SETTINGS (volumetrics)
# =====================================================
def enable_volumetrics():
    scn = bpy.context.scene

    # Eevee (if active)
    try:
        ee = scn.eevee
        if hasattr(ee, "use_volumetric_lights"):
            ee.use_volumetric_lights = True
        if hasattr(ee, "use_volumetric_shadows"):
            ee.use_volumetric_shadows = True

        # quality vs speed (keep moderate)
        if hasattr(ee, "volumetric_tile_size"):
            ee.volumetric_tile_size = '4'  # '2','4','8' depending on version
        if hasattr(ee, "volumetric_samples"):
            ee.volumetric_samples = 64
        if hasattr(ee, "volumetric_sample_distribution"):
            ee.volumetric_sample_distribution = 0.8
        if hasattr(ee, "volumetric_light_clamp"):
            ee.volumetric_light_clamp = 0.0

        if hasattr(ee, "use_ssr"):
            ee.use_ssr = True
        if hasattr(ee, "use_ssr_refraction"):
            ee.use_ssr_refraction = True
        if hasattr(ee, "ssr_thickness"):
            ee.ssr_thickness = 2.0
    except:
        pass


# =====================================================
# TERRAIN MESH (single mesh)
# =====================================================
def create_terrain_mesh():
    col = bpy.data.collections.new(TERRAIN_COLLECTION)
    bpy.context.scene.collection.children.link(col)

    mesh = bpy.data.meshes.new(TERRAIN_NAME)
    obj = bpy.data.objects.new(TERRAIN_NAME, mesh)
    col.objects.link(obj)

    bm = bmesh.new()

    ox = -(GRID_X - 1) * CELL_SIZE * 0.5 if CENTER_GRID else 0.0
    oy = -(GRID_Y - 1) * CELL_SIZE * 0.5 if CENTER_GRID else 0.0

    verts = [[None] * GRID_Y for _ in range(GRID_X)]
    hmin =  1e9
    hmax = -1e9

    for x in range(GRID_X):
        for y in range(GRID_Y):
            wx = ox + x * CELL_SIZE
            wy = oy + y * CELL_SIZE
            wz = fbm(x, y) * HEIGHT
            hmin = min(hmin, wz)
            hmax = max(hmax, wz)
            verts[x][y] = bm.verts.new((wx, wy, wz))

    bm.verts.ensure_lookup_table()

    for x in range(GRID_X - 1):
        for y in range(GRID_Y - 1):
            v1 = verts[x][y]
            v2 = verts[x + 1][y]
            v3 = verts[x + 1][y + 1]
            v4 = verts[x][y + 1]
            try:
                bm.faces.new((v1, v2, v3, v4))
            except:
                pass

    bm.faces.ensure_lookup_table()
    bm.to_mesh(mesh)
    bm.free()

    for p in mesh.polygons:
        p.use_smooth = True

    color_attr_name = "terrain_col"
    color_attr = None
    try:
        if hasattr(mesh, "color_attributes"):
            if color_attr_name in mesh.color_attributes:
                mesh.color_attributes.remove(mesh.color_attributes[color_attr_name])
            color_attr = mesh.color_attributes.new(
                name=color_attr_name,
                type='BYTE_COLOR',
                domain='CORNER'
            )
        else:
            if not mesh.vertex_colors:
                mesh.vertex_colors.new(name=color_attr_name)
            color_attr = mesh.vertex_colors[color_attr_name]
    except:
        color_attr = None

    if color_attr is not None:
        loops = mesh.loops
        polys = mesh.polygons
        data = color_attr.data

        for poly in polys:
            for li in poly.loop_indices:
                vi = loops[li].vertex_index
                z = mesh.vertices[vi].co.z
                c = color_from_height(z, hmin, hmax)
                try:
                    data[li].color = c
                except:
                    data[li].color = (c[0], c[1], c[2], c[3])

    mat = make_terrain_material(color_attr_name=color_attr_name)
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    try:
        mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
        mod.levels = SUBSURF_LEVEL
        mod.render_levels = SUBSURF_LEVEL
        mod.subdivision_type = 'CATMULL_CLARK'
        # Do NOT apply (keeps it faster + stable)
    except:
        pass

    return obj, (hmin, hmax), (ox, oy)


# =====================================================
# WATER BOX (volume)
# =====================================================
def create_water_box(terrain_bounds, water_z=SEA_LEVEL, margin=WATER_MARGIN, depth=WATER_DEPTH):
    (ox, oy) = terrain_bounds

    width = (GRID_X - 1) * CELL_SIZE + margin * 2.0
    depth_xy = (GRID_Y - 1) * CELL_SIZE + margin * 2.0

    cx = ox + (GRID_X - 1) * CELL_SIZE * 0.5
    cy = oy + (GRID_Y - 1) * CELL_SIZE * 0.5

    # Build a box volume: top at water_z, bottom at water_z - depth
    z_top = water_z + max(0.0, WATER_SURFACE_THICKNESS)
    z_bot = water_z - depth
    cz = (z_top + z_bot) * 0.5
    hz = (z_top - z_bot) * 0.5

    mesh = bpy.data.meshes.new("WaterBox")
    obj = bpy.data.objects.new("WaterBox", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    # scale cube to desired dimensions
    for v in bm.verts:
        v.co.x *= width * 0.5
        v.co.y *= depth_xy * 0.5
        v.co.z *= hz if hz > 1e-6 else 0.01

    # translate to position
    for v in bm.verts:
        v.co.x += cx
        v.co.y += cy
        v.co.z += cz

    bm.to_mesh(mesh)
    bm.free()

    for p in mesh.polygons:
        p.use_smooth = True

    mat = make_water_volume_material()
    obj.data.materials.append(mat)

    # for volume objects: render both sides
    try:
        obj.data.use_auto_smooth = False
    except:
        pass

    return obj


# =====================================================
# CLOUDS
# =====================================================
def create_cloud_volume():
    mesh = bpy.data.meshes.new("CloudVolume")
    obj = bpy.data.objects.new("CloudVolume", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)

    # scale to big volume
    for v in bm.verts:
        v.co.x *= CLOUD_SIZE * 0.5
        v.co.y *= CLOUD_SIZE * 0.5
        v.co.z *= CLOUD_THICKNESS * 0.5

    # lift it
    for v in bm.verts:
        v.co.z += CLOUD_ALTITUDE

    bm.to_mesh(mesh)
    bm.free()

    mat = make_cloud_volume_material()
    obj.data.materials.append(mat)

    return obj


def create_thin_cloud_sheet():
    """
    Thin displaced sheet layer:
    - plane with subdiv + displacement modifier (geometry displacement)
    - material is still volumetric-ish? For a sheet, we do alpha+principled with soft mask.
    """
    mesh = bpy.data.meshes.new("CloudSheet")
    obj = bpy.data.objects.new("CloudSheet", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    v1 = bm.verts.new((-CLOUD_SIZE * 0.5, -CLOUD_SIZE * 0.5, CLOUD_THIN_Z))
    v2 = bm.verts.new(( CLOUD_SIZE * 0.5, -CLOUD_SIZE * 0.5, CLOUD_THIN_Z))
    v3 = bm.verts.new(( CLOUD_SIZE * 0.5,  CLOUD_SIZE * 0.5, CLOUD_THIN_Z))
    v4 = bm.verts.new((-CLOUD_SIZE * 0.5,  CLOUD_SIZE * 0.5, CLOUD_THIN_Z))
    bm.faces.new((v1, v2, v3, v4))
    bm.to_mesh(mesh)
    bm.free()

    for p in mesh.polygons:
        p.use_smooth = True

    # Subdivide (modifier) for displacement
    try:
        sub = obj.modifiers.new(name="Subdiv", type='SUBSURF')
        sub.levels = CLOUD_THIN_SUBDIV
        sub.render_levels = CLOUD_THIN_SUBDIV
        sub.subdivision_type = 'SIMPLE'
    except:
        pass

    # Displace modifier using procedural texture
    tex = bpy.data.textures.new("TEX_CloudDisp", type='CLOUDS')
    tex.noise_scale = CLOUD_THIN_NOISE_SCALE

    try:
        disp = obj.modifiers.new(name="Displace", type='DISPLACE')
        disp.texture = tex
        disp.strength = CLOUD_THIN_DISP_STRENGTH
        disp.mid_level = 0.0
    except:
        pass

    # Sheet material (soft alpha)
    mat = bpy.data.materials.new("MAT_CloudSheet")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (620, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (280, 40)
    safe_set_input(bsdf, ["Base Color"], (1.0, 1.0, 1.0, 1.0))
    safe_set_input(bsdf, ["Roughness"], 0.9)
    safe_set_input(bsdf, ["Specular", "Specular IOR Level"], 0.05)

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-860, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-660, 0)
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.0)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-420, 0)
    noise.inputs["Scale"].default_value = 0.01
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.6

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-160, 0)
    try:
        ramp.color_ramp.elements[0].position = 0.48
        ramp.color_ramp.elements[1].position = 0.62
        ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    except:
        pass

    # Use ramp as alpha mask
    safe_set_input(bsdf, ["Alpha"], 1.0)

    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    # drive alpha
    if bsdf.inputs.get("Alpha") and ramp.outputs.get("Color"):
        links.new(ramp.outputs["Color"], bsdf.inputs["Alpha"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    obj.data.materials.append(mat)

    # Enable blend for alpha
    try:
        mat.blend_method = 'BLEND'
        mat.shadow_method = 'HASHED'
    except:
        pass

    return obj


# =====================================================
# CAMERA
# =====================================================
def create_camera(loc=(0, 0, 0), rot_deg=(0, 0, 0), name="Camera"):
    cam_data = bpy.data.cameras.new(name)
    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

    cam_obj.location = Vector(loc)
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = Euler(
        (math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2])),
        'XYZ'
    )

    bpy.context.scene.camera = cam_obj
    return cam_obj


# =====================================================
# RUN
# =====================================================
full_wipe_scene()

enable_volumetrics()

terrain_obj, (hmin, hmax), (ox, oy) = create_terrain_mesh()
setup_world_sky(strength=0.1)

# Water as a BOX volume (camera-inside friendly)
water_obj = create_water_box((ox, oy), water_z=SEA_LEVEL, margin=WATER_MARGIN, depth=WATER_DEPTH)

# Cloud layers:
# 1) Thick volumetric block
cloud_vol = create_cloud_volume()
# 2) Thin displaced sheet (geometry displacement)
cloud_sheet = create_thin_cloud_sheet()

cam_obj = create_camera(loc=CAM_LOC, rot_deg=CAM_ROT_DEG, name="Camera")

print("Done. Terrain min/max height:", hmin, hmax)