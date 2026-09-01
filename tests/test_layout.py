"""Pruebas de proun.layout."""

import random
import unittest

from proun import layout
from proun.errors import SpecError


def rng(semilla=5):
    return random.Random(semilla)


class Reproducibilidad(unittest.TestCase):
    def test_misma_semilla_mismas_posiciones(self):
        for modo in layout.MODES:
            spec = {"mode": modo}
            self.assertEqual(layout.positions(6, rng(5), spec),
                             layout.positions(6, rng(5), spec), modo)

    def test_semillas_distintas_divergen(self):
        self.assertNotEqual(layout.positions(6, rng(1)), layout.positions(6, rng(2)))

    def test_los_tamanos_tambien_son_reproducibles(self):
        self.assertEqual(layout.sizes(5, rng(3)), layout.sizes(5, rng(3)))

    def test_las_posiciones_no_dependen_de_la_resolucion(self):
        # Son normalizadas: el mismo plan sirve para 1080p y para 4K.
        for centro in layout.positions(8, rng(9)):
            self.assertIsInstance(centro[0], float)
            self.assertIsInstance(centro[1], float)


class Modos(unittest.TestCase):
    def test_cantidad_correcta(self):
        for modo in layout.MODES:
            self.assertEqual(len(layout.positions(7, rng(), {"mode": modo})), 7, modo)

    def test_cero_capas(self):
        self.assertEqual(layout.positions(0, rng()), [])

    def test_scatter_reparte(self):
        # El punto de que scatter sea estratificado: no deja media pantalla vacía.
        puntos = layout.positions(9, rng(2), {"mode": "scatter", "bleed": 0})
        self.assertTrue(any(x < 0.4 for x, _ in puntos))
        self.assertTrue(any(x > 0.6 for x, _ in puntos))
        self.assertTrue(any(y < 0.4 for _, y in puntos))
        self.assertTrue(any(y > 0.6 for _, y in puntos))

    def test_scatter_reparte_con_muchas_semillas(self):
        for semilla in range(15):
            puntos = layout.positions(9, rng(semilla), {"mode": "scatter", "bleed": 0})
            self.assertTrue(any(x > 0.5 for x, _ in puntos), semilla)
            self.assertTrue(any(x < 0.5 for x, _ in puntos), semilla)

    def test_free_es_azar_puro(self):
        puntos = layout.positions(40, rng(4), {"mode": "free", "bleed": 0})
        self.assertTrue(all(0 <= x <= 1 for x, _ in puntos))

    def test_row_reparte_en_horizontal(self):
        puntos = layout.positions(4, rng(), {"mode": "row", "jitter": 0, "shuffle": False})
        xs = [x for x, _ in puntos]
        self.assertEqual(xs, sorted(xs))
        self.assertTrue(all(abs(y - 0.5) < 1e-9 for _, y in puntos))

    def test_column_reparte_en_vertical(self):
        puntos = layout.positions(4, rng(), {"mode": "column", "jitter": 0, "shuffle": False})
        ys = [y for _, y in puntos]
        self.assertEqual(ys, sorted(ys))
        self.assertTrue(all(abs(x - 0.5) < 1e-9 for x, _ in puntos))

    def test_stack_apila_al_centro(self):
        puntos = layout.positions(5, rng(), {"mode": "stack", "jitter": 0})
        self.assertTrue(all(p == (0.5, 0.5) for p in puntos))

    def test_grid_sin_temblor_da_celdas_exactas(self):
        puntos = layout.positions(4, rng(), {"mode": "grid", "jitter": 0, "shuffle": False})
        self.assertEqual(sorted(puntos), [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)])

    def test_shuffle_cambia_el_reparto(self):
        ordenado = layout.positions(6, rng(3), {"mode": "grid", "jitter": 0, "shuffle": False})
        revuelto = layout.positions(6, rng(3), {"mode": "grid", "jitter": 0, "shuffle": True})
        self.assertEqual(sorted(ordenado), sorted(revuelto))
        self.assertNotEqual(ordenado, revuelto)


class Sangrado(unittest.TestCase):
    def test_bleed_permite_salirse(self):
        puntos = layout.positions(20, rng(6), {"mode": "free", "bleed": 0.3})
        self.assertTrue(any(x < 0 or x > 1 for x, _ in puntos))

    def test_sin_bleed_todo_queda_dentro(self):
        puntos = layout.positions(20, rng(6), {"mode": "scatter", "bleed": 0})
        self.assertTrue(all(0 <= x <= 1 and 0 <= y <= 1 for x, y in puntos))


class Tamanos(unittest.TestCase):
    def test_rango_por_defecto(self):
        low, high = layout.DEFAULT_SIZE
        self.assertTrue(all(low <= f <= high for f in layout.sizes(20, rng())))

    def test_numero_suelto_es_fijo(self):
        self.assertEqual(layout.sizes(3, rng(), {"size": 0.5}), [0.5, 0.5, 0.5])

    def test_rango_explicito(self):
        self.assertTrue(all(0.2 <= f <= 0.3 for f in layout.sizes(20, rng(), {"size": [0.2, 0.3]})))

    def test_invalidos(self):
        for malo in ([0.8, 0.2], [0, 1], [1, 20], [0.5], "medio", [None, 1]):
            with self.assertRaises(SpecError, msg=malo):
                layout.sizes(3, rng(), {"size": malo})


