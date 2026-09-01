"""Pruebas de proun.ops.shapes."""

import unittest


from proun.errors import SpecError
from proun.ops import shapes


def _tonos(im):
    """Los valores de gris presentes entre los píxeles no transparentes."""
    return {rgba[0] for _, rgba in im.getcolors(maxcolors=BASE_COLORS) if rgba[3] > 0}


BASE_COLORS = 100_000


class Generacion(unittest.TestCase):
    def test_todas_las_formas_generan_algo(self):
        for kind in shapes.KINDS:
            spec = {"kind": kind, "sides": 6} if kind == "polygon" else kind
            im = shapes.build(spec)
            self.assertEqual(im.mode, "RGBA")
            self.assertEqual(im.size, (shapes.BASE, shapes.BASE))
            self.assertGreater(im.getchannel("A").getextrema()[1], 0, kind)

    def test_texto_suelto_equivale_a_kind(self):
        self.assertEqual(shapes.build("circle").tobytes(),
                         shapes.build({"kind": "circle"}).tobytes())

    def test_hay_zonas_transparentes_fuera_de_la_figura(self):
        # Un círculo no llena las esquinas del cuadro que lo contiene.
        im = shapes.build("circle")
        self.assertEqual(im.getpixel((2, 2))[3], 0)

    def test_el_relleno_es_blanco_puro(self):
        im = shapes.build("rect")
        cx = cy = shapes.BASE // 2
        self.assertEqual(im.getpixel((cx, cy))[:3], (255, 255, 255))

    def test_es_determinista(self):
        self.assertEqual(shapes.build("triangle", {"inset": 0.1}).tobytes(),
                         shapes.build("triangle", {"inset": 0.1}).tobytes())


class Contorno(unittest.TestCase):
    def test_sin_outline_no_aparece_el_gris_del_contorno(self):
        # El antialiasing del reescalado deja algunos grises de borde, pero
        # ninguno debería coincidir con el gris reservado para el contorno.
        im = shapes.build("rect")
        tonos = _tonos(im)
        self.assertNotIn(shapes.CONTORNO, tonos)

    def test_con_outline_aparece_el_gris_del_contorno(self):
        im = shapes.build("rect", {"inset": 0.15, "width": 0.05})
        tonos = _tonos(im)
        self.assertIn(shapes.CONTORNO, tonos)
        self.assertIn(shapes.FILL, tonos)

    def test_el_contorno_no_toca_el_borde_real(self):
        # Con un inset grande, la fila justo dentro del borde sigue siendo
        # puro relleno: el contorno vive más adentro, no en el perímetro real.
        im = shapes.build("rect", {"inset": 0.3, "width": 0.03})
        borde = shapes.BASE // 20
        self.assertEqual(im.getpixel((borde, shapes.BASE // 2))[0], shapes.FILL)

    def test_inset_cero_pega_el_contorno_al_borde(self):
        im = shapes.build("rect", {"inset": 0.0, "width": 0.05})
        tonos = _tonos(im)
        self.assertIn(shapes.CONTORNO, tonos)

    def test_width_cero_no_dibuja_contorno(self):
        im = shapes.build("rect", {"inset": 0.15, "width": 0})
        tonos = _tonos(im)
        self.assertNotIn(shapes.CONTORNO, tonos)

    def test_circulo_tambien_lleva_contorno(self):
        im = shapes.build("circle", {"inset": 0.15, "width": 0.05})
        tonos = _tonos(im)
        self.assertIn(shapes.CONTORNO, tonos)


class Poligono(unittest.TestCase):
    def test_lados_por_defecto_es_seis(self):
        self.assertEqual(shapes.build({"kind": "polygon"}).tobytes(),
                         shapes.build({"kind": "polygon", "sides": 6}).tobytes())

    def test_distintos_lados_dan_distinta_figura(self):
        self.assertNotEqual(shapes.build({"kind": "polygon", "sides": 3}).tobytes(),
                            shapes.build({"kind": "polygon", "sides": 8}).tobytes())

    def test_lados_fuera_de_rango(self):
        for malo in (2, 13, 3.5, "seis", True):
            with self.assertRaises(SpecError, msg=malo):
                shapes.build({"kind": "polygon", "sides": malo})


class Validacion(unittest.TestCase):
    def test_kind_desconocido(self):
        with self.assertRaises(SpecError):
            shapes.build("estrella")

    def test_tipo_invalido(self):
        for malo in (5, ["circle"], None):
            with self.assertRaises(SpecError, msg=malo):
                shapes.build(malo)

    def test_outline_no_es_objeto(self):
        with self.assertRaises(SpecError):
            shapes.build("circle", "grueso")

    def test_outline_clave_desconocida(self):
        with self.assertRaises(SpecError):
            shapes.build("circle", {"grosor": 0.1})

    def test_inset_fuera_de_rango(self):
        for malo in (-0.1, 0.5, 1, "poco"):
            with self.assertRaises(SpecError, msg=malo):
                shapes.build("circle", {"inset": malo})

    def test_width_fuera_de_rango(self):
        for malo in (-0.1, 0.5, "poco", True):
            with self.assertRaises(SpecError, msg=malo):
                shapes.build("circle", {"width": malo})


if __name__ == "__main__":
    unittest.main()