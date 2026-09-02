"""Pruebas de proun.pool."""

import random
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from proun import pool
from proun.errors import SpecError

RAIZ = Path(tempfile.mkdtemp(prefix="proun-pool-"))


def setUpModule():
    Image.new("RGB", (900, 300), (200, 50, 50)).save(RAIZ / "ancha.jpg")     # 3:1
    Image.new("RGB", (400, 400), (50, 200, 50)).save(RAIZ / "cuadrada.jpg")  # 1:1
    Image.new("RGB", (300, 900), (50, 50, 200)).save(RAIZ / "vertical.jpg")  # 1:3


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


def candidatas():
    return (RAIZ / "ancha.jpg", RAIZ / "cuadrada.jpg", RAIZ / "vertical.jpg")


def rng(semilla=1):
    return random.Random(semilla)


class SinAspecto(unittest.TestCase):
    def test_es_sorteo_uniforme(self):
        # Sin hueco declarado, cada candidata debería salir con frecuencia
        # parecida a lo largo de muchos sorteos.
        conteos = {p.name: 0 for p in candidatas()}
        r = rng(3)
        for _ in range(3000):
            conteos[pool.choose(candidatas(), None, 2.0, r).name] += 1
        proporciones = [c / 3000 for c in conteos.values()]
        self.assertTrue(all(0.25 < p < 0.42 for p in proporciones), proporciones)


class ConAspecto(unittest.TestCase):
    def test_favorece_lo_que_calza_mejor(self):
        conteos = {p.name: 0 for p in candidatas()}
        r = rng(1)
        for _ in range(2000):
            conteos[pool.choose(candidatas(), 3.0, 2.0, r).name] += 1
        # ancha (ya 3:1) y vertical (1:3, pero rotada da 3:1) deben ganarle
        # por mucho a cuadrada, que pierde área sí o sí.
        self.assertGreater(conteos["ancha.jpg"], conteos["cuadrada.jpg"] * 3)
        self.assertGreater(conteos["vertical.jpg"], conteos["cuadrada.jpg"] * 3)

    def test_considera_la_rotacion(self):
        # "vertical" es 1:3, pero girada calza perfecto contra un hueco 3:1:
        # no debería salir peor calificada que "ancha", que ya es 3:1.
        conteos = {p.name: 0 for p in candidatas()}
        r = rng(2)
        for _ in range(2000):
            conteos[pool.choose(candidatas(), 3.0, 2.0, r).name] += 1
        self.assertAlmostEqual(conteos["ancha.jpg"], conteos["vertical.jpg"], delta=250)

    def test_la_peor_candidata_sigue_teniendo_oportunidad(self):
        # No es determinista: hasta la que peor calza sale alguna vez.
        conteos = {p.name: 0 for p in candidatas()}
        r = rng(4)
        for _ in range(3000):
            conteos[pool.choose(candidatas(), 3.0, 2.0, r).name] += 1
        self.assertGreater(conteos["cuadrada.jpg"], 0)

    def test_bias_alto_es_casi_determinista(self):
        conteos = {p.name: 0 for p in candidatas()}
        r = rng(5)
        for _ in range(500):
            conteos[pool.choose(candidatas(), 3.0, 12.0, r).name] += 1
        self.assertLess(conteos["cuadrada.jpg"], 5)

    def test_bias_bajo_se_acerca_a_uniforme(self):
        conteos = {p.name: 0 for p in candidatas()}
        r = rng(6)
        for _ in range(3000):
            conteos[pool.choose(candidatas(), 3.0, 0.2, r).name] += 1
        proporciones = [c / 3000 for c in conteos.values()]
        self.assertTrue(all(p > 0.15 for p in proporciones), proporciones)

    def test_es_determinista_con_la_misma_semilla(self):
        a = pool.choose(candidatas(), 3.0, 2.0, rng(9))
        b = pool.choose(candidatas(), 3.0, 2.0, rng(9))
        self.assertEqual(a, b)


class Validacion(unittest.TestCase):
    def test_pool_vacio(self):
        with self.assertRaises(SpecError):
            pool.choose((), 3.0, 2.0, rng())
        with self.assertRaises(SpecError):
            pool.choose((), None, 2.0, rng())


if __name__ == "__main__":
    unittest.main()