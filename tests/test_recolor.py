"""Pruebas de proun.ops.recolor."""

import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import recolor, tones

ROJO = "#ff0000"


def grises(w=64, h=64):
    """Lo que normalmente le llega: una capa ya normalizada por tones."""
    return tones.apply(Image.linear_gradient("L").resize((w, h)).convert("RGBA"), True)


def plana(valor=128, w=8, h=8):
    return Image.new("RGBA", (w, h), (valor, valor, valor, 255))


class SinRecolorear(unittest.TestCase):
    def test_modo_none(self):
        original = grises()
        self.assertIs(recolor.apply(original, ROJO, {"mode": "none"}), original)

    def test_fuerza_cero(self):
        original = grises()
        self.assertIs(recolor.apply(original, ROJO, {"strength": 0}), original)


class Duotono(unittest.TestCase):
    def test_es_el_modo_por_defecto(self):
        self.assertEqual(recolor.apply(grises(), ROJO).tobytes(),
                         recolor.apply(grises(), ROJO, {"mode": "duotone"}).tobytes())

    def test_tira_hacia_el_color(self):
        r, g, b = recolor.apply(grises(), ROJO).getpixel((32, 32))[:3]
        self.assertGreater(r, g)
        self.assertGreater(r, b)

    def test_conserva_el_orden_de_luces(self):
        salida = recolor.apply(grises(), ROJO).convert("L")
        self.assertLess(salida.getpixel((32, 5)), salida.getpixel((32, 58)))

    def test_sombra_y_luz_explicitas(self):
        salida = recolor.apply(grises(), ROJO, {"shadow": "#000080", "highlight": "#ffff00"})
        oscuro = salida.getpixel((32, 2))[:3]
        claro = salida.getpixel((32, 61))[:3]
        self.assertGreater(oscuro[2], oscuro[0])
        self.assertGreater(claro[0], claro[2])

    def test_levels_comprime_el_rango(self):
        self.assertNotEqual(recolor.apply(grises(), ROJO, {"levels": [60, 200]}).tobytes(),
                            recolor.apply(grises(), ROJO).tobytes())

    def test_midpoint_corre_los_medios(self):
        self.assertNotEqual(recolor.apply(grises(), ROJO, {"midpoint": 60}).tobytes(),
                            recolor.apply(grises(), ROJO, {"midpoint": 200}).tobytes())

    def test_levels_invalidos(self):
        for malo in ([200, 60], [-10, 100], [0, 300], [100], "0-255", ["a", "b"]):
            with self.assertRaises(SpecError, msg=malo):
                recolor.apply(grises(), ROJO, {"levels": malo})

    def test_midpoint_fuera_de_levels(self):
        with self.assertRaises(SpecError):
            recolor.apply(grises(), ROJO, {"levels": [50, 100], "midpoint": 200})


class OtrosModos(unittest.TestCase):
    def test_tint_multiplica(self):
        salida = recolor.apply(plana(200), ROJO, {"mode": "tint"})
        r, g, b = salida.getpixel((0, 0))[:3]
        self.assertEqual(r, 200)
        self.assertEqual((g, b), (0, 0))

    def test_screen_aclara(self):
        salida = recolor.apply(plana(100), ROJO, {"mode": "screen"})
        r, g, b = salida.getpixel((0, 0))[:3]
        self.assertEqual(r, 255)
        self.assertEqual((g, b), (100, 100))

    def test_hue_impone_el_matiz(self):
        color = Image.new("RGBA", (8, 8), (30, 30, 200, 255))
        r, g, b = recolor.apply(color, ROJO, {"mode": "hue"}).getpixel((0, 0))[:3]
        self.assertGreater(r, g)
        self.assertGreater(r, b)

    def test_channels_aplica_ganancia_y_desplazamiento(self):
        salida = recolor.apply(plana(100), "#ffffff",
                               {"mode": "channels", "channels": {"r": 2, "b": [1, -50]}})
        self.assertEqual(salida.getpixel((0, 0))[:3], (200, 100, 50))

    def test_channels_satura_sin_desbordar(self):
        salida = recolor.apply(plana(200), "#ffffff",
                               {"mode": "channels", "channels": {"r": 5, "g": [1, -300]}})
        r, g = salida.getpixel((0, 0))[:2]
        self.assertEqual(r, 255)
        self.assertEqual(g, 0)

    def test_channels_sin_configuracion(self):
        with self.assertRaises(SpecError):
            recolor.apply(grises(), ROJO, {"mode": "channels"})

    def test_channels_desconocido(self):
        with self.assertRaises(SpecError):
            recolor.apply(grises(), ROJO, {"mode": "channels", "channels": {"alpha": 2}})

    def test_channels_mal_formado(self):
        with self.assertRaises(SpecError):
            recolor.apply(grises(), ROJO, {"mode": "channels", "channels": {"r": [1, 2, 3]}})


