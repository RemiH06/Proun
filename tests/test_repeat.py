"""Pruebas de proun.ops.repeat."""

import unittest

from PIL import Image

from proun.errors import SpecError
from proun.ops import repeat


def marca(w=100, h=60):
    """Pieza asimétrica: la esquina clara delata espejados y giros."""
    im = Image.new("RGBA", (w, h), (40, 40, 40, 255))
    im.paste((240, 240, 240, 255), (0, 0, w // 4, h // 4))
    return im


class SinRepetir(unittest.TestCase):
    def test_vacio_no_toca_la_capa(self):
        original = marca()
        for vacio in (None, False):
            self.assertIs(repeat.apply(original, vacio), original, vacio)

    def test_cero_copias_devuelve_el_mismo_tamano(self):
        self.assertEqual(repeat.apply(marca(), {"step": [0.5, 0], "times": 0}).size, (100, 60))


class Paso(unittest.TestCase):
    def test_uno_deja_las_copias_pegadas(self):
        self.assertEqual(repeat.apply(marca(), {"step": [1, 0]}).size, (200, 60))

    def test_medio_las_solapa_a_la_mitad(self):
        self.assertEqual(repeat.apply(marca(), {"step": [0.5, 0]}).size, (150, 60))

    def test_negativo_va_en_sentido_contrario(self):
        izquierda = repeat.apply(marca(), {"step": [-0.5, 0]})
        derecha = repeat.apply(marca(), {"step": [0.5, 0]})
        self.assertEqual(izquierda.size, derecha.size)
        self.assertEqual(izquierda.transpose(Image.Transpose.FLIP_LEFT_RIGHT).size, derecha.size)

    def test_es_proporcion_no_pixeles(self):
        # El mismo paso sobre piezas de distinto tamaño crece en proporción.
        chica = repeat.apply(marca(100, 60), {"step": [0.5, 0]})
        grande = repeat.apply(marca(400, 240), {"step": [0.5, 0]})
        self.assertEqual((grande.width / chica.width, grande.height / chica.height), (4.0, 4.0))

    def test_vertical(self):
        self.assertEqual(repeat.apply(marca(), {"step": [0, 0.5]}).size, (100, 90))

    def test_diagonal(self):
        self.assertEqual(repeat.apply(marca(), {"step": [0.5, 0.5]}).size, (150, 90))

    def test_par_suelto_equivale_a_step(self):
        self.assertEqual(repeat.apply(marca(), [0.5, 0]).tobytes(),
                         repeat.apply(marca(), {"step": [0.5, 0]}).tobytes())

    def test_times_alarga_la_secuencia(self):
        self.assertEqual(repeat.apply(marca(), {"step": [1, 0], "times": 3}).size, (400, 60))


class VariosPasos(unittest.TestCase):
    def test_cruz(self):
        salida = repeat.apply(marca(), {"steps": [[1, 0], [-1, 0], [0, 1], [0, -1]]})
        self.assertEqual(salida.size, (300, 180))

    def test_cada_paso_arranca_de_la_original(self):
        # Dos pasos opuestos dejan la original al centro, no en una esquina.
        salida = repeat.apply(marca(), {"steps": [[1, 0], [-1, 0]]})
        self.assertEqual(salida.size, (300, 60))

    def test_lista_suelta_equivale_a_steps(self):
        self.assertEqual(repeat.apply(marca(), [[1, 0], [0, 1]]).size,
                         repeat.apply(marca(), {"steps": [[1, 0], [0, 1]]}).size)

    def test_cada_paso_pisa_lo_general(self):
        salida = repeat.apply(marca(), {
            "times": 1,
            "steps": [[1, 0], {"step": [0, 1], "times": 3}],
        })
        self.assertEqual(salida.size, (200, 240))

    def test_un_paso_puede_girar_lo_suyo(self):
        recto = repeat.apply(marca(), {"steps": [{"step": [1, 0]}]})
        girado = repeat.apply(marca(), {"steps": [{"step": [1, 0], "rotate": 90}]})
        self.assertNotEqual(recto.size, girado.size)


class Espejo(unittest.TestCase):
    def test_alternate_voltea_las_impares(self):
        salida = repeat.apply(marca(100, 60), {"step": [1, 0], "mirror": True})
        # La marca de la original queda a la izquierda; la de la copia, a la derecha.
        self.assertEqual(salida.getpixel((5, 5))[:3], (240, 240, 240))
        self.assertEqual(salida.getpixel((195, 5))[:3], (240, 240, 240))

    def test_sin_espejo_no_voltea(self):
        salida = repeat.apply(marca(100, 60), {"step": [1, 0]})
        self.assertEqual(salida.getpixel((105, 5))[:3], (240, 240, 240))
        self.assertNotEqual(salida.getpixel((195, 5))[:3], (240, 240, 240))

    def test_all_voltea_todas(self):
        alterno = repeat.apply(marca(), {"step": [1, 0], "times": 2, "mirror": "alternate"})
        todas = repeat.apply(marca(), {"step": [1, 0], "times": 2, "mirror": "all"})
        self.assertNotEqual(alterno.tobytes(), todas.tobytes())

    def test_el_eje_sigue_al_paso(self):
        # Paso vertical, espejo vertical: la marca de la copia queda abajo.
        salida = repeat.apply(marca(100, 60), {"step": [0, 1], "mirror": True})
        self.assertEqual(salida.getpixel((5, 5))[:3], (240, 240, 240))
        self.assertEqual(salida.getpixel((5, 115))[:3], (240, 240, 240))


class Giro(unittest.TestCase):
    def test_se_acumula_por_copia(self):
        # Paso cero y giros de 90: molinete sobre el mismo centro.
        salida = repeat.apply(marca(100, 100), {"step": [0, 0], "times": 3, "rotate": 90})
        self.assertEqual(salida.size, (100, 100))

    def test_el_giro_cambia_el_tamano_del_conjunto(self):
        recto = repeat.apply(marca(100, 60), {"step": [1, 0], "times": 2})
        girado = repeat.apply(marca(100, 60), {"step": [1, 0], "times": 2, "rotate": 90})
        self.assertNotEqual(recto.size, girado.size)

    def test_las_copias_giradas_siguen_centradas_en_su_lugar(self):
        # El desplazamiento se mide entre centros, así que un giro no descoloca.
        salida = repeat.apply(marca(100, 100), {"step": [1, 0], "rotate": 90})
        self.assertEqual(salida.size, (200, 100))


class Desvanecido(unittest.TestCase):
    def test_las_copias_pierden_opacidad(self):
        salida = repeat.apply(marca(), {"step": [1, 0], "times": 2, "fade": 0.3})
        self.assertLess(salida.getpixel((150, 30))[3], 255)
        self.assertEqual(salida.getpixel((50, 30))[3], 255)

    def test_fade_alto_descarta_las_invisibles(self):
        # Con fade 1 la primera copia ya es transparente y no aporta tamaño.
        self.assertEqual(repeat.apply(marca(), {"step": [1, 0], "times": 3, "fade": 1}).size,
                         (100, 60))


class Fusion(unittest.TestCase):
    def test_multiply_no_ennegrece_la_zona_vacia(self):
        # El RGB de un pixel transparente es negro: sin cuidado, multiply
        # pintaba de negro todo lo que no se solapaba.
        claro = Image.new("RGBA", (60, 60), (255, 255, 255, 255))
        salida = repeat.apply(claro, {"step": [1, 0], "blend": "multiply"})
        self.assertEqual(salida.getpixel((90, 30))[:3], (255, 255, 255))

    def test_multiply_oscurece_donde_se_solapan(self):
        gris = Image.new("RGBA", (60, 60), (200, 200, 200, 255))
        salida = repeat.apply(gris, {"step": [0.5, 0], "blend": "multiply"})
        self.assertLess(salida.getpixel((45, 30))[0], 200)
        self.assertEqual(salida.getpixel((5, 30))[0], 200)

    def test_modo_invalido(self):
        with self.assertRaises(SpecError):
            repeat.apply(marca(), {"step": [1, 0], "blend": "disolver"})


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            repeat.apply(marca(), {"paso": [1, 0]})

    def test_clave_desconocida_en_un_paso(self):
        with self.assertRaises(SpecError):
            repeat.apply(marca(), {"steps": [{"step": [1, 0], "veces": 2}]})

    def test_step_y_steps_excluyentes(self):
        with self.assertRaises(SpecError):
            repeat.apply(marca(), {"step": [1, 0], "steps": [[0, 1]]})

    def test_sin_paso(self):
        with self.assertRaises(SpecError):
            repeat.apply(marca(), {"times": 3})
        with self.assertRaises(SpecError):
            repeat.apply(marca(), {"steps": [{"times": 2}]})

    def test_paso_mal_formado(self):
        for malo in ([1], [1, 2, 3], "1,0", [1, "x"], [True, 0], [100, 0]):
            with self.assertRaises(SpecError, msg=malo):
                repeat.apply(marca(), {"step": malo})

    def test_times_invalido(self):
        for malo in (-1, 2.5, "tres", True, 9999):
            with self.assertRaises(SpecError, msg=malo):
                repeat.apply(marca(), {"step": [1, 0], "times": malo})

    def test_mirror_invalido(self):
        with self.assertRaises(SpecError):
            repeat.apply(marca(), {"step": [1, 0], "mirror": "espejito"})

    def test_fade_fuera_de_rango(self):
        for malo in (-0.1, 2, "medio"):
            with self.assertRaises(SpecError, msg=malo):
                repeat.apply(marca(), {"step": [1, 0], "fade": malo})

    def test_tope_de_copias(self):
        with self.assertRaises(SpecError):
            repeat.apply(marca(), {"steps": [[1, 0]] * 50, "times": 100})

    def test_tope_de_tamano(self):
        with self.assertRaises(SpecError) as caso:
            repeat.apply(marca(2000, 2000), {"step": [3, 3], "times": 20})
        self.assertIn("revisa el paso", str(caso.exception))

    def test_tipo_invalido(self):
        with self.assertRaises(SpecError):
            repeat.apply(marca(), "doble")

    def test_no_muta_el_original(self):
        original = marca()
        antes = original.tobytes()
        repeat.apply(original, {"step": [0.5, 0], "times": 2, "mirror": True})
        self.assertEqual(original.tobytes(), antes)


if __name__ == "__main__":
    unittest.main()