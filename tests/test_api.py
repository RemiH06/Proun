"""Pruebas de la API FastAPI (api/) que envuelve proun.spec/proun.compose."""

import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from api.cache import cache
from api.main import app
from api.paths import PROJECT_ROOT, resolve_sources_path
from api.routes_render import _build_spec, _sin_explosion_de_mosaico
from api.schemas import LayerSpec, PreviewRequest
from proun import compose, layout, loading
from proun.ops import blend, recolor, shapes

RAIZ = Path(tempfile.mkdtemp(prefix="proun-api-"))
FUENTES = RAIZ / "fuentes"
ARCHIVOS = [FUENTES / f"foto{i}.png" for i in range(4)]

client = TestClient(app)


GRANDE = FUENTES / "grande.png"


def setUpModule():
    FUENTES.mkdir(parents=True)
    for i, archivo in enumerate(ARCHIVOS):
        Image.new("RGB", (200, 150), (20 * i, 60, 120)).save(archivo)
    # Simula una foto real (miles de px), el caso donde el mosaico se
    # disparaba: ver Mosaico más abajo.
    Image.new("RGB", (3000, 2000), (80, 40, 20)).save(GRANDE)


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


def capas(*overrides):
    """Una capa de imagen por override (dict de ajustes, "src" se agrega
    solo). Sin overrides, las cuatro fotos de prueba sin ajustes propios."""
    if not overrides:
        return [{"src": str(a)} for a in ARCHIVOS]
    return [{"src": str(ARCHIVOS[i % len(ARCHIVOS)]), **ov} for i, ov in enumerate(overrides)]


def cuerpo(**extra):
    return {
        "layers": capas(),
        "layout_mode": "scatter",
        "color": "#3ba7ff",
        "recolor_mode": "duotone",
        "seed": 424242,
        **extra,
    }


class RutasDeFuentes(unittest.TestCase):
    def test_relativa_se_ancla_a_la_raiz_del_proyecto(self):
        # No depende de cuál sea el cwd real del proceso: por eso el test
        # compara contra PROJECT_ROOT en vez de contra os.getcwd().
        self.assertEqual(resolve_sources_path("fuentes"), str(PROJECT_ROOT / "fuentes"))

    def test_absoluta_no_se_toca(self):
        self.assertEqual(resolve_sources_path(str(FUENTES)), str(FUENTES))

    def test_el_endpoint_devuelve_la_ruta_ya_resuelta(self):
        resp = client.get("/api/sources", params={"path": "fuentes"})
        self.assertEqual(resp.json()["path"], str(PROJECT_ROOT / "fuentes"))


class Opciones(unittest.TestCase):
    def test_coincide_con_las_constantes_del_motor(self):
        resp = client.get("/api/options")
        self.assertEqual(resp.status_code, 200)
        datos = resp.json()
        self.assertEqual(datos["layout_modes"], list(layout.MODES))
        self.assertEqual(datos["recolor_modes"], list(recolor.MODES))
        self.assertEqual(datos["blend_modes"], list(blend.MODES))
        self.assertEqual(datos["shape_kinds"], list(shapes.KINDS))


class Fuentes(unittest.TestCase):
    def test_lista_igual_que_loading_expand(self):
        resp = client.get("/api/sources", params={"path": str(FUENTES)})
        self.assertEqual(resp.status_code, 200)
        datos = resp.json()
        esperado = {str(p) for p in loading.expand([str(FUENTES)])}
        self.assertEqual({img["path"] for img in datos["images"]}, esperado)
        self.assertEqual(datos["count"], len(esperado))


class Miniaturas(unittest.TestCase):
    def test_devuelve_un_png_chico(self):
        resp = client.get("/api/sources/thumbnail", params={"path": str(ARCHIVOS[0])})
        self.assertEqual(resp.status_code, 200)
        imagen = Image.open(io.BytesIO(resp.content))
        self.assertLessEqual(max(imagen.size), 160)


