"""Pruebas de proun.ops.rotate."""

import random
import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import rotate


def asimetrica(w=40, h=20):
    """Rectángulo con una esquina marcada: sirve para saber cómo quedó."""
    im = Image.new("RGBA", (w, h), (30, 30, 30, 255))
    im.paste((240, 240, 240, 255), (0, 0, w // 4, h // 4))
    return im


class Decision(unittest.TestCase):
    def test_vacio_no_gira(self):
        for vacio in (None, False):
            self.assertEqual(rotate.decide(vacio, random.Random()), (0.0, "none"))

    def test_angulo_fijo(self):
        self.assertEqual(rotate.decide(90, random.Random())[0], 90.0)
        self.assertEqual(rotate.decide(-45, random.Random())[0], -45.0)

    def test_random_solo_da_multiplos_de_90(self):
        rng = random.Random(1)
        sorteados = {rotate.decide("random", rng)[0] for _ in range(60)}
        self.assertTrue(sorteados <= {float(a) for a in rotate.QUARTERS})
        self.assertGreater(len(sorteados), 1)

    def test_alias_de_random(self):
        for alias in ("random", "quarter", "quarters", "random90", "90", "RANDOM"):
            angulo = rotate.decide(alias, random.Random(2))[0]
            self.assertIn(angulo, [float(a) for a in rotate.QUARTERS], alias)

    def test_none_como_texto(self):
        self.assertEqual(rotate.decide("none", random.Random())[0], 0.0)

    def test_lista_elige_de_ahi(self):
        rng = random.Random(3)
        sorteados = {rotate.decide([0, 180], rng)[0] for _ in range(40)}
        self.assertEqual(sorteados, {0.0, 180.0})

    def test_rango_libre(self):
        angulo = rotate.decide({"range": [-10, 10]}, random.Random(4))[0]
        self.assertTrue(-10 <= angulo <= 10)

    def test_rango_con_paso(self):
        rng = random.Random(5)
        posibles = {-6.0, -3.0, 0.0, 3.0, 6.0}
        sorteados = {rotate.decide({"range": [-6, 6], "step": 3}, rng)[0] for _ in range(40)}
        self.assertTrue(sorteados <= posibles)

    def test_rango_invertido_se_ordena(self):
        angulo = rotate.decide({"range": [10, -10]}, random.Random(6))[0]
        self.assertTrue(-10 <= angulo <= 10)

    def test_flip_explicito_y_aleatorio(self):
        self.assertEqual(rotate.decide({"flip": "horizontal"}, random.Random())[1], "horizontal")
        rng = random.Random(7)
        sorteados = {rotate.decide({"flip": "random"}, rng)[1] for _ in range(60)}
        self.assertTrue(sorteados <= {"none", "horizontal", "vertical", "both"})

    def test_misma_semilla_mismo_resultado(self):
        spec = {"angles": "random", "flip": "random"}
        self.assertEqual(rotate.decide(spec, random.Random(9)),
                         rotate.decide(spec, random.Random(9)))

    def test_semillas_distintas_divergen(self):
        spec = {"angles": [0, 90, 180, 270]}
        salidas = {rotate.decide(spec, random.Random(s))[0] for s in range(20)}
        self.assertGreater(len(salidas), 1)


class Aplicacion(unittest.TestCase):
    def test_cuarto_de_vuelta_intercambia_lados(self):
        self.assertEqual(rotate.apply(asimetrica(40, 20), 90).size, (20, 40))
        self.assertEqual(rotate.apply(asimetrica(40, 20), 270).size, (20, 40))
        self.assertEqual(rotate.apply(asimetrica(40, 20), 180).size, (40, 20))

    def test_multiplos_de_90_no_pierden_un_pixel(self):
        original = asimetrica(40, 20)
        ida = rotate.apply(original, 90)
        self.assertEqual(rotate.apply(ida, 270).tobytes(), original.tobytes())

    def test_cuatro_cuartos_vuelven_al_inicio(self):
        original = asimetrica()
        girada = original
        for _ in range(4):
            girada = rotate.apply(girada, 90)
        self.assertEqual(girada.tobytes(), original.tobytes())

    def test_360_y_equivalentes(self):
        original = asimetrica()
        self.assertIs(rotate.apply(original, 0), original)
        self.assertIs(rotate.apply(original, 360), original)
        self.assertEqual(rotate.apply(original, 450).size, rotate.apply(original, 90).size)

    def test_negativos_equivalen_a_su_complemento(self):
        self.assertEqual(rotate.apply(asimetrica(), -90).tobytes(),
                         rotate.apply(asimetrica(), 270).tobytes())

    def test_angulo_libre_expande_el_lienzo(self):
        girada = rotate.apply(asimetrica(40, 20), 45)
        self.assertGreater(girada.width, 40)
        self.assertGreater(girada.height, 20)

    def test_angulo_libre_deja_esquinas_transparentes(self):
        girada = rotate.apply(asimetrica(40, 40), 45)
        self.assertEqual(girada.getpixel((0, 0))[3], 0)

    def test_espejos(self):
        original = asimetrica(40, 20)
        # La marca está arriba a la izquierda; cada espejo la manda a otra esquina.
        self.assertEqual(rotate.apply(original, 0, "horizontal").getpixel((38, 2))[:3],
                         (240, 240, 240))
        self.assertEqual(rotate.apply(original, 0, "vertical").getpixel((2, 18))[:3],
                         (240, 240, 240))
        self.assertEqual(rotate.apply(original, 0, "both").getpixel((38, 18))[:3],
                         (240, 240, 240))

    def test_espejo_y_giro_se_combinan(self):
        salida = rotate.apply(asimetrica(40, 20), 90, "horizontal")
        self.assertEqual(salida.size, (20, 40))

    def test_no_muta_el_original(self):
        original = asimetrica()
        antes = original.tobytes()
        rotate.apply(original, 90, "both")
        self.assertEqual(original.tobytes(), antes)


class Validacion(unittest.TestCase):
    def test_texto_desconocido(self):
        with self.assertRaises(SpecError):
            rotate.decide("diagonal", random.Random())

    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            rotate.decide({"grados": 90}, random.Random())

    def test_angles_y_range_excluyentes(self):
        with self.assertRaises(SpecError):
            rotate.decide({"angles": 90, "range": [-5, 5]}, random.Random())

    def test_step_sin_range(self):
        with self.assertRaises(SpecError):
            rotate.decide({"angles": 90, "step": 3}, random.Random())

    def test_lista_vacia(self):
        with self.assertRaises(SpecError):
            rotate.decide([], random.Random())

    def test_lista_con_basura(self):
        with self.assertRaises(SpecError):
            rotate.decide(["noventa", 90], random.Random(0))

    def test_rango_mal_formado(self):
        for malo in ([0], [0, 1, 2], "0-90"):
            with self.assertRaises(SpecError, msg=malo):
                rotate.decide({"range": malo}, random.Random())

    def test_paso_invalido(self):
        with self.assertRaises(SpecError):
            rotate.decide({"range": [-6, 6], "step": -3}, random.Random())

    def test_flip_invalido(self):
        with self.assertRaises(SpecError):
            rotate.decide({"flip": "espejito"}, random.Random())

    def test_tipo_invalido(self):
        with self.assertRaises(SpecError):
            rotate.decide({"angles": {"a": 1}}, random.Random())


if __name__ == "__main__":
    unittest.main()