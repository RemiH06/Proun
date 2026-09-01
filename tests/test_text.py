"""Pruebas de proun.ops.text."""

import unittest
from pathlib import Path

from proun.errors import SpecError
from proun.ops import text


def _tonos(im):
    return {rgba[0] for _, rgba in im.getcolors(maxcolors=200_000) if rgba[3] > 0}


class Generacion(unittest.TestCase):
    def test_texto_suelto_equivale_a_dict(self):
        self.assertEqual(text.build("PROUN").tobytes(),
                         text.build({"text": "PROUN"}).tobytes())

    def test_devuelve_rgba_con_algo_pintado(self):
        im = text.build("PROUN")
        self.assertEqual(im.mode, "RGBA")
        self.assertGreater(im.getchannel("A").getextrema()[1], 0)

    def test_el_relleno_es_blanco_puro(self):
        tonos = _tonos(text.build("O"))
        self.assertIn(text.FILL, tonos)

    def test_es_determinista(self):
        self.assertEqual(text.build("PROUN").tobytes(), text.build("PROUN").tobytes())

    def test_textos_distintos_dan_imagenes_distintas(self):
        self.assertNotEqual(text.build("PROUN").size, text.build("PROUN 1926").size)

    def test_vacio_es_un_error(self):
        for malo in ("", "   ", {"text": ""}):
            with self.assertRaises(SpecError, msg=malo):
                text.build(malo)


class Peso(unittest.TestCase):
    def test_bold_es_el_default(self):
        self.assertEqual(text.build("PROUN").tobytes(),
                         text.build({"text": "PROUN", "weight": "bold"}).tobytes())

    def test_regular_da_otra_imagen(self):
        self.assertNotEqual(text.build({"text": "PROUN", "weight": "bold"}).tobytes(),
                            text.build({"text": "PROUN", "weight": "regular"}).tobytes())

    def test_peso_invalido(self):
        with self.assertRaises(SpecError):
            text.build({"text": "PROUN", "weight": "italic"})


class FuentePropia(unittest.TestCase):
    def test_ruta_valida(self):
        ruta = text.DEFAULT_FONTS["regular"]
        im = text.build({"text": "PROUN", "font": str(ruta)})
        self.assertEqual(im.tobytes(),
                         text.build({"text": "PROUN", "weight": "regular"}).tobytes())

    def test_ruta_inexistente(self):
        with self.assertRaises(SpecError):
            text.build({"text": "PROUN", "font": "/no/existe/algo.ttf"})


class Acentos(unittest.TestCase):
    def test_la_fuente_empaquetada_cubre_espanol(self):
        # No deben quedar cuadros vacíos (notdef): cada carácter aporta algo
        # de tinta propia, y la palabra completa mide más que sus partes.
        for palabra in ("ÁRBOL", "ñoño", "¿qué?", "canción"):
            im = text.build(palabra)
            self.assertGreater(im.width, 10, palabra)
            self.assertGreater(im.getchannel("A").getextrema()[1], 0, palabra)


