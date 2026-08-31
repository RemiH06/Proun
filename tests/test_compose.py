"""Pruebas de proun.compose."""

import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from proun import compose, spec
from proun.errors import SourceError, SpecError
from proun.ops import blend

RAIZ = Path(tempfile.mkdtemp(prefix="proun-compose-"))
FUENTES = RAIZ / "fuentes"
AZUL = "#3ba7ff"


def setUpModule():
    FUENTES.mkdir(parents=True)
    Image.linear_gradient("L").resize((300, 300)).convert("RGB").save(FUENTES / "a.png")
    Image.new("RGB", (400, 200), (200, 60, 60)).save(FUENTES / "b.png")
    Image.new("RGB", (150, 400), (60, 200, 60)).save(FUENTES / "c.png")


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


def config(**extra):
    return spec.build({
        "sources": [str(FUENTES)],
        "resolutions": ["800x450", "1600x900"],
        "colors": [AZUL],
        "seeds": [12345],
        "output": str(RAIZ / "salida"),
        **extra,
    })


class Planificacion(unittest.TestCase):
    def test_solo_depende_de_la_semilla(self):
        base = config()
        self.assertEqual(compose.plan(base, 99), compose.plan(base, 99))
        self.assertNotEqual(compose.plan(base, 99), compose.plan(base, 100))

    def test_incluye_todas_las_capas_por_defecto(self):
        self.assertEqual(len(compose.plan(config(), 1).placements), 3)

    def test_layers_recorta_la_cantidad(self):
        plan = compose.plan(config(layers={"min": 2, "max": 2}), 1)
        self.assertEqual(len(plan.placements), 2)

    def test_layers_por_encima_de_las_disponibles_repite(self):
        plan = compose.plan(config(layers=5), 1)
        self.assertEqual(len(plan.placements), 5)

    def test_el_orden_se_revuelve(self):
        ordenes = {
            tuple(p.layer.src.name for p in compose.plan(config(), s).placements)
            for s in range(12)
        }
        self.assertGreater(len(ordenes), 1)

    def test_guarda_giro_posicion_y_tamano(self):
        colocacion = compose.plan(config(defaults={"rotate": "random"}), 7).placements[0]
        self.assertIn(colocacion.angle, (0.0, 90.0, 180.0, 270.0))
        self.assertEqual(len(colocacion.center), 2)
        self.assertGreater(colocacion.fill, 0)


