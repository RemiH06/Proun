"""Pruebas de proun.naming."""

import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from proun import naming, spec
from proun.errors import SpecError

RAIZ = Path(tempfile.mkdtemp(prefix="proun-naming-"))
FUENTES = RAIZ / "fuentes"


def setUpModule():
    FUENTES.mkdir(parents=True)
    Image.new("RGB", (200, 200), (200, 60, 60)).save(FUENTES / "a.png")


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


def config(**extra):
    return spec.build({"sources": [str(FUENTES)], "colors": ["3ba7ff"], "seeds": [1], **extra})


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

    def test_config_hash_se_agrega_al_final(self):
        nombre = naming.filename(1, "ffffff", 5, config_hash="1a2b3c4d")
        self.assertEqual(nombre, "wp_0001_ffffff_5_1a2b3c4d.png")

    def test_config_hash_invalido(self):
        for malo in ("no-hex", "1a2b3c4", "1A2B3C4D", "1a2b3c4d5"):
            with self.assertRaises(SpecError, msg=malo):
                naming.filename(1, "ffffff", 5, config_hash=malo)


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

    def test_con_hash_de_config(self):
        nombre = naming.filename(7, "3ba7ff", 849213, config_hash="1a2b3c4d")
        self.assertEqual(naming.parse(nombre),
                         {"index": 7, "color": "3ba7ff", "seed": 849213, "hash": "1a2b3c4d"})

    def test_sin_hash_no_agrega_la_clave(self):
        self.assertNotIn("hash", naming.parse(naming.filename(7, "3ba7ff", 849213)))


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


class ContentHash(unittest.TestCase):
    def test_es_determinista(self):
        self.assertEqual(naming.content_hash(config()), naming.content_hash(config()))

    def test_es_hexadecimal_de_ocho(self):
        self.assertRegex(naming.content_hash(config()), r"^[0-9a-f]{8}$")

    def test_cambia_con_el_fondo(self):
        self.assertNotEqual(naming.content_hash(config()),
                            naming.content_hash(config(background="#ff0000")))

    def test_cambia_con_el_layout(self):
        self.assertNotEqual(naming.content_hash(config()),
                            naming.content_hash(config(layout={"mode": "grid"})))

    def test_cambia_con_defaults_de_recoloreado(self):
        self.assertNotEqual(
            naming.content_hash(config()),
            naming.content_hash(config(defaults={"recolor": {"mode": "hue"}})),
        )

    def test_no_cambia_con_lo_que_ya_viaja_en_el_nombre(self):
        # color, semilla, formato y numeración no necesitan hash propio: ya
        # se distinguen solos en el nombre del archivo.
        base = naming.content_hash(config())
        self.assertEqual(base, naming.content_hash(config(colors=["ff0000"])))
        self.assertEqual(base, naming.content_hash(config(seeds=[999])))
        self.assertEqual(base, naming.content_hash(config(format="jpg")))
        self.assertEqual(base, naming.content_hash(config(start_index=50)))
        self.assertEqual(base, naming.content_hash(config(output="otro_directorio")))

    def test_resolutions_no_cambia_el_hash_si_la_referencia_no_se_mueve(self):
        # `resolutions` en sí no afecta el resultado de una resolución dada,
        # pero por defecto también fija `reference` (la base del escalado):
        # sin fijarla aparte, cambiar resolutions sí cambia el resultado.
        base = naming.content_hash(config(reference="1920x1080"))
        self.assertEqual(
            base, naming.content_hash(config(resolutions=["800x600"], reference="1920x1080"))
        )


if __name__ == "__main__":
    unittest.main()