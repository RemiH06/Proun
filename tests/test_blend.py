"""Pruebas de proun.ops.blend."""

import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import blend


def lienzo(valor=0, w=100, h=100):
    return Image.new("RGBA", (w, h), (valor, valor, valor, 255))


def capa(color=(255, 255, 255), w=50, h=50, alfa=255):
    return Image.new("RGBA", (w, h), (*color, alfa))


class Pegado(unittest.TestCase):
    def test_devuelve_el_mismo_lienzo(self):
        base = lienzo()
        self.assertIs(blend.composite(base, capa(), (0, 0)), base)

    def test_pega_donde_se_le_dice(self):
        base = lienzo()
        blend.composite(base, capa((255, 0, 0)), (10, 20))
        self.assertEqual(base.getpixel((15, 25))[:3], (255, 0, 0))
        self.assertEqual(base.getpixel((5, 25))[:3], (0, 0, 0))

    def test_posicion_negativa_recorta(self):
        base = lienzo()
        blend.composite(base, capa((255, 255, 255)), (-30, -30))
        self.assertEqual(base.getpixel((5, 5))[:3], (255, 255, 255))
        self.assertEqual(base.getpixel((25, 25))[:3], (0, 0, 0))

    def test_desbordar_por_la_derecha(self):
        base = lienzo()
        blend.composite(base, capa((255, 255, 255)), (80, 80))
        self.assertEqual(base.getpixel((95, 95))[:3], (255, 255, 255))

    def test_completamente_fuera_no_hace_nada(self):
        base = lienzo()
        antes = base.tobytes()
        blend.composite(base, capa(), (500, 500))
        blend.composite(base, capa(), (-500, -500))
        self.assertEqual(base.tobytes(), antes)

    def test_posicion_flotante_se_redondea(self):
        base = lienzo()
        blend.composite(base, capa((255, 0, 0), 10, 10), (9.6, 9.6))
        self.assertEqual(base.getpixel((15, 15))[:3], (255, 0, 0))
        self.assertEqual(base.getpixel((9, 9))[:3], (0, 0, 0))

    def test_no_muta_la_capa(self):
        pieza = capa((255, 0, 0))
        antes = pieza.tobytes()
        blend.composite(lienzo(), pieza, (0, 0), opacity=0.5)
        self.assertEqual(pieza.tobytes(), antes)


class Opacidad(unittest.TestCase):
    def test_media(self):
        base = lienzo(0)
        blend.composite(base, capa((255, 255, 255)), (0, 0), opacity=0.5)
        self.assertAlmostEqual(base.getpixel((10, 10))[0], 128, delta=2)

    def test_cero_no_toca_nada(self):
        base = lienzo()
        antes = base.tobytes()
        blend.composite(base, capa((255, 255, 255)), (0, 0), opacity=0)
        self.assertEqual(base.tobytes(), antes)

    def test_respeta_el_alfa_que_ya_traia_la_capa(self):
        base = lienzo(0)
        blend.composite(base, capa((255, 255, 255), alfa=128), (0, 0), opacity=0.5)
        self.assertAlmostEqual(base.getpixel((10, 10))[0], 64, delta=3)

    def test_invalida(self):
        for malo in (-0.1, 1.5, "media", True, None):
            with self.assertRaises(SpecError, msg=malo):
                blend.composite(lienzo(), capa(), (0, 0), opacity=malo)


class Modos(unittest.TestCase):
    def test_multiply_oscurece(self):
        base = lienzo(200)
        blend.composite(base, capa((128, 128, 128)), (0, 0), mode="multiply")
        self.assertAlmostEqual(base.getpixel((10, 10))[0], 100, delta=2)

    def test_screen_aclara(self):
        base = lienzo(100)
        blend.composite(base, capa((128, 128, 128)), (0, 0), mode="screen")
        self.assertGreater(base.getpixel((10, 10))[0], 100)

    def test_difference(self):
        base = lienzo(200)
        blend.composite(base, capa((50, 50, 50)), (0, 0), mode="difference")
        self.assertAlmostEqual(base.getpixel((10, 10))[0], 150, delta=2)

    def test_darker_y_lighter(self):
        oscuro = lienzo(200)
        blend.composite(oscuro, capa((50, 50, 50)), (0, 0), mode="darker")
        self.assertEqual(oscuro.getpixel((10, 10))[0], 50)
        claro = lienzo(200)
        blend.composite(claro, capa((50, 50, 50)), (0, 0), mode="lighter")
        self.assertEqual(claro.getpixel((10, 10))[0], 200)

    def test_todos_los_modos_corren(self):
        for modo in blend.MODES:
            base = lienzo(120)
            blend.composite(base, capa((90, 160, 200)), (10, 10), mode=modo)
            self.assertEqual(base.size, (100, 100), modo)

    def test_los_modos_no_pintan_fuera_de_la_capa(self):
        # Con multiply, lo que está fuera del área pegada no cambia.
        base = lienzo(200)
        blend.composite(base, capa((0, 0, 0), 20, 20), (0, 0), mode="multiply")
        self.assertEqual(base.getpixel((50, 50))[0], 200)

    def test_los_modos_respetan_el_alfa(self):
        base = lienzo(200)
        blend.composite(base, capa((0, 0, 0), alfa=0), (0, 0), mode="multiply")
        self.assertEqual(base.getpixel((10, 10))[0], 200)

    def test_modo_con_recorte_por_borde(self):
        base = lienzo(200)
        blend.composite(base, capa((0, 0, 0)), (-25, -25), mode="multiply")
        self.assertEqual(base.getpixel((5, 5))[0], 0)
        self.assertEqual(base.getpixel((50, 50))[0], 200)

    def test_mayusculas(self):
        base = lienzo(200)
        blend.composite(base, capa((128, 128, 128)), (0, 0), mode="MULTIPLY")
        self.assertAlmostEqual(base.getpixel((10, 10))[0], 100, delta=2)

    def test_modo_invalido(self):
        with self.assertRaises(SpecError):
            blend.composite(lienzo(), capa(), (0, 0), mode="disolver")


class Posicion(unittest.TestCase):
    def test_mal_formada(self):
        for malo in ((0,), (0, 0, 0), "0,0", 0, None, (0, "x"), (True, 0)):
            with self.assertRaises(SpecError, msg=malo):
                blend.composite(lienzo(), capa(), malo)


if __name__ == "__main__":
    unittest.main()