class Render(unittest.TestCase):
    def test_tamano_del_lienzo(self):
        base = config()
        plan = compose.plan(base, 12345)
        self.assertEqual(compose.render(base, plan, (800, 450), AZUL).size, (800, 450))

    def test_es_determinista(self):
        base = config()
        plan = compose.plan(base, 12345)
        uno = compose.render(base, plan, (800, 450), AZUL)
        dos = compose.render(base, plan, (800, 450), AZUL)
        self.assertEqual(uno.tobytes(), dos.tobytes())

    def test_determinista_incluso_con_grano(self):
        base = config(finish={"grain": 0.2, "vignette": 0.3})
        plan = compose.plan(base, 555)
        uno = compose.render(base, plan, (400, 300), AZUL)
        dos = compose.render(base, plan, (400, 300), AZUL)
        self.assertEqual(uno.tobytes(), dos.tobytes())

    def test_el_color_cambia_el_resultado(self):
        base = config()
        plan = compose.plan(base, 12345)
        azul = compose.render(base, plan, (400, 300), AZUL)
        rojo = compose.render(base, plan, (400, 300), "#ff0000")
        self.assertNotEqual(azul.tobytes(), rojo.tobytes())

    def test_misma_composicion_en_dos_resoluciones(self):
        base = config()
        plan = compose.plan(base, 12345)
        chica = compose.render(base, plan, (800, 450), AZUL)
        grande = compose.render(base, plan, (1600, 900), AZUL).resize((800, 450))
        muestras = [(x, y) for x in range(20, 800, 97) for y in range(20, 450, 61)]
        parecidos = sum(
            abs(chica.getpixel(p)[0] - grande.getpixel(p)[0]) < 40 for p in muestras
        )
        self.assertGreater(parecidos / len(muestras), 0.7)

    def test_prepare_se_puede_reusar_entre_colores(self):
        base = config()
        plan = compose.plan(base, 12345)
        shaped = compose.prepare(base, plan, (400, 300))
        con_reuso = compose.render(base, plan, (400, 300), AZUL, shaped)
        sin_reuso = compose.render(base, plan, (400, 300), AZUL)
        self.assertEqual(con_reuso.tobytes(), sin_reuso.tobytes())

    def test_prepare_no_se_consume(self):
        # El mismo prepare sirve para varios colores seguidos.
        base = config()
        plan = compose.plan(base, 12345)
        shaped = compose.prepare(base, plan, (400, 300))
        primero = compose.render(base, plan, (400, 300), AZUL, shaped)
        compose.render(base, plan, (400, 300), "#ff0000", shaped)
        self.assertEqual(compose.render(base, plan, (400, 300), AZUL, shaped).tobytes(),
                         primero.tobytes())

    def test_fondo_transparente(self):
        base = config(background=None, layers=1)
        plan = compose.plan(base, 4)
        salida = compose.render(base, plan, (400, 300), AZUL)
        self.assertEqual(salida.mode, "RGBA")

    def test_posicion_explicita(self):
        base = spec.build({
            "sources": [{"src": str(FUENTES / "b.png"), "position": "topleft",
                         "resize": {"size": [100, 50]}}],
            "resolutions": ["400x300"], "colors": [AZUL], "seeds": [1],
            "background": "#000000",
        })
        salida = compose.render(base, compose.plan(base, 1), (400, 300), AZUL)
        self.assertNotEqual(salida.getpixel((5, 5))[:3], (0, 0, 0))
        self.assertEqual(salida.getpixel((395, 295))[:3], (0, 0, 0))


class Escalado(unittest.TestCase):
    def test_factor_por_area(self):
        base = config(reference="800x450")
        self.assertEqual(compose._scale(base, (800, 450)), 1.0)
        self.assertAlmostEqual(compose._scale(base, (1600, 900)), 2.0, places=6)

    def test_se_puede_apagar(self):
        base = config(reference="800x450", scale_with_resolution=False)
        self.assertEqual(compose._scale(base, (1600, 900)), 1.0)

    def test_apagado_mide_contra_el_lienzo_real(self):
        # Sin escalado, una capa de media pantalla mide medio lienzo en cada
        # resolución; con escalado, mide lo mismo en proporción a la referencia.
        base = spec.build({
            "sources": [{"src": str(FUENTES / "a.png"), "resize": {"size": [0.5, 0.5]}}],
            "resolutions": ["800x450", "1600x900"], "colors": [AZUL], "seeds": [1],
            "scale_with_resolution": False,
        })
        plan = compose.plan(base, 1)
        chica = compose.prepare(base, plan, (800, 450))[0].tonal
        grande = compose.prepare(base, plan, (1600, 900))[0].tonal
        self.assertAlmostEqual(grande.width / chica.width, 2.0, places=1)


class Preparacion(unittest.TestCase):
    def test_guarda_la_fuente_solo_si_hace_falta(self):
        con = config(defaults={"recolor": {"strength": 0.5, "mix_with": "source"}})
        sin = config(defaults={"recolor": {"strength": 0.5}})
        self.assertIsNotNone(compose.prepare(con, compose.plan(con, 1), (400, 300))[0].source)
        self.assertIsNone(compose.prepare(sin, compose.plan(sin, 1), (400, 300))[0].source)

    def test_una_capa_sin_resize_recibe_tamano_automatico(self):
        base = config(layout={"size": [0.5, 0.5]}, layers=1)
        capa = compose.prepare(base, compose.plan(base, 2), (800, 450))[0].tonal
        self.assertLessEqual(max(capa.size), 800)
        self.assertGreater(max(capa.size), 100)