class Pixeles(unittest.TestCase):
    def test_centra_la_capa_en_el_punto(self):
        self.assertEqual(layout.to_pixels((0.5, 0.5), (100, 100), (1000, 500)), (450, 200))

    def test_centro_fuera_del_lienzo_da_negativo(self):
        self.assertEqual(layout.to_pixels((0.0, 0.0), (100, 100), (1000, 500)), (-50, -50))

    def test_escala_con_el_lienzo(self):
        chico = layout.to_pixels((0.5, 0.5), (100, 100), (1000, 500))
        grande = layout.to_pixels((0.5, 0.5), (200, 200), (2000, 1000))
        self.assertEqual((grande[0] / 2, grande[1] / 2), (chico[0], chico[1]))


class PosicionExplicita(unittest.TestCase):
    def test_fracciones_del_lienzo(self):
        self.assertEqual(layout.explicit([0.5, 0.5], (100, 100), (1000, 500)), (450, 200))

    def test_pixeles(self):
        self.assertEqual(layout.explicit([100, 100], (50, 50), (1000, 500)), (75, 75))

    def test_ancla_cambia_el_punto_de_agarre(self):
        self.assertEqual(layout.explicit([0, 0], (50, 50), (1000, 500), anchor="topleft"), (0, 0))
        self.assertEqual(layout.explicit([0, 0], (50, 50), (1000, 500), anchor="center"),
                         (-25, -25))

    def test_ancla_nombrada_sin_coordenadas(self):
        self.assertEqual(layout.explicit("bottomright", (100, 100), (1000, 500)), (900, 400))
        self.assertEqual(layout.explicit("topleft", (100, 100), (1000, 500)), (0, 0))

    def test_coordenadas_negativas_son_validas(self):
        self.assertEqual(layout.explicit([-50, -20], (10, 10), (1000, 500), anchor="topleft"),
                         (-50, -20))

    def test_mal_formada(self):
        for malo in ([0.5], [1, 2, 3], 0.5, None, ["x", 0]):
            with self.assertRaises(SpecError, msg=malo):
                layout.explicit(malo, (10, 10), (1000, 500))

    def test_ancla_desconocida(self):
        with self.assertRaises(SpecError):
            layout.explicit([0, 0], (10, 10), (1000, 500), anchor="esquinita")


class Sangrado(unittest.TestCase):
    def test_cero_deja_la_capa_completamente_dentro(self):
        self.assertEqual(layout.clamp((-50, -50), (100, 100), (1000, 500), (0, 0)), (0, 0))
        self.assertEqual(layout.clamp((9999, 9999), (100, 100), (1000, 500), (0, 0)), (900, 400))

    def test_permite_salirse_esa_fraccion_del_tamano(self):
        # bleed 0.25 de una capa de 100 px son 25 px de margen.
        self.assertEqual(layout.clamp((-80, 0), (100, 100), (1000, 500), (0.25, 0.25))[0], -25)
        self.assertEqual(layout.clamp((980, 0), (100, 100), (1000, 500), (0.25, 0.25))[0], 925)

    def test_uno_permite_salirse_entera(self):
        self.assertEqual(layout.clamp((-100, 0), (100, 100), (1000, 500), (1, 1))[0], -100)

    def test_no_toca_lo_que_ya_esta_dentro(self):
        self.assertEqual(layout.clamp((300, 200), (100, 100), (1000, 500), (0, 0)), (300, 200))

    def test_ejes_independientes(self):
        self.assertEqual(layout.clamp((-80, -80), (100, 100), (1000, 500), (0.5, 0)), (-50, 0))

    def test_capa_mas_grande_que_el_lienzo_se_centra(self):
        self.assertEqual(layout.clamp((0, 0), (1200, 700), (1000, 500), (0, 0)), (-100, -100))


