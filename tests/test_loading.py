"""Pruebas de proun.loading."""

import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from proun import loading
from proun.errors import SourceError

RAIZ = Path(tempfile.mkdtemp(prefix="proun-loading-"))


def setUpModule():
    (RAIZ / "sub").mkdir(parents=True)
    Image.new("RGB", (30, 30), (200, 40, 40)).save(RAIZ / "a.png")
    Image.new("RGB", (40, 20), (40, 200, 40)).save(RAIZ / "b.jpg")
    Image.new("RGB", (10, 10), (40, 40, 200)).save(RAIZ / "sub" / "c.png")
    (RAIZ / "notas.txt").write_text("esto no es una imagen", encoding="utf-8")
    (RAIZ / "roto.png").write_bytes(b"tampoco lo es")

    girada = Image.new("RGB", (40, 20), (10, 10, 10))
    exif = girada.getexif()
    exif[274] = 6  # orientación: girar un cuarto de vuelta
    girada.save(RAIZ / "girada.jpg", exif=exif)


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


def setUp_limpio():
    loading.clear_cache()


class Expansion(unittest.TestCase):
    def nombres(self, patrones):
        return sorted(p.name for p in loading.expand(patrones))

    def test_directorio_entra_recursivo(self):
        self.assertEqual(self.nombres(RAIZ), ["a.png", "b.jpg", "c.png", "girada.jpg", "roto.png"])

    def test_ignora_extensiones_ajenas(self):
        self.assertNotIn("notas.txt", self.nombres(RAIZ))

    def test_glob(self):
        self.assertEqual(self.nombres(str(RAIZ / "*.png")), ["a.png", "roto.png"])

    def test_glob_recursivo(self):
        self.assertIn("c.png", self.nombres(str(RAIZ / "**" / "*.png")))

    def test_archivo_suelto_y_texto_o_path(self):
        self.assertEqual(self.nombres(RAIZ / "a.png"), ["a.png"])
        self.assertEqual(self.nombres(str(RAIZ / "a.png")), ["a.png"])

    def test_varios_patrones_sin_duplicados(self):
        salida = loading.expand([RAIZ / "a.png", str(RAIZ / "*.png"), RAIZ])
        self.assertEqual(len(salida), len(set(salida)))
        self.assertIn("a.png", [p.name for p in salida])

    def test_devuelve_rutas_absolutas(self):
        self.assertTrue(all(p.is_absolute() for p in loading.expand(RAIZ)))

    def test_patron_vacio_no_truena(self):
        # Decidir si la lista vacía es un problema le toca a quien llama.
        self.assertEqual(loading.expand(str(RAIZ / "no-existe-*.png")), [])
        self.assertEqual(loading.expand([]), [])


class Carga(unittest.TestCase):
    def setUp(self):
        loading.clear_cache()

    def test_devuelve_rgba(self):
        im = loading.load(RAIZ / "a.png")
        self.assertEqual(im.mode, "RGBA")
        self.assertEqual(im.size, (30, 30))

    def test_corrige_orientacion_exif(self):
        # El archivo mide 40x20 en disco, pero pide un cuarto de vuelta.
        self.assertEqual(loading.load(RAIZ / "girada.jpg").size, (20, 40))

    def test_entrega_copias_independientes(self):
        primera = loading.load(RAIZ / "a.png")
        primera.paste((0, 0, 0, 255), (0, 0, 30, 30))
        segunda = loading.load(RAIZ / "a.png")
        self.assertNotEqual(primera.getpixel((5, 5)), segunda.getpixel((5, 5)))

    def test_la_cache_evita_releer(self):
        loading.load(RAIZ / "a.png")
        copia = RAIZ / "temporal.png"
        shutil.copy(RAIZ / "a.png", copia)
        loading.load(copia)
        copia.unlink()
        # Ya está en caché, así que sigue cargando aunque el archivo se fue.
        self.assertEqual(loading.load(copia).size, (30, 30))
        loading.clear_cache()
        with self.assertRaises(SourceError):
            loading.load(copia)

    def test_inexistente(self):
        with self.assertRaises(SourceError):
            loading.load(RAIZ / "fantasma.png")

    def test_archivo_ilegible(self):
        with self.assertRaises(SourceError):
            loading.load(RAIZ / "roto.png")

    def test_el_mensaje_dice_cual_archivo(self):
        with self.assertRaises(SourceError) as caso:
            loading.load(RAIZ / "roto.png")
        self.assertIn("roto.png", str(caso.exception))


if __name__ == "__main__":
    unittest.main()