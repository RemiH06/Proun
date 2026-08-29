"""Pruebas de proun.ops.finish."""

import random
import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import finish

AZUL = (59, 167, 255)


def lienzo(valor=120, w=120, h=80):
    return Image.new("RGBA", (w, h), (valor, valor, valor, 255))


def rng(semilla=7):
    return random.Random(semilla)


class SinAcabado(unittest.TestCase):
    def test_vacio_no_toca_nada(self):
        base = lienzo()
        for vacio in (None, {}, False):
            self.assertIs(finish.apply(base, AZUL, vacio), base, vacio)

    def test_no_muta_la_imagen_que_recibe(self):
        base = lienzo()
        antes = base.tobytes()
        finish.apply(base, AZUL, {"overlay": {"color": "#ff0000", "opacity": 0.5}})
        finish.apply(base, AZUL, {"grain": 0.4}, rng())
        self.assertEqual(base.tobytes(), antes)


class Ajustes(unittest.TestCase):
    def test_brillo(self):
        claro = finish.apply(lienzo(), AZUL, {"brightness": 1.5}).getpixel((10, 10))[0]
        oscuro = finish.apply(lienzo(), AZUL, {"brightness": 0.5}).getpixel((10, 10))[0]
        self.assertGreater(claro, 120)
        self.assertLess(oscuro, 120)

    def test_contraste_sobre_un_degradado(self):
        base = Image.linear_gradient("L").convert("RGBA")
        subido = finish.apply(base, AZUL, {"contrast": 2.0})
        self.assertLess(subido.getpixel((128, 20))[0], base.getpixel((128, 20))[0])

    def test_saturacion_cero_deja_gris(self):
        color = Image.new("RGBA", (10, 10), (200, 40, 40, 255))
        r, g, b = finish.apply(color, AZUL, {"saturation": 0}).getpixel((5, 5))[:3]
        self.assertEqual(r, g)
        self.assertEqual(g, b)

    def test_blur_suaviza(self):
        base = Image.new("RGBA", (40, 40), (0, 0, 0, 255))
        base.paste((255, 255, 255, 255), (0, 0, 20, 40))
        borroso = finish.apply(base, AZUL, {"blur": 4})
        self.assertNotIn(borroso.getpixel((20, 20))[0], (0, 255))

    def test_conserva_el_tamano(self):
        salida = finish.apply(lienzo(120, 200, 90), AZUL,
                              {"blur": 2, "contrast": 1.2, "vignette": 0.3}, rng())
        self.assertEqual(salida.size, (200, 90))


class Vineta(unittest.TestCase):
    def test_oscurece_las_esquinas(self):
        salida = finish.apply(lienzo(), AZUL, {"vignette": 0.6})
        self.assertLess(salida.getpixel((2, 2))[0], salida.getpixel((60, 40))[0])

    def test_mas_fuerza_oscurece_mas(self):
        suave = finish.apply(lienzo(), AZUL, {"vignette": 0.2}).getpixel((2, 2))[0]
        fuerte = finish.apply(lienzo(), AZUL, {"vignette": 0.9}).getpixel((2, 2))[0]
        self.assertLess(fuerte, suave)


class Velo(unittest.TestCase):
    def test_overlay_cambia_la_imagen(self):
        base = lienzo()
        salida = finish.apply(base, AZUL, {"overlay": {"color": "#ff0000", "opacity": 0.5}})
        self.assertNotEqual(salida.getpixel((10, 10)), base.getpixel((10, 10)))

    def test_overlay_auto_usa_el_color_principal(self):
        salida = finish.apply(lienzo(), AZUL, {"overlay": {"opacity": 0.6, "mode": "multiply"}})
        r, g, b = salida.getpixel((10, 10))[:3]
        self.assertGreater(b, r)

    def test_overlay_mal_formado(self):
        with self.assertRaises(SpecError):
            finish.apply(lienzo(), AZUL, {"overlay": "rojo"})

    def test_overlay_opacidad_invalida(self):
        with self.assertRaises(SpecError):
            finish.apply(lienzo(), AZUL, {"overlay": {"opacity": 3}})


class Grano(unittest.TestCase):
    def test_es_reproducible(self):
        # El punto de todo el proyecto: la misma semilla, el mismo archivo.
        a = finish.apply(lienzo(), AZUL, {"grain": 0.3}, rng(7))
        b = finish.apply(lienzo(), AZUL, {"grain": 0.3}, rng(7))
        self.assertEqual(a.tobytes(), b.tobytes())

    def test_semillas_distintas_dan_granos_distintos(self):
        a = finish.apply(lienzo(), AZUL, {"grain": 0.3}, rng(7))
        b = finish.apply(lienzo(), AZUL, {"grain": 0.3}, rng(8))
        self.assertNotEqual(a.tobytes(), b.tobytes())

    def test_agrega_variacion(self):
        plano = lienzo()
        granoso = finish.apply(plano, AZUL, {"grain": 0.4}, rng())
        self.assertGreater(granoso.convert("L").getextrema()[1] - granoso.convert("L").getextrema()[0], 10)

    def test_no_tapa_la_imagen(self):
        # Con grano fuerte la media sigue cerca del valor original.
        granoso = finish.apply(lienzo(120), AZUL, {"grain": 0.5}, rng()).convert("L")
        oscuro, claro = granoso.getextrema()
        self.assertLess(oscuro, 120)
        self.assertGreater(claro, 120)
        self.assertAlmostEqual((oscuro + claro) / 2, 120, delta=35)

    def test_exige_generador(self):
        with self.assertRaises(SpecError) as caso:
            finish.apply(lienzo(), AZUL, {"grain": 0.2})
        self.assertIn("semilla", str(caso.exception))

    def test_sin_grano_no_exige_generador(self):
        self.assertIsNotNone(finish.apply(lienzo(), AZUL, {"vignette": 0.3}))


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            finish.apply(lienzo(), AZUL, {"vineta": 0.3})

    def test_tipo_invalido(self):
        with self.assertRaises(SpecError):
            finish.apply(lienzo(), AZUL, "mucho")

    def test_valores_fuera_de_rango(self):
        for spec in ({"vignette": 2}, {"grain": -1}, {"blur": 500},
                     {"contrast": 20}, {"brightness": "alto"}, {"saturation": True}):
            with self.assertRaises(SpecError, msg=spec):
                finish.apply(lienzo(), AZUL, spec, rng())


if __name__ == "__main__":
    unittest.main()