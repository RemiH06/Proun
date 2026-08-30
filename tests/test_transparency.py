"""Pruebas de proun.ops.transparency."""

import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import transparency


def franjas(w=90, h=30):
    """Tres bloques: blanco, gris medio y negro."""
    im = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    im.paste((128, 128, 128, 255), (30, 0, 60, h))
    im.paste((0, 0, 0, 255), (60, 0, 90, h))
    return im


def alfa(im, x):
    return im.getchannel("A").getpixel((x, 15))


class SinTransparencia(unittest.TestCase):
    def test_vacio_no_toca_la_capa(self):
        original = franjas()
        for vacio in (None, False):
            self.assertIs(transparency.apply(original, vacio), original, vacio)


class Polaridad(unittest.TestCase):
    def test_el_claro_desaparece(self):
        salida = transparency.apply(franjas(), {"color": "light", "tolerance": 0, "softness": 1})
        self.assertEqual(alfa(salida, 15), 0)
        self.assertEqual(alfa(salida, 75), 255)

    def test_el_oscuro_desaparece(self):
        salida = transparency.apply(franjas(), {"color": "dark", "tolerance": 0, "softness": 1})
        self.assertEqual(alfa(salida, 75), 0)
        self.assertEqual(alfa(salida, 15), 255)

    def test_los_medios_quedan_a_medias(self):
        salida = transparency.apply(franjas(), {"color": "light", "tolerance": 0, "softness": 1})
        self.assertGreater(alfa(salida, 45), 50)
        self.assertLess(alfa(salida, 45), 205)

    def test_alias_equivalen_al_hexadecimal(self):
        for alias, hexa in (("light", "#ffffff"), ("dark", "#000000"),
                            ("white", "#ffffff"), ("black", "#000000")):
            self.assertEqual(transparency.apply(franjas(), alias).tobytes(),
                             transparency.apply(franjas(), hexa).tobytes(), alias)

    def test_color_suelto_equivale_a_la_clave(self):
        self.assertEqual(transparency.apply(franjas(), "#ffffff").tobytes(),
                         transparency.apply(franjas(), {"color": "#ffffff"}).tobytes())


class Corte(unittest.TestCase):
    def test_suavidad_cero_es_corte_duro(self):
        salida = transparency.apply(
            franjas(), {"color": "light", "tolerance": 0.7, "softness": 0})
        self.assertEqual({alfa(salida, x) for x in (15, 45, 75)}, {0, 255})

    def test_tolerancia_alta_se_lleva_los_medios(self):
        salida = transparency.apply(
            franjas(), {"color": "light", "tolerance": 0.6, "softness": 0.05})
        self.assertEqual(alfa(salida, 45), 0)
        self.assertEqual(alfa(salida, 75), 255)

    def test_tolerancia_baja_los_conserva(self):
        salida = transparency.apply(
            franjas(), {"color": "light", "tolerance": 0.05, "softness": 0.05})
        self.assertEqual(alfa(salida, 45), 255)

    def test_croma_de_un_color_cualquiera(self):
        verde = Image.new("RGBA", (20, 20), (0, 255, 0, 255))
        verde.paste((200, 30, 30, 255), (0, 0, 10, 20))
        salida = transparency.apply(verde, {"color": "#00ff00", "tolerance": 0.3, "softness": 0.1})
        self.assertEqual(salida.getchannel("A").getpixel((15, 10)), 0)
        self.assertEqual(salida.getchannel("A").getpixel((5, 10)), 255)


class Inversion(unittest.TestCase):
    def test_conserva_solo_lo_parecido(self):
        salida = transparency.apply(
            franjas(), {"color": "light", "tolerance": 0, "softness": 1, "invert": True})
        self.assertEqual(alfa(salida, 15), 255)
        self.assertEqual(alfa(salida, 75), 0)


class General(unittest.TestCase):
    def test_respeta_el_alfa_previo(self):
        parcial = franjas()
        parcial.putalpha(100)
        salida = transparency.apply(parcial, {"color": "light", "tolerance": 0, "softness": 1})
        self.assertLessEqual(salida.getchannel("A").getextrema()[1], 100)

    def test_no_toca_el_color(self):
        salida = transparency.apply(franjas(), "light")
        self.assertEqual(salida.getpixel((75, 15))[:3], (0, 0, 0))

    def test_conserva_el_tamano(self):
        self.assertEqual(transparency.apply(franjas(40, 90), "light").size, (40, 90))

    def test_no_muta_el_original(self):
        original = franjas()
        antes = original.tobytes()
        transparency.apply(original, "light")
        self.assertEqual(original.tobytes(), antes)


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            transparency.apply(franjas(), {"color": "light", "umbral": 0.5})

    def test_sin_color(self):
        with self.assertRaises(SpecError):
            transparency.apply(franjas(), {"tolerance": 0.5})

    def test_color_invalido(self):
        with self.assertRaises(SpecError):
            transparency.apply(franjas(), "clarito")

    def test_tipo_invalido(self):
        for malo in (0.5, True):
            with self.assertRaises(SpecError, msg=malo):
                transparency.apply(franjas(), malo)

    def test_valores_fuera_de_rango(self):
        for spec in ({"color": "light", "tolerance": 2},
                     {"color": "light", "tolerance": -1},
                     {"color": "light", "softness": 5},
                     {"color": "light", "softness": "media"}):
            with self.assertRaises(SpecError, msg=spec):
                transparency.apply(franjas(), spec)


if __name__ == "__main__":
    unittest.main()