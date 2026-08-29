"""Pruebas de proun.naming."""

import unittest
from pathlib import Path

from proun import naming
from proun.errors import SpecError


class Nombres(unittest.TestCase):
    def test_formato(self):
        self.assertEqual(naming.filename(7, "3ba7ff", 849213), "wp_0007_3ba7ff_849213.png")

    def test_relleno_a_cuatro_digitos(self):
        self.assertEqual(naming.filename(1, "ffffff", 1), "wp_0001_ffffff_1.png")

    def test_indices_grandes_no_se_truncan(self):
        self.assertTrue(naming.filename(123456, "ffffff", 1).startswith("wp_123456_"))

    def test_normaliza_el_color(self):
        for entrada in ("3BA7FF", "#3ba7ff", "#3BA7FF"):
            self.assertEqual(naming.filename(1, entrada, 5), "wp_0001_3ba7ff_5.png", entrada)

    def test_extension(self):
        self.assertTrue(naming.filename(1, "ffffff", 5, "jpg").endswith(".jpg"))
        self.assertTrue(naming.filename(1, "ffffff", 5, ".webp").endswith(".webp"))

    def test_valores_negativos(self):
        with self.assertRaises(SpecError):
            naming.filename(-1, "ffffff", 5)
        with self.assertRaises(SpecError):
            naming.filename(1, "ffffff", -5)


class Directorios(unittest.TestCase):
    def test_una_carpeta_por_resolucion(self):
        ruta = naming.resolution_dir("wallpapers", (1920, 1080))
        self.assertEqual(ruta, Path("wallpapers/1920x1080"))

    def test_acepta_path(self):
        ruta = naming.resolution_dir(Path("/tmp/salida"), (800, 600))
        self.assertEqual(ruta.name, "800x600")


class Lectura(unittest.TestCase):
    def test_ida_y_vuelta(self):
        nombre = naming.filename(7, "3ba7ff", 849213)
        self.assertEqual(naming.parse(nombre),
                         {"index": 7, "color": "3ba7ff", "seed": 849213})

    def test_acepta_ruta_completa(self):
        datos = naming.parse("wallpapers/1920x1080/wp_0042_ff0088_12345.png")
        self.assertEqual(datos["index"], 42)
        self.assertEqual(datos["color"], "ff0088")
        self.assertEqual(datos["seed"], 12345)

    def test_cualquier_extension(self):
        for ext in ("png", "jpg", "webp"):
            self.assertEqual(naming.parse(f"wp_0001_ffffff_9.{ext}")["seed"], 9, ext)

    def test_nombres_ajenos(self):
        for malo in ("foto.png", "wp_1_ffffff_5.png", "wp_0001_zzzzzz_5.png",
                     "wp_0001_ffffff.png", "wp_0001_ffffff_abc.png", ""):
            with self.assertRaises(SpecError, msg=malo):
                naming.parse(malo)


class Convencion(unittest.TestCase):
    def test_el_indice_identifica_la_composicion(self):
        # Mismo índice y misma semilla, distinto color: es el mismo collage
        # recoloreado, y por eso comparten número.
        azul = naming.filename(3, "3ba7ff", 555)
        rojo = naming.filename(3, "ff0000", 555)
        self.assertNotEqual(azul, rojo)
        self.assertEqual(naming.parse(azul)["seed"], naming.parse(rojo)["seed"])
        self.assertEqual(naming.parse(azul)["index"], naming.parse(rojo)["index"])

    def test_la_semilla_del_nombre_es_la_que_regenera(self):
        datos = naming.parse("wp_0009_112233_777888.png")
        self.assertEqual(datos["seed"], 777888)


if __name__ == "__main__":
    unittest.main()