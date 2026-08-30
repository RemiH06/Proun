"""Pruebas de proun.ops.stain."""

import random
import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import stain


def pieza(w=120, h=120, alfa=255):
    return Image.new("RGBA", (w, h), (60, 60, 70, alfa))


def rng(semilla=4):
    return random.Random(semilla)


def alfas(im):
    return im.getchannel("A")


def promedio(im):
    oscuro, claro = alfas(im).getextrema()
    return (oscuro + claro) / 2


class SinMancha(unittest.TestCase):
    def test_vacio_no_toca_la_capa(self):
        original = pieza()
        for vacio in (None, False):
            self.assertIs(stain.apply(original, vacio, rng()), original, vacio)

    def test_amount_cero_no_hace_nada(self):
        original = pieza()
        self.assertIs(stain.apply(original, {"amount": 0}, rng()), original)

    def test_amount_cero_no_exige_generador(self):
        self.assertIsNotNone(stain.apply(pieza(), 0))


class Desgaste(unittest.TestCase):
    def test_come_alfa(self):
        salida = stain.apply(pieza(), 0.6, rng())
        self.assertLess(alfas(salida).getextrema()[0], 255)

    def test_mas_amount_come_mas(self):
        suave = promedio(stain.apply(pieza(), 0.2, rng()))
        fuerte = promedio(stain.apply(pieza(), 0.9, rng()))
        self.assertLess(fuerte, suave)

    def test_nunca_agrega_opacidad(self):
        salida = stain.apply(pieza(), 0.8, rng())
        self.assertLessEqual(alfas(salida).getextrema()[1], 255)

    def test_respeta_el_alfa_que_ya_traia(self):
        # Una capa a medias no puede volverse más opaca por mancharla.
        salida = stain.apply(pieza(alfa=100), 0.5, rng())
        self.assertLessEqual(alfas(salida).getextrema()[1], 100)

    def test_no_toca_el_color(self):
        salida = stain.apply(pieza(), 0.7, rng())
        self.assertEqual(salida.getpixel((60, 60))[:3], (60, 60, 70))

    def test_numero_suelto_equivale_a_amount(self):
        self.assertEqual(stain.apply(pieza(), 0.5, rng(3)).tobytes(),
                         stain.apply(pieza(), {"amount": 0.5}, rng(3)).tobytes())

    def test_conserva_el_tamano(self):
        self.assertEqual(stain.apply(pieza(80, 200), 0.5, rng()).size, (80, 200))

    def test_no_muta_el_original(self):
        original = pieza()
        antes = original.tobytes()
        stain.apply(original, 0.8, rng())
        self.assertEqual(original.tobytes(), antes)


class Reproducibilidad(unittest.TestCase):
    def test_misma_semilla_misma_mancha(self):
        self.assertEqual(stain.apply(pieza(), 0.6, rng(7)).tobytes(),
                         stain.apply(pieza(), 0.6, rng(7)).tobytes())

    def test_semillas_distintas_manchas_distintas(self):
        self.assertNotEqual(stain.apply(pieza(), 0.6, rng(7)).tobytes(),
                            stain.apply(pieza(), 0.6, rng(8)).tobytes())

    def test_exige_generador(self):
        with self.assertRaises(SpecError) as caso:
            stain.apply(pieza(), 0.6)
        self.assertIn("semilla", str(caso.exception))


class Forma(unittest.TestCase):
    def test_escala_cambia_el_tamano_de_las_manchas(self):
        self.assertNotEqual(stain.apply(pieza(), {"amount": 0.7, "scale": 0.1}, rng(2)).tobytes(),
                            stain.apply(pieza(), {"amount": 0.7, "scale": 0.9}, rng(2)).tobytes())

    def test_octavas_agregan_detalle(self):
        self.assertNotEqual(stain.apply(pieza(), {"amount": 0.7, "octaves": 1}, rng(2)).tobytes(),
                            stain.apply(pieza(), {"amount": 0.7, "octaves": 5}, rng(2)).tobytes())

    def test_umbral_endurece_el_contorno(self):
        suave = stain.apply(pieza(), {"amount": 0.9}, rng(5))
        duro = stain.apply(pieza(), {"amount": 0.9, "threshold": 0.6}, rng(5))
        self.assertLess(promedio(duro), promedio(suave))

    def test_edges_come_el_borde_y_deja_el_centro(self):
        salida = alfas(stain.apply(pieza(200, 200), {"amount": 1.0, "edges": 0.95}, rng(3)))
        borde = min(salida.getpixel((2, 100)), salida.getpixel((197, 100)))
        centro = salida.getpixel((100, 100))
        self.assertLess(borde, centro)

    def test_invert_come_el_centro_y_deja_el_borde(self):
        salida = alfas(stain.apply(
            pieza(200, 200), {"amount": 1.0, "edges": 0.95, "invert": True}, rng(3)))
        self.assertLess(salida.getpixel((100, 100)), salida.getpixel((2, 100)))

    def test_sin_edges_el_desgaste_no_privilegia_el_borde(self):
        salida = alfas(stain.apply(pieza(200, 200), {"amount": 0.6}, rng(3)))
        oscuro, claro = salida.getextrema()
        self.assertLess(oscuro, claro)


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            stain.apply(pieza(), {"cantidad": 0.5}, rng())

    def test_tipo_invalido(self):
        for malo in ("mucho", [0.5], True):
            with self.assertRaises(SpecError, msg=malo):
                stain.apply(pieza(), malo, rng())

    def test_valores_fuera_de_rango(self):
        for spec in ({"amount": 2}, {"amount": -1}, {"scale": 0}, {"scale": 9},
                     {"amount": 0.5, "threshold": 3}, {"amount": 0.5, "edges": -0.2},
                     {"amount": 0.5, "octaves": 0}, {"amount": 0.5, "octaves": 99},
                     {"amount": 0.5, "octaves": 2.5}):
            with self.assertRaises(SpecError, msg=spec):
                stain.apply(pieza(), spec, rng())


if __name__ == "__main__":
    unittest.main()