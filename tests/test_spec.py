"""Pruebas de proun.spec."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from proun import spec
from proun.errors import SpecError

RAIZ = Path(tempfile.mkdtemp(prefix="proun-spec-"))
FUENTES = RAIZ / "fuentes"


def setUpModule():
    FUENTES.mkdir(parents=True)
    for nombre, tam in (("a.png", (30, 30)), ("b.png", (40, 20)), ("c.jpg", (10, 10))):
        Image.new("RGB", tam, (120, 120, 120)).save(FUENTES / nombre)


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


def base(**extra):
    return {"sources": [str(FUENTES / "a.png")], "resolutions": ["1920x1080"], **extra}


class Minima(unittest.TestCase):
    def test_lo_indispensable(self):
        config = spec.build(base())
        self.assertEqual(config.resolutions, ((1920, 1080),))
        self.assertEqual(len(config.sources), 1)
        self.assertEqual(len(config.seeds), 1)
        self.assertEqual(config.output, Path("wallpapers"))
        self.assertEqual(config.fmt, "png")

    def test_hay_un_color_por_defecto(self):
        self.assertEqual(len(spec.build(base()).colors), 1)

    def test_la_referencia_es_la_primera_resolucion(self):
        config = spec.build(base(resolutions=["800x600", "1920x1080"]))
        self.assertEqual(config.reference, (800, 600))


class Resoluciones(unittest.TestCase):
    def test_formatos(self):
        config = spec.build(base(resolutions=["1920x1080", [800, 600], "2560X1440", "800×600"]))
        self.assertIn((1920, 1080), config.resolutions)
        self.assertIn((2560, 1440), config.resolutions)

    def test_deduplica_conservando_el_orden(self):
        config = spec.build(base(resolutions=["800x600", "1920x1080", "800x600"]))
        self.assertEqual(config.resolutions, ((800, 600), (1920, 1080)))

    def test_una_sola_como_texto(self):
        self.assertEqual(spec.build(base(resolutions="800x600")).resolutions, ((800, 600),))

    def test_invalidas(self):
        for malo in (["1920"], ["axb"], [[800]], ["0x600"], ["-800x600"], [], ["99999x99999"]):
            with self.assertRaises(SpecError, msg=malo):
                spec.build(base(resolutions=malo))


class Colores(unittest.TestCase):
    def test_lista(self):
        config = spec.build(base(colors=["#ff0000", "00ff00"]))
        self.assertEqual(config.colors, ((255, 0, 0), (0, 255, 0)))

    def test_uno_solo_como_texto(self):
        self.assertEqual(spec.build(base(colors="#ff0000")).colors, ((255, 0, 0),))

    def test_espectro(self):
        self.assertEqual(len(spec.build(base(spectrum=5)).colors), 5)

    def test_espectro_con_parametros(self):
        config = spec.build(base(spectrum={"count": 3, "saturation": 0.4, "value": 0.8}))
        self.assertEqual(len(config.colors), 3)

    def test_lista_y_espectro_se_suman(self):
        config = spec.build(base(colors=["#ff0000"], spectrum=3))
        self.assertEqual(len(config.colors), 4)

    def test_deduplica(self):
        self.assertEqual(len(spec.build(base(colors=["#ff0000", "ff0000"])).colors), 1)

    def test_lista_vacia_es_un_error(self):
        # Distinto de no declararla: escribir [] a mano es una equivocación.
        with self.assertRaises(SpecError):
            spec.build(base(colors=[]))

    def test_invalidos(self):
        for extra in ({"colors": ["azulito"]}, {"spectrum": {"count": 3, "saturation": 5}},
                      {"spectrum": {"cantidad": 3}}, {"spectrum": "muchos"}):
            with self.assertRaises(SpecError, msg=extra):
                spec.build(base(**extra))


class Semillas(unittest.TestCase):
    def test_count_da_esa_cantidad(self):
        self.assertEqual(len(spec.build(base(count=4)).seeds), 4)

    def test_seed_hace_el_lote_reproducible(self):
        self.assertEqual(spec.build(base(seed=7, count=4)).seeds,
                         spec.build(base(seed=7, count=4)).seeds)

    def test_sin_seed_cambian(self):
        self.assertNotEqual(spec.build(base(count=4)).seeds, spec.build(base(count=4)).seeds)

    def test_seeds_explicitas_mandan(self):
        config = spec.build(base(seeds=[111, 222], seed=7, count=9))
        self.assertEqual(config.seeds, (111, 222))

    def test_seeds_una_sola(self):
        self.assertEqual(spec.build(base(seeds=849213)).seeds, (849213,))

    def test_las_semillas_de_un_lote_no_se_repiten(self):
        self.assertEqual(len(set(spec.build(base(seed=3, count=20)).seeds)), 20)

    def test_invalidas(self):
        for extra in ({"count": 0}, {"count": -1}, {"count": "tres"},
                      {"seed": "siete"}, {"seeds": [-1]}, {"seeds": ["a"]}):
            with self.assertRaises(SpecError, msg=extra):
                spec.build(base(**extra))


class Fuentes(unittest.TestCase):
    def test_directorio_completo(self):
        self.assertEqual(len(spec.build(base(sources=[str(FUENTES)])).sources), 3)

    def test_glob(self):
        self.assertEqual(len(spec.build(base(sources=[str(FUENTES / "*.png")])).sources), 2)

    def test_ruta_suelta_como_texto(self):
        self.assertEqual(len(spec.build(base(sources=str(FUENTES / "a.png"))).sources), 1)

    def test_objeto_con_ajustes(self):
        config = spec.build(base(sources=[{"src": str(FUENTES / "a.png"),
                                           "crop": [0, 0, 10, 10], "opacity": 0.5}]))
        self.assertEqual(config.sources[0].crop, [0, 0, 10, 10])
        self.assertEqual(config.sources[0].opacity, 0.5)

    def test_copies_duplica(self):
        config = spec.build(base(sources=[{"src": str(FUENTES / "a.png"), "copies": 3}]))
        self.assertEqual(len(config.sources), 3)
        self.assertEqual(len({c.src for c in config.sources}), 1)

    def test_repeat_es_la_operacion_no_el_conteo(self):
        # copies dice cuántas veces entra la imagen al collage;
        # repeat es la operación que la estampa sobre sí misma.
        config = spec.build(base(sources=[{"src": str(FUENTES / "a.png"),
                                           "repeat": {"step": [0.5, 0], "times": 2}}]))
        self.assertEqual(len(config.sources), 1)
        self.assertEqual(config.sources[0].repeat, {"step": [0.5, 0], "times": 2})

    def test_notas_con_guion_bajo(self):
        config = spec.build(base(sources=[{"src": str(FUENTES / "a.png"), "_nota": "hola"}]))
        self.assertEqual(len(config.sources), 1)

    def test_sin_fuentes(self):
        for malo in (None, [], ""):
            with self.assertRaises(SpecError, msg=malo):
                spec.build(base(sources=malo))

    def test_fuente_inexistente(self):
        with self.assertRaises(SpecError):
            spec.build(base(sources=[str(RAIZ / "no-existe" / "*.png")]))

    def test_clave_desconocida_en_una_capa(self):
        with self.assertRaises(SpecError):
            spec.build(base(sources=[{"src": str(FUENTES / "a.png"), "girar": 90}]))

    def test_sin_src(self):
        with self.assertRaises(SpecError):
            spec.build(base(sources=[{"crop": [0, 0, 10, 10]}]))

    def test_valores_invalidos_en_una_capa(self):
        for extra in ({"opacity": 2}, {"recolor": "duotone"}, {"copies": 0}, {"copies": 9999}):
            with self.assertRaises(SpecError, msg=extra):
                spec.build(base(sources=[{"src": str(FUENTES / "a.png"), **extra}]))


class Cover(unittest.TestCase):
    def test_marca_la_capa(self):
        config = spec.build(base(sources=[{"src": str(FUENTES / "a.png"), "cover": True}]))
        self.assertTrue(config.sources[0].cover)

    def test_por_defecto_es_falso(self):
        self.assertFalse(spec.build(base()).sources[0].cover)

    def test_choca_con_resize_y_position(self):
        for extra in ({"resize": 2}, {"position": [0, 0]}):
            with self.assertRaises(SpecError, msg=extra):
                spec.build(base(sources=[{"src": str(FUENTES / "a.png"),
                                          "cover": True, **extra}]))

    def test_convive_con_crop_mosaico_y_giro(self):
        config = spec.build(base(sources=[{
            "src": str(FUENTES / "a.png"), "cover": True,
            "crop": {"aspect": "16:9"}, "mosaic": 2, "rotate": 90,
        }]))
        self.assertTrue(config.sources[0].cover)

    def test_tipo_invalido(self):
        with self.assertRaises(SpecError):
            spec.build(base(sources=[{"src": str(FUENTES / "a.png"), "cover": "si"}]))


class RegionYSangrado(unittest.TestCase):
    def capa(self, **extra):
        return spec.build(base(sources=[{"src": str(FUENTES / "a.png"), **extra}])).sources[0]

    def test_region_explicita(self):
        self.assertEqual(self.capa(region=[0.5, 0, 1, 0.5]).region, (0.5, 0.0, 1.0, 0.5))

    def test_region_por_ancla(self):
        x0, y0, x1, y1 = self.capa(region="topright").region
        self.assertGreater(x0, 0.5)
        self.assertLess(y1, 0.5)

    def test_region_invalida(self):
        for malo in ([0.5, 0, 0.2, 1], [0, 0, 1], [0, 0, 2, 1], "arriba", [0, 0, 1, 0]):
            with self.assertRaises(SpecError, msg=malo):
                self.capa(region=malo)

    def test_bleed_numero_y_par(self):
        self.assertEqual(self.capa(bleed=0.3).bleed, (0.3, 0.3))
        self.assertEqual(self.capa(bleed=[0.2, 0]).bleed, (0.2, 0.0))

    def test_bleed_invalido(self):
        for malo in (-0.1, 2, "poco", [0.5], True):
            with self.assertRaises(SpecError, msg=malo):
                self.capa(bleed=malo)

    def test_ausentes_por_defecto(self):
        capa = self.capa()
        self.assertIsNone(capa.region)
        self.assertIsNone(capa.bleed)


class Figuras(unittest.TestCase):
    def test_una_figura_no_necesita_src(self):
        config = spec.build(base(sources=[{"shape": "circle"}]))
        self.assertEqual(len(config.sources), 1)
        self.assertIsNone(config.sources[0].src)
        self.assertEqual(config.sources[0].shape, "circle")

    def test_shape_y_src_son_excluyentes(self):
        with self.assertRaises(SpecError):
            spec.build(base(sources=[{"shape": "circle", "src": str(FUENTES / "a.png")}]))

    def test_sin_shape_ni_src(self):
        with self.assertRaises(SpecError):
            spec.build(base(sources=[{"opacity": 0.5}]))

    def test_outline_viaja_intacto(self):
        config = spec.build(base(sources=[
            {"shape": "circle", "outline": {"inset": 0.2, "width": 0.05}}
        ]))
        self.assertEqual(config.sources[0].outline, {"inset": 0.2, "width": 0.05})

    def test_outline_no_es_objeto(self):
        with self.assertRaises(SpecError):
            spec.build(base(sources=[{"shape": "circle", "outline": "grueso"}]))

    def test_copies_funciona_igual_que_con_fotos(self):
        config = spec.build(base(sources=[{"shape": "circle", "copies": 4}]))
        self.assertEqual(len(config.sources), 4)

    def test_hereda_defaults_como_cualquier_capa(self):
        config = spec.build(base(
            defaults={"opacity": 0.4, "blend": "screen"},
            sources=[{"shape": "circle"}],
        ))
        self.assertEqual(config.sources[0].opacity, 0.4)
        self.assertEqual(config.sources[0].blend, "screen")

    def test_puede_convivir_con_fotos_en_la_misma_lista(self):
        config = spec.build(base(sources=[{"shape": "circle"}, str(FUENTES / "a.png")]))
        self.assertEqual(len(config.sources), 2)
        tipos = {c.shape is not None for c in config.sources}
        self.assertEqual(tipos, {True, False})


class RateYOverlap(unittest.TestCase):
    def test_rate_por_defecto_es_uno(self):
        self.assertEqual(spec.build(base(sources=[{"shape": "circle"}])).sources[0].rate, 1.0)

    def test_overlap_por_defecto_es_none(self):
        self.assertIsNone(spec.build(base(sources=[{"shape": "circle"}])).sources[0].overlap)

    def test_valores_explicitos(self):
        config = spec.build(base(sources=[{"shape": "circle", "rate": 0.4, "overlap": 0.1}]))
        self.assertEqual(config.sources[0].rate, 0.4)
        self.assertEqual(config.sources[0].overlap, 0.1)

    def test_rate_fuera_de_rango(self):
        for malo in (-0.1, 1.1, "poco", True):
            with self.assertRaises(SpecError, msg=malo):
                spec.build(base(sources=[{"shape": "circle", "rate": malo}]))

    def test_overlap_fuera_de_rango(self):
        for malo in (-0.1, 1.1, "poco", True):
            with self.assertRaises(SpecError, msg=malo):
                spec.build(base(sources=[{"shape": "circle", "overlap": malo}]))

    def test_tambien_aplican_a_fotos(self):
        config = spec.build(base(sources=[{"src": str(FUENTES / "a.png"), "rate": 0.5}]))
        self.assertEqual(config.sources[0].rate, 0.5)


class Defaults(unittest.TestCase):
    def test_se_aplican_a_todas(self):
        config = spec.build(base(defaults={"rotate": "random", "blend": "screen"},
                                 sources=[str(FUENTES)]))
        self.assertTrue(all(c.rotate == "random" for c in config.sources))
        self.assertTrue(all(c.blend == "screen" for c in config.sources))

    def test_la_capa_pisa_al_default(self):
        config = spec.build(base(
            defaults={"opacity": 0.5, "rotate": "random"},
            sources=[{"src": str(FUENTES / "a.png"), "opacity": 1.0}],
        ))
        self.assertEqual(config.sources[0].opacity, 1.0)
        self.assertEqual(config.sources[0].rotate, "random")

    def test_tones_por_defecto_esta_encendido(self):
        self.assertIs(spec.build(base()).sources[0].tones, True)

    def test_tones_se_puede_apagar(self):
        config = spec.build(base(sources=[{"src": str(FUENTES / "a.png"), "tones": False}]))
        self.assertIs(config.sources[0].tones, False)

    def test_defaults_de_otro_tipo(self):
        with self.assertRaises(SpecError):
            spec.build(base(defaults="rotate"))


class Capas(unittest.TestCase):
    def test_rango(self):
        self.assertEqual(spec.build(base(layers={"min": 2, "max": 5})).layers, (2, 5))

    def test_numero_suelto(self):
        self.assertEqual(spec.build(base(layers=3)).layers, (3, 3))

    def test_par(self):
        self.assertEqual(spec.build(base(layers=[2, 4])).layers, (2, 4))

    def test_ausente_significa_todas(self):
        self.assertIsNone(spec.build(base()).layers)

    def test_invalidos(self):
        for malo in ({"min": 5, "max": 2}, {"min": 0}, {"minimo": 2}, "muchas", 0):
            with self.assertRaises(SpecError, msg=malo):
                spec.build(base(layers=malo))


class Salida(unittest.TestCase):
    def test_formatos_validos(self):
        for fmt in ("png", "jpg", "jpeg", "webp", "PNG", ".png"):
            self.assertIn(spec.build(base(format=fmt)).fmt, spec.FORMATS, fmt)

    def test_total(self):
        config = spec.build(base(count=2, resolutions=["800x600", "640x480"], spectrum=3))
        self.assertEqual(config.total, 12)

    def test_invalidos(self):
        for extra in ({"format": "tiff"}, {"quality": 0}, {"quality": 101},
                      {"quality": "alta"}, {"start_index": -1}):
            with self.assertRaises(SpecError, msg=extra):
                spec.build(base(**extra))


class Archivo(unittest.TestCase):
    def test_rutas_relativas_al_archivo(self):
        # Las fuentes se resuelven junto al JSON, no junto al directorio actual.
        ruta = RAIZ / "config.json"
        ruta.write_text(json.dumps({"sources": ["fuentes/a.png"], "resolutions": ["800x600"]}),
                        encoding="utf-8")
        config = spec.build(spec.load(ruta))
        self.assertEqual(config.sources[0].src.name, "a.png")

    def test_notas_de_nivel_superior(self):
        ruta = RAIZ / "notas.json"
        ruta.write_text(json.dumps({"_titulo": "prueba", "sources": ["fuentes/a.png"]}),
                        encoding="utf-8")
        self.assertEqual(len(spec.build(spec.load(ruta)).sources), 1)

    def test_json_invalido(self):
        ruta = RAIZ / "roto.json"
        ruta.write_text("{esto no es json", encoding="utf-8")
        with self.assertRaises(SpecError):
            spec.load(ruta)

    def test_json_que_no_es_objeto(self):
        ruta = RAIZ / "lista.json"
        ruta.write_text("[1, 2, 3]", encoding="utf-8")
        with self.assertRaises(SpecError):
            spec.load(ruta)

    def test_archivo_inexistente(self):
        with self.assertRaises(SpecError):
            spec.load(RAIZ / "fantasma.json")

    def test_clave_desconocida_de_nivel_superior(self):
        with self.assertRaises(SpecError):
            spec.build(base(resolucion="1920x1080"))


if __name__ == "__main__":
    unittest.main()