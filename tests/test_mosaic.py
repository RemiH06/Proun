"""Pruebas de proun.ops.mosaic."""

import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import mosaic

LIENZO = (1920, 1080)


def imagen(w=300, h=300):
    return Image.new("RGBA", (w, h), (120, 120, 120, 255))


def asimetrica(w=100, h=100):
    """Pieza con una esquina marcada, para detectar espejados y desfases."""
    im = Image.new("RGBA", (w, h), (30, 30, 30, 255))
    im.paste((240, 240, 240, 255), (0, 0, w // 4, h // 4))
    return im


class SinMosaico(unittest.TestCase):
    def test_valores_vacios(self):
        original = imagen()
        for vacio in (None, False):
            self.assertIs(mosaic.apply(original, vacio, LIENZO), original)

    def test_cero_no_es_vacio(self):
        with self.assertRaises(SpecError):
            mosaic.apply(imagen(), 0, LIENZO)


class Cuadricula(unittest.TestCase):
    def test_entero_suelto_es_cuadrado(self):
        # El caso original: 300x300 a 600x600 sin escalar nada.
        self.assertEqual(mosaic.apply(imagen(300, 300), 2, LIENZO).size, (600, 600))

    def test_tira_horizontal(self):
        self.assertEqual(mosaic.apply(imagen(300, 300), [4, 1], LIENZO).size, (1200, 300))

    def test_tira_vertical(self):
        self.assertEqual(mosaic.apply(imagen(300, 300), [1, 3], LIENZO).size, (300, 900))

    def test_par_suelto_equivale_a_grid(self):
        self.assertEqual(mosaic.apply(imagen(), [2, 3], LIENZO).size,
                         mosaic.apply(imagen(), {"grid": [2, 3]}, LIENZO).size)

    def test_grid_de_uno_devuelve_la_pieza(self):
        self.assertEqual(mosaic.apply(imagen(300, 200), [1, 1], LIENZO).size, (300, 200))

    def test_las_piezas_se_repiten_de_verdad(self):
        pieza = asimetrica(100, 100)
        salida = mosaic.apply(pieza, [2, 2], LIENZO)
        # La marca de la esquina aparece en las cuatro piezas.
        for x, y in ((10, 10), (110, 10), (10, 110), (110, 110)):
            self.assertEqual(salida.getpixel((x, y))[:3], (240, 240, 240), (x, y))


class TamanoExacto(unittest.TestCase):
    def test_llena_y_recorta(self):
        salida = mosaic.apply(imagen(200, 200), {"size": [1920, 1080]}, LIENZO)
        self.assertEqual(salida.size, (1920, 1080))

    def test_size_en_fracciones_del_lienzo(self):
        salida = mosaic.apply(imagen(200, 200), {"size": [0.5, 0.5]}, LIENZO)
        self.assertEqual(salida.size, (960, 540))

    def test_size_menor_que_la_pieza(self):
        self.assertEqual(mosaic.apply(imagen(300, 300), {"size": [100, 50]}, LIENZO).size,
                         (100, 50))


class Pieza(unittest.TestCase):
    def test_tile_reescala_antes_de_repetir(self):
        salida = mosaic.apply(imagen(300, 300), {"tile": [150, 150], "grid": [2, 2]}, LIENZO)
        self.assertEqual(salida.size, (300, 300))

    def test_tile_en_fracciones_de_la_imagen(self):
        salida = mosaic.apply(imagen(300, 300), {"tile": [0.5, 0.5], "grid": [4, 1]}, LIENZO)
        self.assertEqual(salida.size, (600, 150))

    def test_resample_invalido(self):
        with self.assertRaises(SpecError):
            mosaic.apply(imagen(), {"tile": [50, 50], "grid": [2, 2], "resample": "magia"}, LIENZO)


class EspejoYDesfase(unittest.TestCase):
    def test_mirror_voltea_las_impares(self):
        salida = mosaic.apply(asimetrica(100, 100), {"grid": [2, 1], "mirror": True}, LIENZO)
        # La marca de la primera pieza está a la izquierda; en la segunda, a la derecha.
        self.assertEqual(salida.getpixel((10, 10))[:3], (240, 240, 240))
        self.assertEqual(salida.getpixel((190, 10))[:3], (240, 240, 240))

    def test_sin_mirror_no_voltea(self):
        salida = mosaic.apply(asimetrica(100, 100), {"grid": [2, 1]}, LIENZO)
        self.assertEqual(salida.getpixel((110, 10))[:3], (240, 240, 240))
        self.assertNotEqual(salida.getpixel((190, 10))[:3], (240, 240, 240))

    def test_offset_conserva_el_tamano(self):
        salida = mosaic.apply(imagen(100, 100), {"grid": [3, 3], "offset": [0.5, 0]}, LIENZO)
        self.assertEqual(salida.size, (300, 300))

    def test_offset_desplaza_filas_alternas(self):
        salida = mosaic.apply(asimetrica(100, 100), {"grid": [3, 2], "offset": [0.5, 0]}, LIENZO)
        # Fila 0 sin correr: marca en x=10. Fila 1 corrida media pieza: marca en x=60.
        self.assertEqual(salida.getpixel((10, 10))[:3], (240, 240, 240))
        self.assertEqual(salida.getpixel((60, 110))[:3], (240, 240, 240))

    def test_offset_numero_suelto_es_horizontal(self):
        a = mosaic.apply(asimetrica(), {"grid": [2, 2], "offset": 0.5}, LIENZO)
        b = mosaic.apply(asimetrica(), {"grid": [2, 2], "offset": [0.5, 0]}, LIENZO)
        self.assertEqual(a.tobytes(), b.tobytes())

    def test_offset_fuera_de_rango(self):
        for malo in (1, 1.5, -0.2, "medio"):
            with self.assertRaises(SpecError, msg=malo):
                mosaic.apply(imagen(), {"grid": [2, 2], "offset": malo}, LIENZO)


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            mosaic.apply(imagen(), {"cuadricula": [2, 2]}, LIENZO)

    def test_grid_y_size_son_excluyentes(self):
        with self.assertRaises(SpecError) as caso:
            mosaic.apply(imagen(), {"grid": [2, 2], "size": [500, 500]}, LIENZO)
        self.assertIn("no los dos", str(caso.exception))

    def test_sin_grid_ni_size(self):
        with self.assertRaises(SpecError):
            mosaic.apply(imagen(), {"mirror": True}, LIENZO)

    def test_grid_mal_formado(self):
        for malo in ([2], [2, 2, 2], [0, 2], [2, -1], [2.5, 2], [True, 2], "2x2"):
            with self.assertRaises(SpecError, msg=malo):
                mosaic.apply(imagen(), {"grid": malo}, LIENZO)

    def test_tope_de_piezas(self):
        # Una pieza de 1x1 llenando 1920x1080 serían dos millones de pegados.
        with self.assertRaises(SpecError) as caso:
            mosaic.apply(imagen(1, 1), {"size": [1920, 1080]}, LIENZO)
        self.assertIn("piezas", str(caso.exception))

    def test_tipo_invalido(self):
        with self.assertRaises(SpecError):
            mosaic.apply(imagen(), "doble", LIENZO)

    def test_no_muta_el_original(self):
        original = asimetrica(100, 100)
        antes = original.tobytes()
        mosaic.apply(original, {"grid": [2, 2], "mirror": True}, LIENZO)
        self.assertEqual(original.tobytes(), antes)


if __name__ == "__main__":
    unittest.main()