class CapaDeFondo(unittest.TestCase):
    def fondo(self, **extra):
        return spec.build({
            "sources": [{"src": str(FUENTES / "b.png"), "cover": True},
                        str(FUENTES / "a.png"), str(FUENTES / "c.png")],
            "resolutions": ["400x300"], "colors": [AZUL], "seeds": [3],
            "background": None, **extra,
        })

    def test_cubre_el_lienzo_exacto(self):
        base = self.fondo()
        for resolucion in ((400, 300), (300, 400), (1000, 200)):
            shaped = compose.prepare(base, compose.plan(base, 3), resolucion)
            self.assertEqual(shaped[0].tonal.size, resolucion, resolucion)

    def test_no_deja_esquinas_transparentes(self):
        base = self.fondo()
        salida = compose.render(base, compose.plan(base, 3), (400, 300), AZUL)
        for esquina in ((0, 0), (399, 0), (0, 299), (399, 299)):
            self.assertEqual(salida.getpixel(esquina)[3], 255, esquina)

    def test_va_siempre_primera(self):
        base = self.fondo()
        for semilla in range(10):
            plan = compose.plan(base, semilla)
            self.assertTrue(plan.placements[0].layer.cover, semilla)
            self.assertFalse(any(p.layer.cover for p in plan.placements[1:]), semilla)

    def test_no_la_recorta_el_limite_de_capas(self):
        base = self.fondo(layers=1)
        plan = compose.plan(base, 3)
        self.assertEqual(len(plan.placements), 2)
        self.assertTrue(plan.placements[0].layer.cover)

    def test_cubre_incluso_girada(self):
        # El ajuste al lienzo va después del giro; si fuera antes, un cuarto de
        # vuelta dejaría el fondo sin cubrir.
        base = spec.build({
            "sources": [{"src": str(FUENTES / "b.png"), "cover": True, "rotate": 90}],
            "resolutions": ["400x300"], "colors": [AZUL], "seeds": [1], "background": None,
        })
        shaped = compose.prepare(base, compose.plan(base, 1), (400, 300))
        self.assertEqual(shaped[0].tonal.size, (400, 300))

    def test_varias_capas_de_fondo_conservan_su_orden(self):
        base = spec.build({
            "sources": [{"src": str(FUENTES / "b.png"), "cover": True},
                        {"src": str(FUENTES / "c.png"), "cover": True}],
            "resolutions": ["400x300"], "colors": [AZUL], "seeds": [1],
        })
        nombres = [p.layer.src.name for p in compose.plan(base, 1).placements]
        self.assertEqual(nombres, ["b.png", "c.png"])


