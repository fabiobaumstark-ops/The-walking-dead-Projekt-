"""Phase 1.6 – Hero-Kameras (Blockout-Version) + Draufsicht-Kamera. Werte in scripts/configs/kameras.json."""
import math

import bpy

import viertel_lib as V


def kamera(name, loc, yaw, lens, blende, fokus, shift_y=0.0, sensor=36):
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = sensor
    cd.lens = lens
    cd.shift_y = shift_y
    cd.clip_start = 0.1
    cd.clip_end = 3000
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = blende
    cd.dof.focus_distance = fokus
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, yaw)  # waagerecht: Vertikalen bleiben senkrecht
    V.collection("11_Kameras").objects.link(ob)
    return ob


def bauen():
    K = V.config("kameras.json")
    dach = {o.get("id"): o for o in bpy.data.objects if o.get("id")}
    for k in K["kameras"]:
        x, y, dz = k["pos"]
        if k.get("auf_dach"):
            b = dach[k["auf_dach"]]
            z = b.location.z + b["geschosse"] * 3.8 + dz
        else:
            z = V.h(x, y) + 0.05 + dz
        tx, ty = k["ziel"]
        yaw = math.atan2(ty - y, tx - x) - math.pi / 2
        ob = kamera(k["name"], (x, y, z), yaw, k["brennweite"], k["blende"], k["fokus_m"], k["shift_y"], K["sensor_mm"])
        ob["titel"] = k["titel"]
    u = K["uebersicht"]
    cd = bpy.data.cameras.new(u["name"])
    cd.type = "ORTHO"
    cd.ortho_scale = u["ortho_skala"]
    cd.clip_end = 2000
    ob = bpy.data.objects.new(u["name"], cd)
    ob.location = (u["mitte"][0], u["mitte"][1], 400)
    V.collection("11_Kameras").objects.link(ob)
    bpy.context.scene.camera = bpy.data.objects["CAM_Hero_01"]