class Preview(unittest.TestCase):
    def test_refleja_un_cambio_de_layout(self):
        a = client.post("/api/preview", json=cuerpo(layout_mode="scatter"))
        b = client.post("/api/preview", json=cuerpo(layout_mode="grid"))
        self.assertEqual(a.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_es_reproducible(self):
        a = client.post("/api/preview", json=cuerpo())
        b = client.post("/api/preview", json=cuerpo())
        self.assertEqual(a.content, b.content)

    def test_una_imagen_rotada_da_un_resultado_distinto(self):
        recto = cuerpo(layers=capas({}, {}))
        girado = cuerpo(layers=capas({"rotate": {"angles": [90]}}, {}))
        a = client.post("/api/preview", json=recto)
        b = client.post("/api/preview", json=girado)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_una_posicion_explicita_ubica_la_capa_ahi(self):
        # Dos posiciones bien separadas tienen que dar composiciones
        # distintas; si position no llegara al motor, darían lo mismo.
        arriba_izq = cuerpo(layers=capas({"position": [0.1, 0.1]}))
        abajo_der = cuerpo(layers=capas({"position": [0.9, 0.9]}))
        a = client.post("/api/preview", json=arriba_izq)
        b = client.post("/api/preview", json=abajo_der)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_z_alto_pinta_encima(self):
        # Dos capas centradas en el mismo punto exacto, cada una con su
        # propio color: la de z más alto tiene que quedar arriba (se ve su
        # color en el centro), sin importar en qué orden se sortearon.
        centro = {"position": [0.5, 0.5]}
        arriba_azul = cuerpo(layers=capas(
            {**centro, "z": -5, "color": "#ff0000"},
            {**centro, "z": 5, "color": "#2244ff"},
        ))
        resp = client.post("/api/preview", json=arriba_azul)
        self.assertEqual(resp.status_code, 200)
        imagen = Image.open(io.BytesIO(resp.content))
        r, g, b = imagen.getpixel((imagen.width // 2, imagen.height // 2))[:3]
        self.assertGreater(b, r)

        arriba_roja = cuerpo(layers=capas(
            {**centro, "z": 5, "color": "#ff0000"},
            {**centro, "z": -5, "color": "#2244ff"},
        ))
        resp2 = client.post("/api/preview", json=arriba_roja)
        imagen2 = Image.open(io.BytesIO(resp2.content))
        r2, g2, b2 = imagen2.getpixel((imagen2.width // 2, imagen2.height // 2))[:3]
        self.assertGreater(r2, b2)

    def test_caleidoscopio_no_revienta_y_cambia_el_resultado(self):
        sin_repeat = cuerpo(layers=capas({}))
        con_caleidoscopio = cuerpo(
            layers=capas({"repeat": {"pivot": [0.5, 0], "sectors": 4}})
        )
        a = client.post("/api/preview", json=sin_repeat)
        b = client.post("/api/preview", json=con_caleidoscopio)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_un_crop_distinto_cambia_el_resultado(self):
        libre = cuerpo(layers=capas({}))
        cuadrado = cuerpo(layers=capas({"crop": {"aspect": "1:1"}}))
        a = client.post("/api/preview", json=libre)
        b = client.post("/api/preview", json=cuadrado)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_resize_por_capa_cambia_el_resultado(self):
        chica = cuerpo(layers=capas({"resize": {"size": [0.1, 0.1]}}))
        grande = cuerpo(layers=capas({"resize": {"size": [0.8, 0.8]}}))
        a = client.post("/api/preview", json=chica)
        b = client.post("/api/preview", json=grande)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_stain_por_capa_cambia_el_resultado(self):
        sin_mancha = cuerpo(layers=capas({}))
        manchada = cuerpo(layers=capas({"stain": {"amount": 0.9}}))
        a = client.post("/api/preview", json=sin_mancha)
        b = client.post("/api/preview", json=manchada)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_finish_por_capa_cambia_el_resultado(self):
        sin_acabado = cuerpo(layers=capas({}))
        con_vineta = cuerpo(layers=capas({"finish": {"vignette": 0.9}}))
        a = client.post("/api/preview", json=sin_acabado)
        b = client.post("/api/preview", json=con_vineta)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_una_figura_sola_no_revienta(self):
        resp = client.post("/api/preview", json=cuerpo(layers=[{"shape": "circle"}]))
        self.assertEqual(resp.status_code, 200)
        Image.open(io.BytesIO(resp.content))  # no tira, es un PNG real

    def test_un_texto_solo_no_revienta(self):
        resp = client.post("/api/preview", json=cuerpo(layers=[{"text": "PROUN"}]))
        self.assertEqual(resp.status_code, 200)
        Image.open(io.BytesIO(resp.content))

    def test_dos_textos_distintos_dan_resultados_distintos(self):
        a = client.post("/api/preview", json=cuerpo(layers=[{"text": "PROUN"}]))
        b = client.post("/api/preview", json=cuerpo(layers=[{"text": "OTRO"}]))
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_background_explicito_cambia_el_resultado(self):
        auto = cuerpo()
        rojo = cuerpo(background={"solid": "#ff0000"})
        a = client.post("/api/preview", json=auto)
        b = client.post("/api/preview", json=rojo)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)

    def test_la_vista_previa_respeta_el_aspecto_del_canvas(self):
        vertical = cuerpo(resolution="1080x1920")
        resp = client.post("/api/preview", json=vertical)
        self.assertEqual(resp.status_code, 200)
        imagen = Image.open(io.BytesIO(resp.content))
        self.assertGreater(imagen.height, imagen.width)
        self.assertLessEqual(max(imagen.size), 480)

    def test_finish_explicito_cambia_el_resultado(self):
        sin_acabado = cuerpo()
        con_vineta = cuerpo(finish={"vignette": 0.8})
        a = client.post("/api/preview", json=sin_acabado)
        b = client.post("/api/preview", json=con_vineta)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertNotEqual(a.content, b.content)


class CacheDeGeometria(unittest.TestCase):
    def setUp(self):
        cache.clear()

    def test_no_rehace_geometria_si_solo_cambia_el_color(self):
        with patch.object(compose, "prepare", wraps=compose.prepare) as prep, \
             patch.object(compose, "render", wraps=compose.render) as rend:
            client.post("/api/preview", json=cuerpo(color="#3ba7ff"))
            client.post("/api/preview", json=cuerpo(color="#ff0000"))
            self.assertEqual(prep.call_count, 1)
            self.assertEqual(rend.call_count, 2)

    def test_no_rehace_geometria_si_solo_cambia_el_recolor(self):
        # Este es el caso que justifica un hash de geometría propio en vez de
        # reusar naming.content_hash tal cual: recolor sí participa de ese
        # hash (para nombrar bien los exports) pero no de la geometría.
        with patch.object(compose, "prepare", wraps=compose.prepare) as prep:
            client.post("/api/preview", json=cuerpo(recolor_mode="duotone"))
            client.post("/api/preview", json=cuerpo(recolor_mode="tint"))
            self.assertEqual(prep.call_count, 1)

    def test_no_rehace_geometria_si_solo_cambia_opacity_o_blend(self):
        with patch.object(compose, "prepare", wraps=compose.prepare) as prep:
            client.post("/api/preview", json=cuerpo(layers=capas({"opacity": 1.0})))
            client.post("/api/preview", json=cuerpo(layers=capas({"opacity": 0.4})))
            client.post("/api/preview", json=cuerpo(layers=capas({"opacity": 0.4, "blend": "screen"})))
            self.assertEqual(prep.call_count, 1)

    def test_si_cambia_el_layout_si_rehace_geometria(self):
        with patch.object(compose, "prepare", wraps=compose.prepare) as prep:
            client.post("/api/preview", json=cuerpo(layout_mode="scatter"))
            client.post("/api/preview", json=cuerpo(layout_mode="grid"))
            self.assertEqual(prep.call_count, 2)

    def test_si_cambia_rotate_si_rehace_geometria(self):
        with patch.object(compose, "prepare", wraps=compose.prepare) as prep:
            client.post("/api/preview", json=cuerpo(layers=capas({})))
            client.post("/api/preview", json=cuerpo(layers=capas({"rotate": {"angles": [90]}})))
            self.assertEqual(prep.call_count, 2)


class Mosaico(unittest.TestCase):
    """`compose._shape_layer` salta el resize automático al hueco del layout
    cuando la capa pide `mosaic` sin su propio `resize` (arranca del tamaño
    nativo del archivo). Con una foto real eso disparaba capas de decenas de
    miles de px. `_build_spec` le agrega un `resize.max_side` de compensación
    antes de que el motor vea el spec; estos tests cubren esa compensación,
    no el mosaico del motor en sí (eso ya lo prueba `tests/test_mosaic.py`)."""

    def test_agrega_resize_de_compensacion(self):
        body = PreviewRequest(layers=[LayerSpec(src=str(GRANDE), mosaic={"grid": [3, 3]})])
        built = _build_spec(body, "800x600")
        self.assertIsNotNone(built.sources[0].resize)
        self.assertIn("max_side", built.sources[0].resize)

    def test_no_toca_capas_sin_mosaico(self):
        body = PreviewRequest(layers=[LayerSpec(src=str(GRANDE))])
        built = _build_spec(body, "800x600")
        self.assertIsNone(built.sources[0].resize)

    def test_respeta_un_resize_propio(self):
        body = PreviewRequest(layers=[LayerSpec(
            src=str(GRANDE), mosaic={"grid": [3, 3]}, resize={"max_side": 111},
        )])
        built = _build_spec(body, "800x600")
        self.assertEqual(built.sources[0].resize, {"max_side": 111})

    def test_no_toca_capas_sin_grid_explicito(self):
        capa = {"src": str(GRANDE), "mosaic": {"size": [400, 400]}}
        resultado = _sin_explosion_de_mosaico(capa, 800)
        self.assertNotIn("resize", resultado)

    def test_el_resultado_final_no_explota_de_tamano(self):
        # Reproduce el bug real: antes de la compensación, una foto de
        # 3000x2000 con grid [3,3] terminaba en decenas de miles de px.
        body = PreviewRequest(layers=[LayerSpec(src=str(GRANDE), mosaic={"grid": [3, 3]})])
        built = _build_spec(body, "800x600")
        current = compose.plan(built, built.seeds[0])
        shaped = compose.prepare(built, current, built.resolutions[0])
        ancho, alto = shaped[0].tonal.size
        # Generoso a propósito: el punto es "no explota", no un tamaño exacto.
        self.assertLess(ancho, 800 * 3)
        self.assertLess(alto, 600 * 3)


class Errores(unittest.TestCase):
    def test_sin_capas_da_400_con_el_mensaje_en_espanol(self):
        resp = client.post("/api/preview", json=cuerpo(layers=[]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("imagen", resp.json()["detail"])


class Export(unittest.TestCase):
    def test_da_una_imagen_real_en_la_resolucion_pedida(self):
        # output apunta dentro de RAIZ (que tearDownModule ya limpia) para no
        # escribir en el wallpapers/ real del repo al correr los tests.
        salida = RAIZ / "salida"
        resp = client.post("/api/export", json=cuerpo(
            resolution="320x200", output=str(salida),
        ))
        self.assertEqual(resp.status_code, 200)
        imagen = Image.open(io.BytesIO(resp.content))
        self.assertEqual(imagen.size, (320, 200))
        destino = Path(resp.headers["x-export-path"])
        self.assertTrue(destino.is_file())
        self.assertTrue(destino.is_relative_to(salida))


if __name__ == "__main__":
    unittest.main()
