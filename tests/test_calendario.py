"""Pruebas de calendario.py (script de la raíz del proyecto, no proun/)."""

import contextlib
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import calendario
from proun.errors import SpecError

RAIZ = Path(tempfile.mkdtemp(prefix="proun-calendario-"))
FUENTES = RAIZ / "fuentes"


def contar_paginas_pdf(path) -> int:
    """Pillow escribe PDF pero no lo puede releer, así que se cuentan los
    objetos `/Type /Page` (no `/Pages`, el árbol) directo en los bytes."""
    datos = Path(path).read_bytes()
    return len(re.findall(rb"/Type\s*/Page(?!s)", datos))


def setUpModule():
    FUENTES.mkdir(parents=True)
    for i in range(12):
        Image.new("RGB", (300, 200), (10 * i, 40, 80)).save(FUENTES / f"foto{i:02d}.png")


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


class MedidasDePapel(unittest.TestCase):
    def test_mm_a_px(self):
        self.assertEqual(calendario.mm_to_px(25.4, 300), 300)
        self.assertEqual(calendario.mm_to_px(25.4, 100), 100)

    def test_a4_vertical(self):
        w, h = calendario.page_size("a4", "portrait", 100)
        self.assertLess(w, h)

    def test_landscape_invierte_los_lados(self):
        vertical = calendario.page_size("a4", "portrait", 100)
        horizontal = calendario.page_size("a4", "landscape", 100)
        self.assertEqual(vertical, horizontal[::-1])


class SeleccionDeImagenes(unittest.TestCase):
    def test_toma_las_primeras_doce_en_orden(self):
        elegidas = calendario.pick_twelve([str(FUENTES)], seed=None)
        self.assertEqual(len(elegidas), 12)
        self.assertEqual(elegidas, sorted(elegidas))

    def test_menos_de_doce_es_un_error(self):
        pocas = RAIZ / "pocas"
        pocas.mkdir()
        Image.new("RGB", (10, 10)).save(pocas / "a.png")
        with self.assertRaises(SpecError):
            calendario.pick_twelve([str(pocas)], seed=None)

    def test_seed_es_reproducible(self):
        una = calendario.pick_twelve([str(FUENTES)], seed=7)
        otra = calendario.pick_twelve([str(FUENTES)], seed=7)
        self.assertEqual(una, otra)

    def test_semillas_distintas_pueden_dar_orden_distinto(self):
        ordenes = {tuple(calendario.pick_twelve([str(FUENTES)], seed=s)) for s in range(8)}
        self.assertGreater(len(ordenes), 1)


class Render(unittest.TestCase):
    def test_tamano_de_pagina(self):
        pagina = calendario.render_month(FUENTES / "foto00.png", 2027, 3, (400, 600), 20, 10)
        self.assertEqual(pagina.size, (400, 600))

    def test_meses_de_cuatro_y_seis_semanas_dan_el_mismo_tamano(self):
        # Febrero 2026 pinta 4 filas; enero 2028 pinta 6: la página no debería
        # cambiar de tamaño ni de layout general por eso.
        corto = calendario.render_month(FUENTES / "foto00.png", 2026, 2, (400, 600), 20, 10)
        largo = calendario.render_month(FUENTES / "foto00.png", 2028, 1, (400, 600), 20, 10)
        self.assertEqual(corto.size, largo.size)

    def test_es_determinista(self):
        a = calendario.render_month(FUENTES / "foto00.png", 2027, 3, (400, 600), 20, 10)
        b = calendario.render_month(FUENTES / "foto00.png", 2027, 3, (400, 600), 20, 10)
        self.assertEqual(a.tobytes(), b.tobytes())


class Filtros(unittest.TestCase):
    def test_sin_filters_no_hay_que_darle_nada(self):
        self.assertEqual(calendario.load_filters(None), {})

    def test_lee_el_json(self):
        archivo = RAIZ / "filtros.json"
        archivo.write_text(json.dumps({"color": "#ff0000", "tones": True}), encoding="utf-8")
        self.assertEqual(calendario.load_filters(str(archivo)),
                         {"color": "#ff0000", "tones": True})

    def test_clave_desconocida(self):
        archivo = RAIZ / "filtros_malos.json"
        archivo.write_text(json.dumps({"blur": 4}), encoding="utf-8")
        with self.assertRaises(SpecError):
            calendario.load_filters(str(archivo))

    def test_claves_con_guion_bajo_son_comentarios(self):
        archivo = RAIZ / "filtros_con_nota.json"
        archivo.write_text(
            json.dumps({"_nota": "esto es un comentario", "tones": True}), encoding="utf-8"
        )
        self.assertEqual(calendario.load_filters(str(archivo)), {"tones": True})

    def test_json_invalido(self):
        archivo = RAIZ / "filtros_rotos.json"
        archivo.write_text("{no es json", encoding="utf-8")
        with self.assertRaises(SpecError):
            calendario.load_filters(str(archivo))

    def test_apply_filters_sin_nada_devuelve_la_misma_imagen(self):
        foto = Image.new("RGBA", (20, 20), (10, 20, 30, 255))
        salida = calendario.apply_filters(foto, {}, None)
        self.assertIs(salida, foto)

    def test_recolor_cambia_los_pixeles(self):
        foto = Image.new("RGBA", (20, 20), (10, 20, 30, 255))
        salida = calendario.apply_filters(
            foto, {"color": "#ff0000", "tones": True, "recolor": {"mode": "duotone"}}, None
        )
        self.assertNotEqual(salida.tobytes(), foto.tobytes())

    def test_se_aplica_de_punta_a_punta_en_render_month(self):
        sin_filtro = calendario.render_month(FUENTES / "foto00.png", 2027, 3, (400, 600), 20, 10)
        con_filtro = calendario.render_month(
            FUENTES / "foto00.png", 2027, 3, (400, 600), 20, 10,
            filtros={"color": "#ff0000", "recolor": {"mode": "duotone"}},
        )
        self.assertNotEqual(sin_filtro.tobytes(), con_filtro.tobytes())


def correr(*args):
    """Corre calendario.main() sin ensuciar la salida de la corrida de tests."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return calendario.main(list(args))


class CLI(unittest.TestCase):
    def test_genera_un_solo_pdf_de_doce_paginas(self):
        salida = RAIZ / "calendario_cli.pdf"
        codigo = correr("--sources", str(FUENTES), "--year", "2027",
                        "--out", str(salida), "--dpi", "72")
        self.assertEqual(codigo, 0)
        self.assertTrue(salida.is_file())
        self.assertEqual(contar_paginas_pdf(salida), 12)

    def test_crea_el_directorio_de_salida_si_falta(self):
        salida = RAIZ / "sub" / "nuevo" / "calendario.pdf"
        codigo = correr("--sources", str(FUENTES), "--out", str(salida), "--dpi", "72")
        self.assertEqual(codigo, 0)
        self.assertTrue(salida.is_file())

    def test_pocas_imagenes_termina_con_error(self):
        vacio = RAIZ / "vacio"
        vacio.mkdir()
        codigo = correr("--sources", str(vacio), "--out", str(RAIZ / "no_sale.pdf"))
        self.assertEqual(codigo, 2)

    def test_filters_invalido_termina_con_error(self):
        malo = RAIZ / "filtros_cli_malos.json"
        malo.write_text(json.dumps({"nope": 1}), encoding="utf-8")
        codigo = correr("--sources", str(FUENTES), "--out", str(RAIZ / "no_sale2.pdf"),
                        "--filters", str(malo))
        self.assertEqual(codigo, 2)


if __name__ == "__main__":
    unittest.main()
