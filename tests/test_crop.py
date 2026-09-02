"""Pruebas de proun.ops.crop."""

import random
import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import crop


def imagen(w=300, h=300):
    """Imagen con un degradado, para poder verificar qué zona quedó."""
    return Image.linear_gradient("L").resize((w, h)).convert("RGBA")


class SinRecorte(unittest.TestCase):
    def test_valores_vacios_devuelven_la_misma_imagen(self):
        original = imagen()
        for vacio in (None, False, {}, []):
            self.assertIs(crop.apply(original, vacio), original, vacio)


class Caja(unittest.TestCase):
    def test_pixeles(self):
        self.assertEqual(crop.apply(imagen(), [0, 0, 100, 50]).size, (100, 50))

    def test_fracciones(self):
        self.assertEqual(crop.apply(imagen(), {"box": [0.0, 0.0, 0.5, 0.5]}).size, (150, 150))

    def test_lista_suelta_equivale_a_box(self):
        self.assertEqual(
            crop.apply(imagen(), [10, 20, 100, 50]).size,
            crop.apply(imagen(), {"box": [10, 20, 100, 50]}).size,
        )

    def test_el_origen_se_respeta(self):
        # Degradado horizontal: oscuro a la izquierda, claro a la derecha.
        base = (Image.linear_gradient("L")
                .transpose(Image.Transpose.ROTATE_90)
                .resize((300, 300)).convert("RGBA"))
        izquierda = crop.apply(base, [0, 0, 50, 300]).getpixel((25, 150))[0]
        derecha = crop.apply(base, [250, 0, 50, 300]).getpixel((25, 150))[0]
        self.assertLess(izquierda, derecha)

    def test_se_recorta_al_borde_si_se_pasa(self):
        # Pedir 400 px de ancho sobre una imagen de 300 no falla, se limita.
        self.assertEqual(crop.apply(imagen(300, 300), [200, 0, 400, 100]).size, (100, 100))

    def test_fuera_de_la_imagen(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(100, 100), [500, 500, 50, 50])

    def test_longitud_equivocada(self):
        for malo in ([0, 0, 10], [0, 0, 10, 10, 10], "0,0,10,10"):
            with self.assertRaises(SpecError, msg=malo):
                crop.apply(imagen(), {"box": malo})

    def test_ancho_cero(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(), [0, 0, 0, 50])


class Proporcion(unittest.TestCase):
    def test_recorta_el_lado_sobrante(self):
        self.assertEqual(crop.apply(imagen(400, 400), {"aspect": "16:9"}).size, (400, 225))
        self.assertEqual(crop.apply(imagen(800, 200), {"aspect": 1.0}).size, (200, 200))

    def test_ancla_cambia_la_zona(self):
        base = Image.linear_gradient("L").resize((300, 300)).convert("RGBA")
        arriba = crop.apply(base, {"aspect": "3:1", "anchor": "top"}).getpixel((150, 25))[0]
        abajo = crop.apply(base, {"aspect": "3:1", "anchor": "bottom"}).getpixel((150, 25))[0]
        self.assertLess(arriba, abajo)

    def test_ancla_random_es_reproducible(self):
        a = crop.apply(imagen(), {"aspect": "16:9", "anchor": "random"}, random.Random(4))
        b = crop.apply(imagen(), {"aspect": "16:9", "anchor": "random"}, random.Random(4))
        self.assertEqual(a.tobytes(), b.tobytes())

    def test_random_sin_generador(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(), {"aspect": "16:9", "anchor": "random"})

    def test_proporcion_invalida(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(), {"aspect": "dieciséis a nueve"})


class Margenes(unittest.TestCase):
    def test_numero_suelto_va_a_los_cuatro_lados(self):
        self.assertEqual(crop.apply(imagen(200, 200), {"margin": 10}).size, (180, 180))

    def test_fraccion(self):
        self.assertEqual(crop.apply(imagen(200, 200), {"margin": 0.25}).size, (100, 100))

    def test_par_es_horizontal_y_vertical(self):
        self.assertEqual(crop.apply(imagen(200, 100), {"margin": [20, 10]}).size, (160, 80))

    def test_cuatro_valores(self):
        salida = crop.apply(imagen(200, 200), {"margin": [10, 20, 30, 40]})
        self.assertEqual(salida.size, (160, 140))

    def test_margen_que_no_deja_nada(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(100, 100), {"margin": 60})

    def test_longitud_invalida(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(), {"margin": [1, 2, 3]})


class AutoRotate(unittest.TestCase):
    def test_gira_si_retiene_mas_area(self):
        # Retrato angosto contra un slot ancho: girado retiene mucho más.
        alto = imagen(200, 600)
        sin = crop.apply(alto, {"aspect": "3:1"})
        con = crop.apply(alto, {"aspect": "3:1", "auto_rotate": True})
        self.assertGreater(con.size[0] * con.size[1], sin.size[0] * sin.size[1])

    def test_no_gira_si_ya_conviene_tal_cual(self):
        ancha = imagen(600, 200)
        normal = crop.apply(ancha, {"aspect": "3:1"})
        auto = crop.apply(ancha, {"aspect": "3:1", "auto_rotate": True})
        self.assertEqual(normal.tobytes(), auto.tobytes())

    def test_default_es_false(self):
        alto = imagen(200, 600)
        sin_declarar = crop.apply(alto, {"aspect": "3:1"})
        declarado_false = crop.apply(alto, {"aspect": "3:1", "auto_rotate": False})
        self.assertEqual(sin_declarar.tobytes(), declarado_false.tobytes())

    def test_sin_aspect_es_un_error(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(), {"box": [0, 0, 10, 10], "auto_rotate": True})

    def test_no_pierde_nitidez_es_transpose_no_rotate_libre(self):
        # Un giro de 90 exacto no debe interpolar: recortar y comparar
        # contra un giro manual con transpose debe dar bytes idénticos.
        from PIL import Image
        alto = imagen(200, 600)
        con = crop.apply(alto, {"aspect": "3:1", "auto_rotate": True})
        manual = crop.apply(alto.transpose(Image.Transpose.ROTATE_90), {"aspect": "3:1"})
        self.assertEqual(con.tobytes(), manual.tobytes())


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(), {"recorte": [0, 0, 10, 10]})

    def test_modos_son_excluyentes(self):
        with self.assertRaises(SpecError) as caso:
            crop.apply(imagen(), {"box": [0, 0, 10, 10], "aspect": "16:9"})
        self.assertIn("solo uno", str(caso.exception))

    def test_solo_ancla_no_alcanza(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(), {"anchor": "top"})

    def test_tipo_invalido(self):
        with self.assertRaises(SpecError):
            crop.apply(imagen(), "mitad")

    def test_no_muta_el_original(self):
        original = imagen()
        antes = original.size
        crop.apply(original, [0, 0, 50, 50])
        self.assertEqual(original.size, antes)


if __name__ == "__main__":
    unittest.main()