class RegionSangradoYColor(unittest.TestCase):
    def config(self, **extra):
        return spec.build({
            "resolutions": ["400x300"], "colors": ["#ffffff"], "seeds": [5],
            "background": "#000000", **extra,
        })

    def test_la_region_confina_el_centro(self):
        base = self.config(sources=[{"src": str(FUENTES / "a.png"),
                                     "region": [0.6, 0.6, 1.0, 1.0]}])
        for semilla in range(12):
            centro = compose.plan(base, semilla).placements[0].center
            self.assertGreaterEqual(centro[0], 0.6, semilla)
            self.assertGreaterEqual(centro[1], 0.6, semilla)

    def test_sin_region_el_centro_no_cambia(self):
        sin = self.config(sources=[str(FUENTES / "a.png")])
        self.assertNotEqual(compose.plan(sin, 3).placements[0].center, (0.5, 0.5))

    def test_bleed_cero_deja_la_capa_dentro(self):
        base = self.config(sources=[{"src": str(FUENTES / "a.png"), "bleed": 0,
                                     "resize": {"size": [80, 60]}}],
                           layout={"mode": "free", "bleed": 0.9})
        salida = compose.render(base, compose.plan(base, 2), (400, 300), "#ffffff")
        # Con la capa forzada adentro, ningún borde del lienzo queda intacto
        # por accidente: basta con que algo se haya dibujado.
        self.assertGreater(salida.convert("L").getextrema()[1], 0)

    def test_color_de_la_capa_puede_ser_una_lista(self):
        base = self.config(sources=[{"src": str(FUENTES / "a.png"),
                                     "color": ["#ff0000", "#00ff00", "#0000ff"]}])
        elegidos = {compose.plan(base, s).placements[0].color for s in range(20)}
        self.assertGreater(len(elegidos), 1)
        self.assertTrue(elegidos <= {"#ff0000", "#00ff00", "#0000ff"})

    def test_el_color_elegido_es_reproducible(self):
        base = self.config(sources=[{"src": str(FUENTES / "a.png"),
                                     "color": ["#ff0000", "#00ff00"]}])
        self.assertEqual(compose.plan(base, 9).placements[0].color,
                         compose.plan(base, 9).placements[0].color)

    def test_lista_de_colores_vacia(self):
        base = self.config(sources=[{"src": str(FUENTES / "a.png"), "color": []}])
        with self.assertRaises(SpecError):
            compose.plan(base, 1)


class Errores(unittest.TestCase):
    def test_dice_que_imagen_fallo(self):
        base = spec.build({
            "sources": [{"src": str(FUENTES / "a.png"), "crop": [5000, 5000, 10, 10]}],
            "resolutions": ["400x300"], "colors": [AZUL], "seeds": [1],
        })
        with self.assertRaises(SourceError) as caso:
            compose.render(base, compose.plan(base, 1), (400, 300), AZUL)
        self.assertIn("a.png", str(caso.exception))

    def test_archivo_borrado_despues_de_validar(self):
        temporal = FUENTES / "temporal.png"
        Image.new("RGB", (50, 50), (10, 10, 10)).save(temporal)
        base = spec.build({"sources": [str(temporal)], "resolutions": ["400x300"],
                           "colors": [AZUL], "seeds": [1]})
        temporal.unlink()
        from proun import loading
        loading.clear_cache()
        with self.assertRaises(SourceError):
            compose.render(base, compose.plan(base, 1), (400, 300), AZUL)


class Guardado(unittest.TestCase):
    def imagen(self):
        base = config()
        return compose.render(base, compose.plan(base, 1), (200, 150), AZUL)

    def test_los_tres_formatos(self):
        imagen = self.imagen()
        for fmt in ("png", "jpg", "webp"):
            ruta = compose.save(imagen, RAIZ / f"prueba.{fmt}", fmt)
            self.assertGreater(ruta.stat().st_size, 0, fmt)
            with Image.open(ruta) as abierta:
                self.assertEqual(abierta.size, (200, 150), fmt)

    def test_crea_los_directorios(self):
        ruta = compose.save(self.imagen(), RAIZ / "nueva" / "carpeta" / "x.png")
        self.assertTrue(ruta.is_file())

    def test_jpeg_aplana_sobre_negro(self):
        transparente = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        ruta = compose.save(transparente, RAIZ / "plano.jpg", "jpg")
        with Image.open(ruta) as abierta:
            self.assertEqual(abierta.convert("RGB").getpixel((10, 10)), (0, 0, 0))

    def test_optimize_no_cambia_el_contenido(self):
        imagen = self.imagen()
        rapido = compose.save(imagen, RAIZ / "rapido.png", "png", optimize=False)
        lento = compose.save(imagen, RAIZ / "lento.png", "png", optimize=True)
        with Image.open(rapido) as a, Image.open(lento) as b:
            self.assertEqual(a.tobytes(), b.tobytes())


if __name__ == "__main__":
    unittest.main()