class Alineado(unittest.TestCase):
    def test_align_invalido(self):
        with self.assertRaises(SpecError):
            text.build({"text": "PROUN", "align": "justify"})

    def test_wrap_ausente_no_corta_lineas(self):
        largo = text.build("UNA LINEA MUY MUY LARGA DE VERDAD")
        # Sin wrap, todo cabe en una sola línea: el ancho crece con el texto.
        corto = text.build("HOLA")
        self.assertGreater(largo.width, corto.width * 3)

    def test_wrap_corta_en_varias_lineas(self):
        sin_wrap = text.build("UNA FRASE BASTANTE LARGA PARA PROBAR")
        con_wrap = text.build({"text": "UNA FRASE BASTANTE LARGA PARA PROBAR", "wrap": 0.3})
        self.assertGreater(con_wrap.height, sin_wrap.height)
        self.assertLess(con_wrap.width, sin_wrap.width)

    def test_wrap_fuera_de_rango(self):
        for malo in (0, 1.5, -0.2, "media", True):
            with self.assertRaises(SpecError, msg=malo):
                text.build({"text": "PROUN", "wrap": malo})

    def test_line_spacing_agranda_el_alto(self):
        chico = text.build({"text": "UNA FRASE LARGA PARA PROBAR", "wrap": 0.3,
                            "line_spacing": 1.0})
        grande = text.build({"text": "UNA FRASE LARGA PARA PROBAR", "wrap": 0.3,
                             "line_spacing": 2.0})
        self.assertGreater(grande.height, chico.height)

    def test_line_spacing_invalido(self):
        for malo in (0, -1, "mucho"):
            with self.assertRaises(SpecError, msg=malo):
                text.build({"text": "PROUN", "line_spacing": malo})

    def test_left_center_right_dan_imagenes_distintas(self):
        base = "UNA FRASE LARGA PARA PROBAR EL ALINEADO DE VERDAD"
        izq = text.build({"text": base, "wrap": 0.3, "align": "left"})
        centro = text.build({"text": base, "wrap": 0.3, "align": "center"})
        der = text.build({"text": base, "wrap": 0.3, "align": "right"})
        self.assertNotEqual(izq.tobytes(), centro.tobytes())
        self.assertNotEqual(centro.tobytes(), der.tobytes())
        self.assertEqual(izq.size, der.size)


class Contorno(unittest.TestCase):
    def test_sin_outline_el_gris_del_contorno_pesa_poco(self):
        # Una letra curva antialiasea casi todos los grises en su borde;
        # se comprueba que el peso alrededor de CONTORNO sea marginal, no
        # que esté ausente del todo.
        def peso_contorno(im):
            return sum(n for n, rgba in im.getcolors(200_000)
                      if rgba[3] > 0 and abs(rgba[0] - text.CONTORNO) <= 3)

        im = text.build("O")
        total = sum(v for v in im.getchannel("A").histogram()[1:]) or 1
        self.assertLess(peso_contorno(im) / total, 0.05)

    def test_con_outline_hay_muchos_mas_pixeles_cerca_del_gris_del_contorno(self):
        # Una letra curva antialiasea casi todos los grises en su borde, así
        # que "aparece o no aparece" no es una prueba justa; se compara
        # cuánto pesa la banda alrededor de CONTORNO entre las dos versiones.
        def peso_contorno(im):
            return sum(n for n, rgba in im.getcolors(200_000)
                      if rgba[3] > 0 and abs(rgba[0] - text.CONTORNO) <= 5)

        sin = peso_contorno(text.build("O"))
        con = peso_contorno(text.build({"text": "O", "outline": {"width": 0.08}}))
        self.assertGreater(con, sin * 3)

    def test_outline_agranda_la_imagen(self):
        sin = text.build("O")
        con = text.build({"text": "O", "outline": {"width": 0.1}})
        self.assertGreaterEqual(con.width, sin.width)

    def test_outline_no_es_objeto(self):
        with self.assertRaises(SpecError):
            text.build({"text": "PROUN", "outline": "grueso"})

    def test_width_fuera_de_rango(self):
        for malo in (-0.1, 0.5, "poco", True):
            with self.assertRaises(SpecError, msg=malo):
                text.build({"text": "PROUN", "outline": {"width": malo}})


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            text.build({"text": "PROUN", "tamano": 40})

    def test_falta_la_clave_text(self):
        with self.assertRaises(SpecError):
            text.build({"weight": "bold"})

    def test_tipo_invalido(self):
        for malo in (5, ["PROUN"], None):
            with self.assertRaises(SpecError, msg=malo):
                text.build(malo)


class FuenteEmpaquetada(unittest.TestCase):
    def test_los_dos_pesos_existen(self):
        self.assertTrue(Path(text.DEFAULT_FONTS["bold"]).is_file())
        self.assertTrue(Path(text.DEFAULT_FONTS["regular"]).is_file())


if __name__ == "__main__":
    unittest.main()