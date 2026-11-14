"""Topes de memoria y CPU del motor: una sola especificación no puede pedir
gigas de RAM ni horas de CPU (auditoría de seguridad del 2026-11-14, antes de
publicar el GUI). Cada prueba usa un valor que antes pasaba y reventaba."""

import random
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from proun import geometry, loading
from proun.errors import SpecError
from proun.ops import mosaic, resize, stain, text


class TopeDePixeles(unittest.TestCase):
    def test_debajo_del_tope_pasa(self):
        geometry.tope((6528, 4896), "mosaico de recetas/tinta.py")

    def test_encima_del_tope_falla_con_el_nombre(self):
        with self.assertRaisesRegex(SpecError, "resize pediría"):
            geometry.tope((60000, 60000), "resize")


class Resize(unittest.TestCase):
    def test_size_gigante(self):
        im = Image.new("RGBA", (10, 10))
        with self.assertRaises(SpecError):
            resize.apply(im, {"size": [60000, 60000], "mode": "stretch"}, (1920, 1080))

    def test_scale_gigante(self):
        im = Image.new("RGBA", (100, 100))
        with self.assertRaises(SpecError):
            resize.apply(im, {"scale": 1000}, (1920, 1080))

    def test_fill_con_imagen_muy_alargada(self):
        # El destino cabe, pero cubrirlo con una imagen de 1x1000 agrandaría
        # el otro lado a millones de px antes de recortar.
        im = Image.new("RGBA", (1, 1000))
        with self.assertRaises(SpecError):
            resize.apply(im, {"size": [4000, 4000], "mode": "fill"}, (4000, 4000))

    def test_un_resize_normal_sigue_igual(self):
        im = Image.new("RGBA", (3000, 2000))
        out = resize.apply(im, {"size": [1920, 1080], "mode": "fill"}, (1920, 1080))
        self.assertEqual(out.size, (1920, 1080))


class Mosaico(unittest.TestCase):
    def test_tile_gigante(self):
        im = Image.new("RGBA", (10, 10))
        with self.assertRaises(SpecError):
            mosaic.apply(im, {"tile": [10000, 10000], "grid": [1, 1]}, (1920, 1080))

    def test_hoja_gigante_con_pocas_piezas(self):
        # 141x141 piezas no llega al tope de piezas (20 000), pero la hoja
        # serían 14100x14100 px.
        im = Image.new("RGBA", (100, 100))
        with self.assertRaisesRegex(SpecError, "el mosaico pediría"):
            mosaic.apply(im, {"grid": [141, 141]}, (1920, 1080))

    def test_mosaico_de_recetas_tinta_cabe(self):
        im = Image.new("RGBA", (3264, 2448))
        out = mosaic.apply(im, {"grid": [2, 2], "mirror": True}, (1920, 1080))
        self.assertEqual(out.size, (6528, 4896))


class Texto(unittest.TestCase):
    def test_line_spacing_enorme(self):
        with self.assertRaisesRegex(SpecError, "el texto"):
            text.build({"text": "uno\ndos", "line_spacing": 5000, "wrap": 1})

    def test_texto_larguisimo_sin_wrap(self):
        with self.assertRaisesRegex(SpecError, "el texto"):
            text.build({"text": "proun " * 200})

    def test_un_titulo_normal_sigue_igual(self):
        self.assertGreater(text.build({"text": "Proun 1919"}).width, 1)


class Octavas(unittest.TestCase):
    def test_clouds_valida_octaves_como_stain(self):
        # `clouds` lo usan fondo y acabado: antes hacía int(octaves) sin tope.
        with self.assertRaisesRegex(SpecError, "octaves"):
            stain.clouds((64, 64), {"octaves": 100000}, random.Random(1))

    def test_clouds_dentro_del_rango(self):
        self.assertEqual(stain.clouds((64, 64), {"octaves": 6}, random.Random(1)).size, (64, 64))


class CacheDeImagenes(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp(prefix="proun-cache-"))
        self.fotos = []
        for i in range(4):
            ruta = self.carpeta / f"foto{i}.png"
            Image.new("RGB", (100, 100), (i * 40, 0, 0)).save(ruta)
            self.fotos.append(ruta)
        loading._cache.clear()

    def tearDown(self):
        loading._cache.clear()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_respeta_el_tope_de_memoria(self):
        # Cada foto son 100x100x4 = 40 000 bytes: caben dos.
        with patch.object(loading, "CACHE_BYTES", 80_000):
            for foto in self.fotos:
                loading.load(foto)
        self.assertEqual(list(loading._cache), [f.resolve() for f in self.fotos[2:]])

    def test_saca_primero_la_menos_usada(self):
        with patch.object(loading, "CACHE_BYTES", 80_000):
            loading.load(self.fotos[0])
            loading.load(self.fotos[1])
            loading.load(self.fotos[0])
            loading.load(self.fotos[2])
        self.assertEqual(list(loading._cache), [self.fotos[0].resolve(), self.fotos[2].resolve()])

    def test_la_miniatura_no_llena_la_cache(self):
        mini = loading.thumbnail(self.fotos[0], 32)
        self.assertEqual(mini.size, (32, 32))
        self.assertEqual(len(loading._cache), 0)

    def test_miniatura_de_algo_que_no_existe(self):
        with self.assertRaises(SpecError):
            loading.thumbnail(self.carpeta / "no.png", 32)


if __name__ == "__main__":
    unittest.main()