class Empaquetado(unittest.TestCase):
    def rects_no_solapan(self, posiciones, sizes):
        rects = list(zip(posiciones, sizes))
        for i in range(len(rects)):
            (ax, ay), (aw, ah) = rects[i]
            for j in range(i + 1, len(rects)):
                (bx, by), (bw, bh) = rects[j]
                solapan = not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)
                self.assertFalse(solapan, (i, j))

    def test_vacio(self):
        self.assertEqual(layout.pack([], 500), ([], (0, 0)))

    def test_una_pieza_queda_en_el_origen(self):
        posiciones, bloque = layout.pack([(100, 60)], 500)
        self.assertEqual(posiciones, [(0, 0)])
        self.assertEqual(bloque, (100, 60))

    def test_sin_solapes_con_muchas_piezas(self):
        r = random.Random(3)
        sizes = [(r.randint(20, 200), r.randint(20, 200)) for _ in range(25)]
        posiciones, _ = layout.pack(sizes, 700)
        self.rects_no_solapan(posiciones, sizes)

    def test_sin_solapes_barrido_de_semillas(self):
        for semilla in range(60):
            r = random.Random(semilla)
            n = r.randint(1, 15)
            sizes = [(r.randint(20, 250), r.randint(20, 250)) for _ in range(n)]
            posiciones, _ = layout.pack(sizes, r.randint(150, 800), gap=r.choice([0, 2, 5]))
            self.rects_no_solapan(posiciones, sizes)

    def test_nada_se_sale_del_ancho_pedido(self):
        # Salvo la pieza que de por sí es más ancha que el pedido.
        sizes = [(80, 40)] * 10
        posiciones, bloque = layout.pack(sizes, 300)
        self.assertTrue(all(x + 80 <= 300 for x, _ in posiciones))
        self.assertLessEqual(bloque[0], 300)

    def test_pieza_mas_ancha_que_el_pedido_no_se_recorta(self):
        posiciones, bloque = layout.pack([(500, 50)], 200)
        self.assertEqual(bloque[0], 500)

    def test_gap_separa_las_piezas(self):
        junto = layout.pack([(100, 50), (100, 50)], 300, gap=0)[0]
        separado = layout.pack([(100, 50), (100, 50)], 300, gap=10)[0]
        self.assertNotEqual(junto, separado)

    def test_es_determinista(self):
        sizes = [(80, 40), (60, 90), (120, 30)]
        self.assertEqual(layout.pack(sizes, 300), layout.pack(sizes, 300))

    def test_el_orden_importa(self):
        sizes = [(80, 40), (60, 90), (120, 30)]
        a, _ = layout.pack(sizes, 300)
        b, _ = layout.pack(list(reversed(sizes)), 300)
        self.assertNotEqual(a, list(reversed(b)))

    def test_bloque_es_la_caja_que_contiene_todo(self):
        sizes = [(80, 40), (60, 90), (120, 30), (50, 50)]
        posiciones, bloque = layout.pack(sizes, 300)
        for (x, y), (w, h) in zip(posiciones, sizes):
            self.assertLessEqual(x + w, bloque[0])
            self.assertLessEqual(y + h, bloque[1])


class Centrado(unittest.TestCase):
    def test_centra_horizontal_siempre(self):
        x, _ = layout.center_block((200, 100), (1000, 500), "top")
        self.assertEqual(x, 400)

    def test_top(self):
        self.assertEqual(layout.center_block((200, 100), (1000, 500), "top"), (400, 0))

    def test_bottom(self):
        self.assertEqual(layout.center_block((200, 100), (1000, 500), "bottom"), (400, 400))

    def test_center(self):
        self.assertEqual(layout.center_block((200, 100), (1000, 500), "center"), (400, 200))

    def test_ancla_invalida(self):
        with self.assertRaises(SpecError):
            layout.center_block((200, 100), (1000, 500), "izquierda")


class OpcionesDeEmpaquetado(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(layout.pack_options({}), (0.94, 0, "center"))

    def test_valores_explicitos(self):
        self.assertEqual(layout.pack_options({"width": 0.8, "gap": 4, "anchor": "top"}),
                         (0.8, 4, "top"))

    def test_width_fuera_de_rango(self):
        for malo in (0, 1.5, -0.2, "mucho"):
            with self.assertRaises(SpecError, msg=malo):
                layout.pack_options({"width": malo})

    def test_gap_invalido(self):
        for malo in (-1, 2.5, "poco", True):
            with self.assertRaises(SpecError, msg=malo):
                layout.pack_options({"gap": malo})


class Validacion(unittest.TestCase):
    def test_clave_desconocida(self):
        with self.assertRaises(SpecError):
            layout.positions(3, rng(), {"modo": "scatter"})

    def test_align_no_consume_el_generador(self):
        # El centro es un relleno: la posición real sale de compose._pack.
        estado_antes = rng(5).getstate()
        r = rng(5)
        layout.positions(4, r, {"mode": "align"})
        self.assertEqual(r.getstate(), estado_antes)

    def test_align_da_centros_constantes(self):
        self.assertEqual(layout.positions(3, rng(), {"mode": "align"}), [(0.5, 0.5)] * 3)

    def test_modo_invalido(self):
        with self.assertRaises(SpecError):
            layout.positions(3, rng(), {"mode": "espiral"})

    def test_spec_de_otro_tipo(self):
        for malo in ("scatter", [1, 2], 3):
            with self.assertRaises(SpecError, msg=malo):
                layout.positions(3, rng(), malo)
            with self.assertRaises(SpecError, msg=malo):
                layout.sizes(3, rng(), malo)

    def test_bleed_y_jitter_fuera_de_rango(self):
        for spec in ({"bleed": -1}, {"bleed": 2}, {"jitter": 5}, {"jitter": "poco"}):
            with self.assertRaises(SpecError, msg=spec):
                layout.positions(3, rng(), spec)

    def test_conteo_negativo(self):
        with self.assertRaises(SpecError):
            layout.positions(-1, rng())


if __name__ == "__main__":
    unittest.main()