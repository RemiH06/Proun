"""Pruebas de proun.colors y proun.errors.

Correr con: python3 -m unittest discover -s tests
"""

import unittest

from proun import colors
from proun.errors import SourceError, SpecError


class Parseo(unittest.TestCase):
    def test_formatos_equivalentes(self):
        for entrada in ("#ff0088", "ff0088", "FF0088", "#f08", "f08", [255, 0, 136]):
            self.assertEqual(colors.parse(entrada), (255, 0, 136), entrada)

    def test_espacios_alrededor(self):
        self.assertEqual(colors.parse("  #f08  "), (255, 0, 136))

    def test_ida_y_vuelta(self):
        self.assertEqual(colors.to_hex(colors.parse("#3ba7ff")), "3ba7ff")

    def test_to_hex_acepta_tupla_o_texto(self):
        self.assertEqual(colors.to_hex((255, 0, 136)), "ff0088")
        self.assertEqual(colors.to_hex("#F08"), "ff0088")

    def test_invalidos(self):
        for malo in ("#12345", "zzzzzz", "", "#", [1, 2], [1, 2, 3, 4], [300, 0, 0],
                     [-1, 0, 0], ["a", "b", "c"], None):
            with self.assertRaises(SpecError, msg=malo):
                colors.parse(malo)


class Mezclas(unittest.TestCase):
    def test_mix_en_los_extremos(self):
        negro, blanco = (0, 0, 0), (255, 255, 255)
        self.assertEqual(colors.mix(negro, blanco, 0), negro)
        self.assertEqual(colors.mix(negro, blanco, 1), blanco)
        self.assertEqual(colors.mix(negro, blanco, 0.5), (128, 128, 128))

    def test_mix_recorta_fuera_de_rango(self):
        self.assertEqual(colors.mix((0, 0, 0), (255, 255, 255), 5), (255, 255, 255))
        self.assertEqual(colors.mix((0, 0, 0), (255, 255, 255), -5), (0, 0, 0))

    def test_shade(self):
        gris = (100, 100, 100)
        self.assertEqual(colors.shade(gris, 0), (0, 0, 0))
        self.assertEqual(colors.shade(gris, 1), gris)
        self.assertEqual(colors.shade(gris, 2), (255, 255, 255))
        self.assertLess(colors.shade(gris, 0.5)[0], gris[0])
        self.assertGreater(colors.shade(gris, 1.5)[0], gris[0])

    def test_shade_no_acepta_negativos(self):
        with self.assertRaises(SpecError):
            colors.shade((100, 100, 100), -1)


class Matiz(unittest.TestCase):
    def test_hue_conocidos(self):
        self.assertAlmostEqual(colors.hue_of("#ff0000"), 0.0, places=3)
        self.assertAlmostEqual(colors.hue_of("#00ff00"), 1 / 3, places=3)
        self.assertAlmostEqual(colors.hue_of("#0000ff"), 2 / 3, places=3)


class Espectro(unittest.TestCase):
    def test_cantidad_y_unicidad(self):
        paleta = colors.spectrum(6)
        self.assertEqual(len(paleta), 6)
        self.assertEqual(len(set(paleta)), 6)

    def test_es_determinista(self):
        self.assertEqual(colors.spectrum(5), colors.spectrum(5))

    def test_arco_parcial(self):
        completo = colors.spectrum(4, span=1.0)
        cuarto = colors.spectrum(4, span=0.25)
        self.assertNotEqual(completo, cuarto)
        self.assertEqual(len(cuarto), 4)

    def test_uno_solo(self):
        self.assertEqual(len(colors.spectrum(1)), 1)

    def test_invalidos(self):
        for kwargs in ({"count": 0}, {"count": -3}, {"count": 3, "saturation": 2},
                       {"count": 3, "value": -0.1}):
            with self.assertRaises(SpecError, msg=kwargs):
                colors.spectrum(**kwargs)


class Errores(unittest.TestCase):
    def test_jerarquia(self):
        self.assertTrue(issubclass(SpecError, ValueError))
        self.assertTrue(issubclass(SourceError, SpecError))


if __name__ == "__main__":
    unittest.main()