class Fuerza(unittest.TestCase):
    def test_mezcla_contra_los_tonos_por_defecto(self):
        # Con mix_with = "tones", bajar la fuerza acerca al gris de entrada,
        # nunca al color original de la foto.
        medio = recolor.apply(plana(128), ROJO, {"strength": 0.5}).getpixel((0, 0))[:3]
        lleno = recolor.apply(plana(128), ROJO).getpixel((0, 0))[:3]
        self.assertLess(medio[0], lleno[0])
        self.assertGreater(medio[0], 128)

    def test_mezcla_contra_la_fuente_cuando_se_pide(self):
        original = Image.new("RGBA", (8, 8), (0, 0, 255, 255))
        salida = recolor.apply(plana(128), ROJO, {"strength": 0.5, "mix_with": "source"}, original)
        self.assertGreater(salida.getpixel((0, 0))[2], 100)

    def test_source_faltante(self):
        with self.assertRaises(SpecError) as caso:
            recolor.apply(plana(128), ROJO, {"strength": 0.5, "mix_with": "source"})
        self.assertIn("tones", str(caso.exception))

    def test_source_de_otro_tamano(self):
        with self.assertRaises(SpecError):
            recolor.apply(plana(128, 8, 8), ROJO,
                          {"strength": 0.5, "mix_with": "source"}, plana(128, 16, 16))

    def test_mix_with_invalido(self):
        with self.assertRaises(SpecError):
            recolor.apply(plana(128), ROJO, {"strength": 0.5, "mix_with": "original"})

    def test_source_solo_importa_con_fuerza_parcial(self):
        # A fuerza plena no hay mezcla, así que no debe exigir la fuente.
        self.assertIsNotNone(recolor.apply(plana(128), ROJO, {"mix_with": "source"}))

    def test_fuerza_fuera_de_rango(self):
        for malo in (-0.1, 1.5, "media", True):
            with self.assertRaises(SpecError, msg=malo):
                recolor.apply(grises(), ROJO, {"strength": malo})


class ColorPropio(unittest.TestCase):
    def test_la_capa_puede_ignorar_el_color_del_lote(self):
        del_lote = recolor.apply(grises(), "#00ff00")
        propio = recolor.apply(grises(), "#00ff00", {"color": ROJO})
        self.assertNotEqual(del_lote.tobytes(), propio.tobytes())
        r, g = propio.getpixel((32, 32))[:2]
        self.assertGreater(r, g)

    def test_acepta_cualquier_hexadecimal(self):
        for color in ("#3ba7ff", "3ba7ff", "#f08", [255, 0, 136]):
            self.assertIsNotNone(recolor.apply(grises(8, 8), color), color)

    def test_color_invalido(self):
        with self.assertRaises(SpecError):
            recolor.apply(grises(), "azulito")


class General(unittest.TestCase):
    def test_conserva_el_alfa(self):
        con_alfa = grises()
        con_alfa.putalpha(64)
        self.assertEqual(recolor.apply(con_alfa, ROJO).getchannel("A").getpixel((0, 0)), 64)

    def test_conserva_el_tamano(self):
        self.assertEqual(recolor.apply(grises(40, 90), ROJO).size, (40, 90))

    def test_no_muta_el_original(self):
        original = grises()
        antes = original.tobytes()
        recolor.apply(original, ROJO)
        self.assertEqual(original.tobytes(), antes)

    def test_saturacion(self):
        gris = recolor.apply(grises(), ROJO, {"saturation": 0.0}).getpixel((32, 32))
        self.assertAlmostEqual(gris[0], gris[1], delta=2)

    def test_saturacion_invalida(self):
        for malo in (-1, 11, "mucha", True):
            with self.assertRaises(SpecError, msg=malo):
                recolor.apply(grises(), ROJO, {"saturation": malo})

    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            recolor.apply(grises(), ROJO, {"normalize": True})

    def test_modo_invalido(self):
        with self.assertRaises(SpecError):
            recolor.apply(grises(), ROJO, {"mode": "arcoiris"})

    def test_grayscale_ya_no_existe(self):
        # Ese trabajo se fue a ops/tones.
        with self.assertRaises(SpecError):
            recolor.apply(grises(), ROJO, {"mode": "grayscale"})


if __name__ == "__main__":
    unittest.main()