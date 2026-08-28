"""Pruebas de proun.geometry."""

import random
import unittest

from proun import geometry
from proun.errors import SpecError


class Medidas(unittest.TestCase):
    def test_entero_es_pixel_y_flotante_es_fraccion(self):
        self.assertEqual(geometry.measure(600, 1920), 600)
        self.assertEqual(geometry.measure(0.5, 1920), 960)

    def test_uno_y_uno_punto_cero_son_distintos(self):
        # El corazón de la convención: 1 es un pixel, 1.0 es todo el ancho.
        self.assertEqual(geometry.measure(1, 1920), 1)
        self.assertEqual(geometry.measure(1.0, 1920), 1920)

    def test_minimo_configurable(self):
        self.assertEqual(geometry.measure(0, 1920, minimum=0), 0)
        with self.assertRaises(SpecError):
            geometry.measure(0, 1920)

    def test_redondeo(self):
        self.assertEqual(geometry.measure(0.333, 1000), 333)

    def test_rechaza_lo_que_no_es_numero(self):
        for malo in ("600", None, True, False, [600]):
            with self.assertRaises(SpecError, msg=malo):
                geometry.measure(malo, 1920)

    def test_mensaje_lleva_el_nombre(self):
        with self.assertRaises(SpecError) as caso:
            geometry.measure("x", 100, name="resize.size[ancho]")
        self.assertIn("resize.size[ancho]", str(caso.exception))


class Pares(unittest.TestCase):
    def test_mezcla_pixeles_y_fracciones(self):
        self.assertEqual(geometry.pair([960, 0.5], (1920, 1080)), (960, 540))

    def test_rechaza_longitud_equivocada(self):
        for malo in ([100], [1, 2, 3], 100, "100x100", None):
            with self.assertRaises(SpecError, msg=malo):
                geometry.pair(malo, (1920, 1080))


class Anclas(unittest.TestCase):
    def test_nombradas(self):
        self.assertEqual(geometry.anchor_factors("center"), (0.5, 0.5))
        self.assertEqual(geometry.anchor_factors("topleft"), (0.0, 0.0))
        self.assertEqual(geometry.anchor_factors("bottomright"), (1.0, 1.0))

    def test_tolera_formato(self):
        for variante in ("TopLeft", "top-left", "top_left", " topleft "):
            self.assertEqual(geometry.anchor_factors(variante), (0.0, 0.0), variante)

    def test_par_explicito(self):
        self.assertEqual(geometry.anchor_factors([0.25, 0.75]), (0.25, 0.75))

    def test_random_necesita_generador(self):
        with self.assertRaises(SpecError):
            geometry.anchor_factors("random")
        valor = geometry.anchor_factors("random", random.Random(3))
        self.assertEqual(valor, geometry.anchor_factors("random", random.Random(3)))

    def test_desconocida(self):
        with self.assertRaises(SpecError):
            geometry.anchor_factors("esquinita")


class Proporciones(unittest.TestCase):
    def test_formatos(self):
        for entrada in ("16:9", "16/9", 16 / 9):
            self.assertAlmostEqual(geometry.parse_aspect(entrada), 16 / 9, places=4)

    def test_invalidas(self):
        for malo in ("16", "16:9:3", "a:b", "16:0", 0, -2, "-16:9"):
            with self.assertRaises(SpecError, msg=malo):
                geometry.parse_aspect(malo)


class Cajas(unittest.TestCase):
    def test_fit_box_recorta_el_lado_largo(self):
        # Una imagen cuadrada a 16:9 pierde alto, no ancho.
        self.assertEqual(geometry.fit_box((400, 400), 16 / 9), (400, 225))
        # Una panorámica a 1:1 pierde ancho.
        self.assertEqual(geometry.fit_box((800, 200), 1.0), (200, 200))

    def test_fit_box_no_agranda(self):
        ancho, alto = geometry.fit_box((300, 300), 16 / 9)
        self.assertLessEqual(ancho, 300)
        self.assertLessEqual(alto, 300)

    def test_place_box(self):
        self.assertEqual(geometry.place_box((100, 100), (500, 300), (0.5, 0.5)), (200, 100))
        self.assertEqual(geometry.place_box((100, 100), (500, 300), (0.0, 0.0)), (0, 0))
        self.assertEqual(geometry.place_box((100, 100), (500, 300), (1.0, 1.0)), (400, 200))

    def test_place_box_con_inner_mas_grande(self):
        # Colocar algo más grande que el contenedor da coordenadas negativas,
        # que es justo lo que se quiere para recortar centrado.
        self.assertEqual(geometry.place_box((600, 400), (500, 300), (0.5, 0.5)), (-50, -50))


if __name__ == "__main__":
    unittest.main()