"""Pruebas de proun.ops.background."""

import random
import unittest

from proun.errors import SpecError
from proun.ops import background

AZUL = (59, 167, 255)
TAM = (200, 100)


class Solido(unittest.TestCase):
    def test_color_explicito(self):
        fondo = background.build(TAM, AZUL, "#101018")
        self.assertEqual(fondo.getpixel((100, 50)), (16, 16, 24, 255))

    def test_lista_rgb(self):
        self.assertEqual(background.build(TAM, AZUL, [16, 16, 24]).getpixel((0, 0))[:3],
                         (16, 16, 24))

    def test_objeto_solid(self):
        self.assertEqual(background.build(TAM, AZUL, {"solid": "#ffffff"}).getpixel((0, 0)),
                         (255, 255, 255, 255))

    def test_solid_auto_deriva_del_color_principal(self):
        fondo = background.build(TAM, AZUL, {"solid": "auto"}).getpixel((0, 0))
        # Una sombra del azul: azul por encima de rojo, y oscuro.
        self.assertGreater(fondo[2], fondo[0])
        self.assertLess(fondo[2], AZUL[2])

    def test_es_opaco(self):
        self.assertEqual(background.build(TAM, AZUL, "#000000").getpixel((0, 0))[3], 255)


class Transparente(unittest.TestCase):
    def test_null_deja_el_lienzo_vacio(self):
        fondo = background.build(TAM, AZUL, None)
        self.assertEqual(fondo.getpixel((100, 50)), (0, 0, 0, 0))


class Degradados(unittest.TestCase):
    def test_auto_es_un_degradado(self):
        fondo = background.build(TAM, AZUL, "auto")
        self.assertNotEqual(fondo.getpixel((100, 2)), fondo.getpixel((100, 98)))

    def test_vertical_cambia_de_arriba_a_abajo(self):
        fondo = background.build(TAM, AZUL, {"gradient": ["#ffffff", "#000000"]})
        self.assertGreater(fondo.getpixel((100, 2))[0], fondo.getpixel((100, 98))[0])
        self.assertEqual(fondo.getpixel((5, 50))[0], fondo.getpixel((195, 50))[0])

    def test_horizontal_cambia_de_izquierda_a_derecha(self):
        fondo = background.build(TAM, AZUL,
                                 {"gradient": ["#ffffff", "#000000"], "direction": "horizontal"})
        self.assertGreater(fondo.getpixel((2, 50))[0], fondo.getpixel((198, 50))[0])

    def test_radial_va_del_centro_al_borde(self):
        fondo = background.build(TAM, AZUL,
                                 {"gradient": ["#ffffff", "#000000"], "direction": "radial"})
        self.assertGreater(fondo.getpixel((100, 50))[0], fondo.getpixel((2, 2))[0])

    def test_diagonal_no_deja_esquinas_negras(self):
        # El giro de 45 grados dejaba las esquinas fuera del rombo y salían en negro.
        fondo = background.build(TAM, AZUL, {"gradient": ["#ffffff", "#888888"],
                                             "direction": "diagonal"})
        for esquina in ((2, 2), (197, 2), (2, 97), (197, 97)):
            self.assertGreater(fondo.getpixel(esquina)[0], 100, esquina)

    def test_diagonal_va_de_una_esquina_a_la_otra(self):
        fondo = background.build(TAM, AZUL, {"gradient": ["#ffffff", "#000000"],
                                             "direction": "diagonal"})
        self.assertGreater(fondo.getpixel((2, 2))[0], fondo.getpixel((197, 97))[0])

    def test_auto_dark_y_auto_light(self):
        fondo = background.build(TAM, AZUL, {"gradient": ["auto_light", "auto_dark"]})
        self.assertGreater(fondo.getpixel((100, 2))[0], fondo.getpixel((100, 98))[0])

    def test_tamanos_raros(self):
        for tam in ((1, 1), (1000, 3), (3, 1000)):
            fondo = background.build(tam, AZUL, {"gradient": ["#fff", "#000"],
                                                 "direction": "diagonal"})
            self.assertEqual(fondo.size, tam, tam)


class Manchado(unittest.TestCase):
    def test_rompe_la_uniformidad_del_solido(self):
        limpio = background.build(TAM, AZUL, {"solid": "#f2efe8"})
        sucio = background.build(TAM, AZUL,
                                 {"solid": "#f2efe8", "stain": {"amount": 0.4}},
                                 random.Random(3))
        self.assertEqual(len(set(limpio.convert("L").getextrema())), 1)
        oscuro, claro = sucio.convert("L").getextrema()
        self.assertGreater(claro - oscuro, 5)

    def test_es_reproducible(self):
        spec = {"solid": "#f2efe8", "stain": {"amount": 0.4}}
        self.assertEqual(background.build(TAM, AZUL, spec, random.Random(3)).tobytes(),
                         background.build(TAM, AZUL, spec, random.Random(3)).tobytes())

    def test_tambien_mancha_degradados(self):
        sucio = background.build(TAM, AZUL,
                                 {"gradient": ["#ffffff", "#eeeeee"],
                                  "stain": {"amount": 0.5, "color": "#333333"}},
                                 random.Random(4))
        self.assertLess(sucio.convert("L").getextrema()[0], 200)

    def test_amount_cero_no_hace_nada(self):
        spec = {"solid": "#f2efe8", "stain": {"amount": 0}}
        self.assertEqual(background.build(TAM, AZUL, spec).tobytes(),
                         background.build(TAM, AZUL, {"solid": "#f2efe8"}).tobytes())

    def test_exige_generador(self):
        with self.assertRaises(SpecError):
            background.build(TAM, AZUL, {"solid": "#fff", "stain": {"amount": 0.3}})

    def test_validacion(self):
        for malo in ({"amount": 2}, {"cantidad": 0.3}, "mucho"):
            with self.assertRaises(SpecError, msg=malo):
                background.build(TAM, AZUL, {"solid": "#fff", "stain": malo}, random.Random(1))


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            background.build(TAM, AZUL, {"fondo": "#fff"})

    def test_solid_y_gradient_excluyentes(self):
        with self.assertRaises(SpecError):
            background.build(TAM, AZUL, {"solid": "#fff", "gradient": ["#000", "#fff"]})

    def test_sin_solid_ni_gradient(self):
        with self.assertRaises(SpecError):
            background.build(TAM, AZUL, {"direction": "radial"})

    def test_direction_con_solid(self):
        with self.assertRaises(SpecError):
            background.build(TAM, AZUL, {"solid": "#fff", "direction": "radial"})

    def test_gradient_mal_formado(self):
        for malo in (["#fff"], ["#fff", "#000", "#888"], "#fff", 3):
            with self.assertRaises(SpecError, msg=malo):
                background.build(TAM, AZUL, {"gradient": malo})

    def test_direction_invalida(self):
        with self.assertRaises(SpecError):
            background.build(TAM, AZUL, {"gradient": ["#fff", "#000"], "direction": "espiral"})

    def test_color_invalido(self):
        with self.assertRaises(SpecError):
            background.build(TAM, AZUL, "azulito")

    def test_tipo_invalido(self):
        with self.assertRaises(SpecError):
            background.build(TAM, AZUL, 42)


if __name__ == "__main__":
    unittest.main()