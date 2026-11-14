"""Pruebas de proun.ops.iso: figuras isométricas de cubos."""

import unittest

from proun import compose, spec
from proun.errors import SpecError
from proun.ops import iso, recolor, shapes


def figura(nombre, **extra):
    return iso.build({"kind": "iso", "figure": nombre, **extra})


def cubo():
    """Un cubo solo y dónde cae el centro de cada una de sus tres caras."""
    im = figura("cubo")
    w, h = im.size
    return im, {"arriba": (w // 2, h // 4), "izquierda": (w // 4, h * 3 // 5),
                "derecha": (w * 3 // 4, h * 3 // 5)}


class Generacion(unittest.TestCase):
    def test_todas_las_figuras_generan_algo(self):
        for nombre in iso.FIGURAS:
            with self.subTest(figura=nombre):
                im = figura(nombre)
                self.assertEqual(im.mode, "RGBA")
                self.assertEqual(max(im.size), iso.BASE)
                self.assertEqual(im.getchannel("A").getextrema()[1], 255)

    def test_cada_cara_tiene_su_gris(self):
        im, centros = cubo()
        self.assertEqual(im.getpixel(centros["arriba"]), (iso.ARRIBA,) * 3 + (255,))
        self.assertEqual(im.getpixel(centros["izquierda"]), (iso.IZQUIERDA,) * 3 + (255,))
        self.assertEqual(im.getpixel(centros["derecha"]), (iso.DERECHA,) * 3 + (255,))

    def test_fuera_de_la_figura_es_transparente(self):
        im, _ = cubo()
        # Las esquinas del recuadro quedan fuera del hexágono del cubo.
        self.assertEqual(im.getpixel((1, 1))[3], 0)
        self.assertEqual(im.getpixel((im.width - 2, im.height - 2))[3], 0)

    def test_el_borde_no_tiene_halo_oscuro(self):
        # El vértice de arriba es cara superior (blanca) a medio cubrir: al
        # achicar no debe mezclarse con el negro del fondo vacío.
        im, _ = cubo()
        x = im.width // 2
        for y in range(4):
            gris, _, _, alfa = im.getpixel((x, y))
            if 0 < alfa < 255:
                self.assertGreater(gris, 230)

    def test_es_determinista(self):
        self.assertEqual(figura("penrose").tobytes(), figura("penrose").tobytes())

    def test_el_tamano_cambia_la_figura(self):
        self.assertNotEqual(figura("marco", size=3).tobytes(), figura("marco", size=5).tobytes())

    def test_desde_shapes(self):
        self.assertEqual(shapes.build({"kind": "iso", "figure": "cruz"}).tobytes(),
                         figura("cruz").tobytes())
        # "iso" suelto es un cubo.
        self.assertEqual(shapes.build("iso").tobytes(), figura("cubo").tobytes())


class Imposibles(unittest.TestCase):
    def test_adelantar_un_cubo_no_deja_costura(self):
        # Una columna de dos cubos donde el de arriba se pinta antes: sin
        # ocultar caras tocadas, el de abajo pintaría su cara superior encima
        # del de arriba. Tiene que verse igual que la columna normal.
        normal = iso.build({"kind": "iso", "voxels": [[0, 0, 0], [0, 0, 1]]})
        adelantada = iso.build({"kind": "iso", "voxels": [[0, 0, 0], [0, 0, 1, 1]]})
        self.assertEqual(normal.tobytes(), adelantada.tobytes())

    def test_penrose_no_es_el_mismo_recorrido_pintado_en_orden(self):
        # Mismos cubos sin el truco de orden: la punta del brazo que sube
        # tapa el arranque del primero y la ilusión no cierra.
        n = 5
        trucados = iso._penrose(n)
        planos = [[x, y, z] for x, y, z, _ in trucados]
        self.assertNotEqual(figura("penrose", size=n).tobytes(),
                            iso.build({"kind": "iso", "voxels": planos}).tobytes())

    def test_penrose_cierra_sobre_si_mismo(self):
        # La punta del tercer brazo cae en pantalla justo sobre el arranque
        # del primero: por eso el triángulo parece cerrado.
        self.assertEqual(iso._proyectar(5, 5, 5), iso._proyectar(0, 0, 0))


class ConRecolor(unittest.TestCase):
    def test_tres_stops_dan_un_color_por_cara(self):
        im, centros = cubo()
        pintado = recolor.apply(im, "#000000", {"mode": "colormap",
                                                "stops": ["#ff0000", "#00ff00", "#0000ff"]})
        self.assertEqual(pintado.getpixel(centros["derecha"])[:3], (255, 0, 0))
        self.assertEqual(pintado.getpixel(centros["arriba"])[:3], (0, 0, 255))
        r, g, b = pintado.getpixel(centros["izquierda"])[:3]
        self.assertEqual(r, 0)
        self.assertGreater(g, 250)
        self.assertLess(b, 5)

    def test_entra_a_un_wallpaper(self):
        base = spec.build({
            "sources": [{"shape": {"kind": "iso", "figure": "penrose"}, "position": [0.5, 0.5]}],
            "resolutions": ["400x300"], "colors": ["#3ba7ff"], "seeds": [1],
        })
        salida = compose.render(base, compose.plan(base, 1), (400, 300), "#3ba7ff")
        self.assertEqual(salida.size, (400, 300))


class Validacion(unittest.TestCase):
    def falla(self, shape, outline=None):
        with self.assertRaises(SpecError):
            shapes.build(shape, outline)

    def test_figura_desconocida(self):
        self.falla({"kind": "iso", "figure": "dodecaedro"})

    def test_tamano_fuera_de_rango(self):
        for nombre, malo in (("penrose", 3), ("penrose", 11), ("marco", 2), ("cubo", 2),
                             ("cruz", True), ("escalera", 2.5)):
            with self.subTest(figura=nombre, size=malo):
                self.falla({"kind": "iso", "figure": nombre, "size": malo})

    def test_clave_desconocida(self):
        self.falla({"kind": "iso", "figure": "cubo", "color": "#fff"})

    def test_figure_y_voxels_juntos(self):
        self.falla({"kind": "iso", "figure": "cubo", "voxels": [[0, 0, 0]]})

    def test_voxels_mal_formados(self):
        for malo in ([], [[0, 0]], [[0, 0, 0.5]], [[0, 0, 0, 0, 0]], "cubos", [[0, 0, True]]):
            with self.subTest(voxels=malo):
                self.falla({"kind": "iso", "voxels": malo})

    def test_voxels_repetidos(self):
        self.falla({"kind": "iso", "voxels": [[0, 0, 0], [0, 0, 0, 2]]})

    def test_demasiados_voxels(self):
        self.falla({"kind": "iso", "voxels": [[i, 0, 0] for i in range(iso.MAX_VOXELS + 1)]})

    def test_no_lleva_contorno(self):
        self.falla({"kind": "iso"}, {"width": 0.05})


if __name__ == "__main__":
    unittest.main()
