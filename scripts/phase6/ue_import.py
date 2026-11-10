"""Phase 6.1 – Import ins Unreal-Projekt (Unreal-Seite). Laeuft IM Unreal-Editor 5.8, nicht in Blender.

Start: Unreal-Editor -> Menue Tools -> "Execute Python Script..." -> diese Datei waehlen.
Voraussetzung: Plugin "Python Editor Script Plugin" aktiv (Edit -> Plugins), Export mit scripts/phase6/export_unreal.py.

Was passiert:
1. Texturen aus assets/ importieren (/Game/Viertel/Texturen), Normalmaps OpenGL -> Gruen kippen
2. Zwei Mastermaterialien bauen (M_Viertel_Basis, M_Viertel_Maske fuer Blaetter/Gras) + je Blender-Material eine Instanz
3. Alle Formen (FBX) importieren (/Game/Viertel/Meshes), Materialien zuweisen, Nanite/Kollision je Kategorie
4. Neues Level /Game/Viertel/Karten/L_Viertel_<Test|Alles>: Einzelobjekte als StaticMeshActor,
   viele gleiche Formen (Gras, Efeu, Bauteile) als EIN Actor mit Hierarchical-Instanced-Static-Mesh
5. Sonne, Himmel, Nebel, Feuerlicht, PlayerStart; alles speichern
Bei Fehlern: Output Log (Window -> Output Log) nach "VIERTEL" filtern und mir die Zeilen schicken.
Wiederholbar: vorhandene Assets werden wiederverwendet (NEU_IMPORT = True erzwingt Neuimport).
"""
import json
import os
import struct
import zlib

import unreal

# ------------------------------------------------------------------ Einstellungen
EXPORT = "unreal_test"          # "unreal_test" (Testpaket) oder "unreal" (ganzes Viertel)
NEU_IMPORT = False              # True: Meshes/Texturen neu importieren
NANITE = True                   # Nanite auf dem Mac ist bei Epic "Beta" (Apple Silicon M2+); bei Problemen False
NANITE_AB_FLAECHEN = 50000      # schwere Formen (Baeume, Gras, grosse Gebaeude)
EINZEL_BIS = 8                  # bis zu so vielen Platzierungen: einzelne Actors, darueber Instanzen
GRAS_AUSBLENDEN_CM = 9000       # Pflanzen-Instanzen ab dieser Entfernung ausblenden (Leistung)

try:
    REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
except NameError:  # falls __file__ fehlt: Pfad zum Projektordner hier eintragen
    REPO = os.path.expanduser("~/twd")
QUELLE = os.path.join(REPO, "export", EXPORT)
ZIEL = "/Game/Viertel"
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary


def log(*a):
    unreal.log("VIERTEL " + " ".join(str(x) for x in a))


def warn(*a):
    unreal.log_warning("VIERTEL " + " ".join(str(x) for x in a))


def asset_name(s):
    return "".join(c if c.isalnum() or c == "_" else "_" for c in s)[:90]


# ------------------------------------------------------------------ Import-Hilfen
def importieren(datei, ordner, name, optionen=None):
    pfad = f"{ordner}/{name}"
    if EAL.does_asset_exist(pfad) and not NEU_IMPORT:
        return EAL.load_asset(pfad)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", datei)
    t.set_editor_property("destination_path", ordner)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    if optionen is not None:
        t.set_editor_property("options", optionen)
    AT.import_asset_tasks([t])
    for p in t.get_editor_property("imported_object_paths") or []:
        a = EAL.load_asset(p)
        if a is not None and (optionen is None or isinstance(a, unreal.StaticMesh)):
            return a
    return EAL.load_asset(pfad)


def png(pfad, rgba):
    """Einfarbiges 4x4-PNG (nur Standardbibliothek) fuer Standard-Texturen der Mastermaterialien."""
    roh = b"".join(b"\x00" + bytes(rgba) * 4 for _ in range(4))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    with open(pfad, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(roh)) + chunk(b"IEND", b""))


TEX = {}


def textur(rel, rolle, opengl=False):
    """rolle: farbe (sRGB), rau/maske (linear), normal."""
    key = (rel, rolle)
    if key in TEX:
        return TEX[key]
    datei = rel if os.path.isabs(rel) else os.path.join(REPO, rel)
    if not os.path.exists(datei):
        warn("Textur fehlt", datei)
        TEX[key] = None
        return None
    name = "T_" + asset_name(os.path.splitext(os.path.basename(datei))[0]) + ("" if rolle != "normal" else "_N")
    tex = importieren(datei, f"{ZIEL}/Texturen", name)
    if tex is None:
        warn("Textur-Import fehlgeschlagen", datei)
    else:
        try:
            if rolle == "normal":
                tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
                tex.set_editor_property("srgb", False)
                tex.set_editor_property("flip_green_channel", bool(opengl))
            elif rolle in ("rau", "maske"):
                tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
                tex.set_editor_property("srgb", False)
            else:
                tex.set_editor_property("srgb", True)
        except Exception as e:  # noqa: BLE001
            warn("Textur-Einstellung", name, e)
    TEX[key] = tex
    return tex


