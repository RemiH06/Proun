"""Pruebas de proun.ops.tones."""

import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import tones


def lavada(w=64, h=64, base=110, rango=32):
    """Degradado de rango tonal estrecho, como una foto sin contraste."""
    gris = Image.linear_gradient("L").resize((w, h))
    return gris.point(lambda v: base + round(v * rango / 255)).convert("RGBA")


def contrastada(w=64, h=64):
    return Image.linear_gradient("L").resize((w, h)).convert("RGBA")


def extremos(im):
    return im.convert("L").getextrema()


class SinNormalizar(unittest.TestCase):
    def test_ausente_no_toca_la_capa(self):
        original = lavada()
        for vacio in (None, False):
            self.assertIs(tones.apply(original, vacio), original, vacio)

    def test_conserva_el_color_cuando_no_se_aplica(self):
        color = Image.new("RGBA", (8, 8), (200, 30, 30, 255))
        self.assertEqual(tones.apply(color, False).getpixel((0, 0))[:3], (200, 30, 30))


class Normalizacion(unittest.TestCase):
    def test_true_y_diccionario_vacio_son_lo_mismo(self):
        self.assertEqual(tones.apply(lavada(), True).tobytes(),
                         tones.apply(lavada(), {}).tobytes())

    def test_estira_el_rango_tonal(self):
        antes = extremos(lavada())
        despues = extremos(tones.apply(lavada(), True))
        self.assertGreater(antes[0], 100)
        self.assertLess(despues[0], 10)
        self.assertGreater(despues[1], 245)

    def test_es_el_punto_del_modulo(self):
        # Dos imágenes con rangos muy distintos terminan en el mismo rango.
        una = extremos(tones.apply(lavada(base=110, rango=32), True))
        otra = extremos(tones.apply(contrastada(), True))
        self.assertEqual(una, otra)

    def test_normalize_false_solo_pasa_a_grises(self):
        salida = tones.apply(lavada(), {"normalize": False})
        self.assertEqual(extremos(salida), extremos(lavada()))

    def test_pasa_a_grises_siempre(self):
        color = Image.new("RGBA", (8, 8), (200, 30, 30, 255))
        r, g, b = tones.apply(color, {"normalize": False}).getpixel((0, 0))[:3]
        self.assertEqual(r, g)
        self.assertEqual(g, b)

    def test_cutoff_recorta_extremos(self):
        suave = tones.apply(lavada(), {"cutoff": 0})
        agresivo = tones.apply(lavada(), {"cutoff": 20})
        self.assertNotEqual(suave.tobytes(), agresivo.tobytes())

    def test_conserva_el_alfa(self):
        con_alfa = lavada()
        con_alfa.putalpha(77)
        self.assertEqual(tones.apply(con_alfa, True).getchannel("A").getpixel((0, 0)), 77)

    def test_conserva_el_tamano(self):
        self.assertEqual(tones.apply(lavada(40, 90), True).size, (40, 90))

    def test_no_muta_el_original(self):
        original = lavada()
        antes = original.tobytes()
        tones.apply(original, True)
        self.assertEqual(original.tobytes(), antes)


class Ajustes(unittest.TestCase):
    def test_equalize_cambia_el_reparto(self):
        self.assertNotEqual(tones.apply(lavada(), {"equalize": True}).tobytes(),
                            tones.apply(lavada(), True).tobytes())

    def test_gamma_mayor_que_uno_aclara(self):
        base = tones.apply(contrastada(), True).convert("L")
        claro = tones.apply(contrastada(), {"gamma": 2.0}).convert("L")
        self.assertGreater(claro.getpixel((32, 32)), base.getpixel((32, 32)))

    def test_gamma_menor_que_uno_oscurece(self):
        base = tones.apply(contrastada(), True).convert("L")
        oscuro = tones.apply(contrastada(), {"gamma": 0.5}).convert("L")
        self.assertLess(oscuro.getpixel((32, 32)), base.getpixel((32, 32)))

    def test_invert_da_el_negativo(self):
        normal = tones.apply(contrastada(), True).convert("L")
        negativo = tones.apply(contrastada(), {"invert": True}).convert("L")
        self.assertAlmostEqual(normal.getpixel((32, 5)) + negativo.getpixel((32, 5)), 255, delta=2)

    def test_los_ajustes_se_combinan(self):
        salida = tones.apply(lavada(), {"cutoff": 2, "gamma": 1.3, "invert": True})
        self.assertEqual(salida.size, (64, 64))


class Dominante(unittest.TestCase):
    def con_fondo(self, fondo, sujeto, w=80, h=80):
        """Imagen tipo foto: casi todo fondo, un sujeto chico encima."""
        im = Image.new("RGBA", (w, h), (fondo, fondo, fondo, 255))
        im.paste((sujeto, sujeto, sujeto, 255), (10, 10, 30, 30))
        return im

    def test_lleva_el_fondo_claro_al_blanco(self):
        salida = tones.apply(self.con_fondo(190, 40), {"normalize": False, "dominant": "light"})
        self.assertEqual(salida.convert("L").getpixel((60, 60)), 255)
        self.assertLess(salida.convert("L").getpixel((20, 20)), 100)

    def test_lleva_el_fondo_oscuro_al_negro(self):
        salida = tones.apply(self.con_fondo(60, 220), {"normalize": False, "dominant": "dark"})
        self.assertEqual(salida.convert("L").getpixel((60, 60)), 0)

    def test_light_invierte_una_foto_oscura(self):
        # El fondo oscuro se vuelve blanco: la foto sale como negativo y el
        # sujeto queda de tinta, que es lo que la hace legible sobre papel.
        salida = tones.apply(self.con_fondo(50, 210), {"normalize": False, "dominant": "light"})
        self.assertEqual(salida.convert("L").getpixel((60, 60)), 255)
        self.assertLess(salida.convert("L").getpixel((20, 20)), 120)

    def test_auto_elige_el_extremo_mas_cercano(self):
        clara = tones.apply(self.con_fondo(200, 30), {"normalize": False, "dominant": "auto"})
        oscura = tones.apply(self.con_fondo(40, 220), {"normalize": False, "dominant": "auto"})
        self.assertEqual(clara.convert("L").getpixel((60, 60)), 255)
        self.assertEqual(oscura.convert("L").getpixel((60, 60)), 0)

    def test_no_toca_una_imagen_ya_blanca(self):
        blanca = Image.new("RGBA", (40, 40), (255, 255, 255, 255))
        blanca.paste((0, 0, 0, 255), (5, 5, 15, 15))
        salida = tones.apply(blanca, {"normalize": False, "dominant": "light"})
        self.assertEqual(salida.convert("L").getpixel((30, 30)), 255)

    def test_valor_invalido(self):
        with self.assertRaises(SpecError):
            tones.apply(lavada(), {"dominant": "medio"})


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            tones.apply(lavada(), {"normalizar": True})

    def test_tipo_invalido(self):
        for malo in ("mucho", 3, [1, 2]):
            with self.assertRaises(SpecError, msg=malo):
                tones.apply(lavada(), malo)

    def test_cutoff_fuera_de_rango(self):
        for malo in (-1, 50, 80, "poco", True):
            with self.assertRaises(SpecError, msg=malo):
                tones.apply(lavada(), {"cutoff": malo})

    def test_gamma_invalido(self):
        for malo in (0, -1, "alto", True):
            with self.assertRaises(SpecError, msg=malo):
                tones.apply(lavada(), {"gamma": malo})


if __name__ == "__main__":
    unittest.main()