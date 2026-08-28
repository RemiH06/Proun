"""Pruebas de proun.ops.resize."""

import random
import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import resize

LIENZO = (1000, 500)


def imagen(w=400, h=200):
    return Image.new("RGBA", (w, h), (120, 120, 120, 255))


class SinCambio(unittest.TestCase):
    def test_valores_vacios(self):
        original = imagen()
        for vacio in (None, False):
            self.assertIs(resize.apply(original, vacio, LIENZO), original)

    def test_destino_igual_al_actual(self):
        original = imagen(400, 200)
        self.assertIs(resize.apply(original, [400, 200], LIENZO), original)


class Destino(unittest.TestCase):
    def test_size_en_pixeles(self):
        self.assertEqual(resize.apply(imagen(400, 200), {"size": [200, 200]}, LIENZO).size,
                         (200, 100))

    def test_size_en_fracciones_del_lienzo(self):
        # 0.5 del lienzo de 1000x500 es 500x250; la imagen 400x200 crece a 500x250.
        self.assertEqual(resize.apply(imagen(400, 200), {"size": [0.5, 0.5]}, LIENZO).size,
                         (500, 250))

    def test_par_suelto_equivale_a_size(self):
        self.assertEqual(resize.apply(imagen(), [300, 300], LIENZO).size,
                         resize.apply(imagen(), {"size": [300, 300]}, LIENZO).size)

    def test_numero_suelto_es_escala(self):
        self.assertEqual(resize.apply(imagen(200, 100), 2, LIENZO).size, (400, 200))
        self.assertEqual(resize.apply(imagen(200, 100), 0.5, LIENZO).size, (100, 50))

    def test_max_side(self):
        self.assertEqual(resize.apply(imagen(800, 400), {"max_side": 400}, LIENZO).size, (400, 200))

    def test_max_side_no_agranda(self):
        chica = imagen(100, 50)
        self.assertIs(resize.apply(chica, {"max_side": 400}, LIENZO), chica)


class Modos(unittest.TestCase):
    def test_fit_cabe_completa(self):
        # 400x200 dentro de 100x100: manda el ancho.
        self.assertEqual(resize.apply(imagen(400, 200), {"size": [100, 100]}, LIENZO).size,
                         (100, 50))

    def test_fit_agranda_por_defecto(self):
        self.assertEqual(resize.apply(imagen(100, 50), {"size": [400, 400]}, LIENZO).size,
                         (400, 200))

    def test_shrink_only_no_agranda(self):
        chica = imagen(100, 50)
        self.assertEqual(
            resize.apply(chica, {"size": [400, 400], "shrink_only": True}, LIENZO).size, (100, 50)
        )

    def test_fill_cubre_y_recorta(self):
        salida = resize.apply(imagen(400, 200), {"size": [100, 100], "mode": "fill"}, LIENZO)
        self.assertEqual(salida.size, (100, 100))

    def test_stretch_deforma(self):
        salida = resize.apply(imagen(400, 200), {"size": [100, 100], "mode": "stretch"}, LIENZO)
        self.assertEqual(salida.size, (100, 100))

    def test_keep_aspect_false_es_stretch(self):
        salida = resize.apply(imagen(400, 200), {"size": [100, 100], "keep_aspect": False}, LIENZO)
        self.assertEqual(salida.size, (100, 100))

    def test_mode_gana_sobre_keep_aspect(self):
        salida = resize.apply(
            imagen(400, 200), {"size": [100, 100], "keep_aspect": False, "mode": "fit"}, LIENZO
        )
        self.assertEqual(salida.size, (100, 50))

    def test_fill_respeta_el_ancla(self):
        base = Image.linear_gradient("L").resize((200, 400)).convert("RGBA")
        arriba = resize.apply(base, {"size": [200, 100], "mode": "fill", "anchor": "top"}, LIENZO)
        abajo = resize.apply(base, {"size": [200, 100], "mode": "fill", "anchor": "bottom"}, LIENZO)
        self.assertLess(arriba.getpixel((100, 50))[0], abajo.getpixel((100, 50))[0])

    def test_ancla_random_reproducible(self):
        args = ({"size": [100, 100], "mode": "fill", "anchor": "random"}, LIENZO)
        a = resize.apply(imagen(400, 200), *args, random.Random(8))
        b = resize.apply(imagen(400, 200), *args, random.Random(8))
        self.assertEqual(a.tobytes(), b.tobytes())


class Remuestreo(unittest.TestCase):
    def test_filtros_validos(self):
        for filtro in ("nearest", "bilinear", "bicubic", "lanczos", "LANCZOS"):
            salida = resize.apply(imagen(), {"size": [50, 50], "resample": filtro}, LIENZO)
            self.assertEqual(salida.size, (50, 25), filtro)

    def test_filtro_invalido(self):
        with self.assertRaises(SpecError):
            resize.apply(imagen(), {"size": [50, 50], "resample": "magia"}, LIENZO)


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            resize.apply(imagen(), {"tamano": [10, 10]}, LIENZO)

    def test_destinos_excluyentes(self):
        with self.assertRaises(SpecError) as caso:
            resize.apply(imagen(), {"size": [10, 10], "scale": 2}, LIENZO)
        self.assertIn("solo uno", str(caso.exception))

    def test_sin_destino(self):
        with self.assertRaises(SpecError):
            resize.apply(imagen(), {"mode": "fill"}, LIENZO)

    def test_modo_invalido(self):
        with self.assertRaises(SpecError):
            resize.apply(imagen(), {"size": [10, 10], "mode": "encajar"}, LIENZO)

    def test_escala_no_positiva(self):
        for malo in (0, -1, "2", True):
            with self.assertRaises(SpecError, msg=malo):
                resize.apply(imagen(), {"scale": malo}, LIENZO)

    def test_size_mal_formado(self):
        for malo in ([100], [1, 2, 3], "100x100"):
            with self.assertRaises(SpecError, msg=malo):
                resize.apply(imagen(), {"size": malo}, LIENZO)

    def test_tipo_invalido(self):
        with self.assertRaises(SpecError):
            resize.apply(imagen(), "grande", LIENZO)

    def test_nunca_devuelve_dimension_cero(self):
        # Una escala minúscula tiene que dar al menos un pixel, no cero.
        self.assertEqual(resize.apply(imagen(400, 200), 0.0001, LIENZO).size, (1, 1))


if __name__ == "__main__":
    unittest.main()