# ------------------------------------------------------------------ Materialien
SAMPLER = {"farbe": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
           "rau": unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,
           "maske": unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,
           "normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL}
STANDARD = {}


def standard_texturen():
    os.makedirs(os.path.join(QUELLE, "standard"), exist_ok=True)
    for rolle, farbe in (("farbe", (255, 255, 255, 255)), ("rau", (255, 255, 255, 255)),
                         ("maske", (255, 255, 255, 255)), ("normal", (128, 128, 255, 255))):
        p = os.path.join(QUELLE, "standard", f"standard_{rolle}.png")
        png(p, farbe)
        STANDARD[rolle] = textur(p, rolle, False)


def master(name, maskiert):
    pfad = f"{ZIEL}/Materialien/{name}"
    if EAL.does_asset_exist(pfad) and not NEU_IMPORT:
        return EAL.load_asset(pfad)
    if EAL.does_asset_exist(pfad):
        EAL.delete_asset(pfad)
    m = AT.create_asset(name, f"{ZIEL}/Materialien", unreal.Material, unreal.MaterialFactoryNew())
    if maskiert:
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        m.set_editor_property("two_sided", True)
    x = -900

    def tparam(pname, rolle, y):
        e = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
        e.set_editor_property("parameter_name", pname)
        e.set_editor_property("texture", STANDARD[rolle])
        e.set_editor_property("sampler_type", SAMPLER[rolle])
        return e

    def sparam(pname, wert, y):
        e = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, x + 350, y)
        e.set_editor_property("parameter_name", pname)
        e.set_editor_property("default_value", wert)
        return e

    def mal(a, a_aus, b, b_aus, y):
        e = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, x + 600, y)
        MEL.connect_material_expressions(a, a_aus, e, "A")
        MEL.connect_material_expressions(b, b_aus, e, "B")
        return e

    farbe = tparam("Farbe", "farbe", -300)
    tint = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, x + 350, -200)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    MEL.connect_material_property(mal(farbe, "RGB", tint, "", -250), "", unreal.MaterialProperty.MP_BASE_COLOR)
    rau = tparam("Rau", "rau", 0)
    MEL.connect_material_property(mal(rau, "R", sparam("RauFaktor", 1.0, 80), "", 20), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(sparam("Metall", 0.0, 200), "", unreal.MaterialProperty.MP_METALLIC)
    normal = tparam("Normal", "normal", 350)
    MEL.connect_material_property(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
    if maskiert:
        maske = tparam("Maske", "maske", 650)
        MEL.connect_material_property(maske, "R", unreal.MaterialProperty.MP_OPACITY_MASK)
    MEL.recompile_material(m)
    return m


MI = {}


def material_instanz(name, info, masters):
    if name in MI:
        return MI[name]
    pfad = f"{ZIEL}/Materialien/Instanzen/MI_{name}"
    if EAL.does_asset_exist(pfad) and not NEU_IMPORT:
        MI[name] = EAL.load_asset(pfad)
        return MI[name]
    if EAL.does_asset_exist(pfad):
        EAL.delete_asset(pfad)
    mi = AT.create_asset(f"MI_{name}", f"{ZIEL}/Materialien/Instanzen", unreal.MaterialInstanceConstant,
                         unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, masters[bool(info.get("maske"))])
    tx = info.get("tex", {})
    for rolle, pname in (("farbe", "Farbe"), ("rau", "Rau"), ("normal", "Normal"), ("maske", "Maske")):
        if rolle in tx and (rolle != "maske" or info.get("maske")):
            t = textur(tx[rolle], rolle, info.get("normal_opengl", False))
            if t is not None:
                MEL.set_material_instance_texture_parameter_value(mi, pname, t)
    if "farbe" in tx:
        tint = (1.0, 1.0, 1.0)
    else:
        tint = info.get("basis", (0.5, 0.5, 0.5))
    MEL.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(*tint, 1.0))
    MEL.set_material_instance_scalar_parameter_value(mi, "RauFaktor", 1.0 if "rau" in tx else float(info.get("rau", 0.7)))
    MEL.set_material_instance_scalar_parameter_value(mi, "Metall", float(info.get("metall", 0.0)))
    MI[name] = mi
    return mi


# ------------------------------------------------------------------ Meshes
def fbx_optionen():
    o = unreal.FbxImportUI()
    for k, v in (("import_mesh", True), ("import_as_skeletal", False), ("import_materials", False),
                 ("import_textures", False), ("import_animations", False), ("create_physics_asset", False)):
        try:
            o.set_editor_property(k, v)
        except Exception:  # noqa: BLE001
            pass
    sm = o.get_editor_property("static_mesh_import_data")
    for k, v in (("combine_meshes", True), ("auto_generate_collision", False), ("generate_lightmap_u_vs", False),
                 ("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)):
        try:
            sm.set_editor_property(k, v)
        except Exception:  # noqa: BLE001
            pass
    return o


def mesh_einrichten(sm, form, mats):
    # Materialien: Slot-Namen = Blender-Materialnamen (bereinigt), sonst Reihenfolge
    slots = list(sm.get_editor_property("static_materials"))
    namen = [asset_name(str(s.get_editor_property("material_slot_name"))).lower() for s in slots]
    for k, mname in enumerate(form["mats"]):
        mi = mats.get(mname)
        if mi is None:
            continue
        idx = namen.index(mname.lower()) if mname.lower() in namen else (k if k < len(slots) else None)
        if idx is not None:
            sm.set_material(idx, mi)
    # Kollision: Gebaeude/Fahrzeuge/Sonstiges genau (Spieler laeuft darauf), Pflanzen/Figuren ohne
    try:
        bs = sm.get_editor_property("body_setup")
        if bs is not None:
            flag = unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if form["kategorie"] in ("gebaeude", "fahrzeug", "sonstiges") \
                else unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX
            bs.set_editor_property("collision_trace_flag", flag)
    except Exception as e:  # noqa: BLE001
        warn("Kollision", form["name"], e)
    # Nanite fuer schwere Formen
    if NANITE and form["flaechen"] >= NANITE_AB_FLAECHEN:
        try:
            ns = sm.get_editor_property("nanite_settings")
            ns.set_editor_property("enabled", True)
            sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            if hasattr(sub, "set_nanite_settings"):
                sub.set_nanite_settings(sm, ns, True)
            else:
                sm.set_editor_property("nanite_settings", ns)
        except Exception as e:  # noqa: BLE001
            warn("Nanite", form["name"], e)


# ------------------------------------------------------------------ Level
def tf(t):
    return unreal.Transform(location=unreal.Vector(t[0], t[1], t[2]),
                            rotation=unreal.Rotator(roll=t[3], pitch=t[4], yaw=t[5]),
                            scale=unreal.Vector(t[6], t[7], t[8]))


def instanz_actor(eas, sm, form, liste):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    actor = eas.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0))
    actor.set_actor_label(f"ISM_{form['name']}")
    wurzel = sds.k2_gather_subobject_data_for_instance(actor)[0]
    h, grund = sds.add_new_subobject(unreal.AddNewSubobjectParams(
        parent_handle=wurzel, new_class=unreal.HierarchicalInstancedStaticMeshComponent, blueprint_context=None))
    comp = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
    if comp is None:
        raise RuntimeError(f"Komponente nicht erzeugt: {grund}")
    comp.set_static_mesh(sm)
    ts = [tf(t) for t in liste]
    try:
        comp.add_instances(ts, False, True)
    except Exception:  # noqa: BLE001 - aeltere Signatur
        for t in ts:
            comp.add_instance(t)
    if form["kategorie"] in ("pflanze", "figur"):
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        if form["kategorie"] == "pflanze":
            comp.set_editor_property("instance_end_cull_distance", GRAS_AUSBLENDEN_CM)
            comp.set_editor_property("cast_shadow", form["flaechen"] > 2000)
    return actor


def einzel_actor(eas, sm, form, t):
    a = eas.spawn_actor_from_object(sm, unreal.Vector(t[0], t[1], t[2]), unreal.Rotator(roll=t[3], pitch=t[4], yaw=t[5]))
    a.set_actor_scale3d(unreal.Vector(t[6], t[7], t[8]))
    if form["kategorie"] in ("pflanze", "figur"):
        a.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return a


def umgebung(eas, sz):
    def spawn(klasse, ort=(0, 0, 0), rot=(0, 0, 0), label=None):
        a = eas.spawn_actor_from_class(klasse, unreal.Vector(*ort), unreal.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2]))
        if label:
            a.set_actor_label(label)
        a.set_folder_path("Viertel/Umgebung")
        return a
    for L in sz["licht"]:
        if L["typ"] == "SUN":
            a = spawn(unreal.DirectionalLight, (0, 0, 2000), L["blick"], "Sonne")
            c = a.get_component_by_class(unreal.DirectionalLightComponent)
            c.set_editor_property("intensity", 8.0)
            c.set_editor_property("use_temperature", True)
            c.set_editor_property("temperature", float(L.get("kelvin") or 5000))
            c.set_editor_property("source_angle", float(L.get("winkel", 1.0)))
            try:
                c.set_editor_property("atmosphere_sun_light", True)
            except Exception:  # noqa: BLE001
                pass
        elif L["typ"] == "POINT":
            a = spawn(unreal.PointLight, L["t"][:3], (0, 0, 0), L["name"])
            c = a.get_component_by_class(unreal.PointLightComponent)
            c.set_editor_property("intensity", 8000.0)
            c.set_editor_property("attenuation_radius", 1500.0)
            c.set_editor_property("use_temperature", True)
            c.set_editor_property("temperature", float(L.get("kelvin") or 2000))
    spawn(unreal.SkyAtmosphere, label="Himmel")
    sl = spawn(unreal.SkyLight, (0, 0, 500), label="Himmelslicht")
    try:
        sl.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    except Exception:  # noqa: BLE001
        pass
    nb = spawn(unreal.ExponentialHeightFog, (0, 0, 0), label="Dunst")
    fc = nb.get_component_by_class(unreal.ExponentialHeightFogComponent)
    for k, v in (("fog_density", 0.06), ("fog_height_falloff", 0.15), ("volumetric_fog", True),
                 ("volumetric_fog_scattering_distribution", 0.6)):
        try:
            fc.set_editor_property(k, v)
        except Exception as e:  # noqa: BLE001
            warn("Nebel", k, e)
    st = sz["start"]
    spawn(unreal.PlayerStart, (st["pos"][0], st["pos"][1], st["pos"][2] + 20), (0, 0, st["blick"][2]), "Start_CAM_Hero_01")


# ------------------------------------------------------------------ Ablauf
def main():
    sz = json.load(open(os.path.join(QUELLE, "szene.json")))
    log("Quelle", QUELLE, "Formen", len(sz["formen"]), "Platzierungen", sum(len(v) for v in sz["platzierungen"].values()))
    standard_texturen()
    masters = {False: master("M_Viertel_Basis", False), True: master("M_Viertel_Maske", True)}
    formen = sz["formen"]
    mats = {}
    with unreal.ScopedSlowTask(len(sz["materialien"]), "Viertel: Materialien") as st:
        st.make_dialog(True)
        for name, info in sz["materialien"].items():
            if st.should_cancel():
                return
            st.enter_progress_frame(1, name)
            try:
                mats[name] = material_instanz(name, info, masters)
            except Exception as e:  # noqa: BLE001
                warn("Material", name, e)
    opt = fbx_optionen()
    meshes = {}
    with unreal.ScopedSlowTask(len(formen), "Viertel: Meshes") as st:
        st.make_dialog(True)
        for name, form in formen.items():
            if st.should_cancel():
                return
            st.enter_progress_frame(1, name)
            try:
                sm = importieren(os.path.join(QUELLE, form["datei"]), f"{ZIEL}/Meshes/{form['kategorie']}", name, opt)
                if sm is None:
                    warn("Mesh-Import fehlgeschlagen", name)
                    continue
                mesh_einrichten(sm, form, mats)
                meshes[name] = sm
            except Exception as e:  # noqa: BLE001
                warn("Mesh", name, e)
    karte = f"{ZIEL}/Karten/L_Viertel_{'Test' if sz.get('test') else 'Alles'}"
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if EAL.does_asset_exist(karte):
        EAL.delete_asset(karte)
    les.new_level(karte)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    n_einzel = n_inst = 0
    with unreal.ScopedSlowTask(len(sz["platzierungen"]), "Viertel: Platzieren") as st:
        st.make_dialog(True)
        for name, liste in sz["platzierungen"].items():
            if st.should_cancel():
                break
            st.enter_progress_frame(1, name)
            sm, form = meshes.get(name), formen.get(name)
            if sm is None:
                continue
            ordner = f"Viertel/{form['kategorie']}"
            try:
                if len(liste) <= EINZEL_BIS:
                    for t in liste:
                        einzel_actor(eas, sm, form, t).set_folder_path(ordner)
                        n_einzel += 1
                else:
                    instanz_actor(eas, sm, form, liste).set_folder_path(ordner)
                    n_inst += len(liste)
            except Exception as e:  # noqa: BLE001
                warn("Platzieren", name, len(liste), e)
    umgebung(eas, sz)
    les.save_current_level()
    EAL.save_directory(ZIEL, only_if_is_dirty=True, recursive=True)
    log("FERTIG Karte", karte, "Einzelobjekte", n_einzel, "Instanzen", n_inst, "Meshes", len(meshes), "/", len(formen))


main()
