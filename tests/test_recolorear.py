"""Pruebas de recolorear.py: repintar un wallpaper ya exportado."""

import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import recolorear
from proun.ops import recolor

RAIZ = Path(tempfile.mkdtemp(prefix="proun-recolorear-"))


def setUpModule():
    RAIZ.mkdir(parents=True, exist_ok=True)


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


def duotono_azul(w=16, h=16):
    """Simula un wallpaper ya exportado: blanco a negro sobre el canal azul,
    como el que describe el usuario (wp_0001_3ba7ff...)."""
    grad = Image.linear_gradient("L").resize((w, h))
    return Image.merge("RGB", (grad.point(lambda v: 0), grad.point(lambda v: 0), grad))


class Recolorear(unittest.TestCase):
    def test_usa_inferno_por_defecto(self):
        salida = recolorear.recolorear(duotono_azul())
        con_colormap = recolor.apply(duotono_azul().convert("RGBA"), "#000000", {"mode": "colormap"})
        self.assertEqual(salida.convert("RGB").tobytes(), con_colormap.convert("RGB").tobytes())

    def test_respeta_un_name_explicito(self):
        salida = recolorear.recolorear(duotono_azul(), name="inferno")
        esperado = recolor.apply(duotono_azul().convert("RGBA"), "#000000",
                                 {"mode": "colormap", "name": "inferno"})
        self.assertEqual(salida.convert("RGB").tobytes(), esperado.convert("RGB").tobytes())

    def test_stops_propios(self):
        salida = recolorear.recolorear(duotono_azul(), stops=["#000000", "#ffffff"])
        esquina_oscura = salida.getpixel((0, salida.height - 1))[:3]
        esquina_clara = salida.getpixel((0, 0))[:3]
        self.assertNotEqual(esquina_oscura, esquina_clara)

    def test_conserva_el_degradado_de_tonos(self):
        # El modo colormap no deja todo plano: la esquina clara del duotono
        # azul original y la oscura tienen que seguir dando colores
        # distintos entre sí en el resultado.
        salida = recolorear.recolorear(duotono_azul())
        esquinas = {
            salida.getpixel((0, 0))[:3],
            salida.getpixel((salida.width - 1, salida.height - 1))[:3],
        }
        self.assertEqual(len(esquinas), 2)

    def test_es_determinista(self):
        una = recolorear.recolorear(duotono_azul())
        otra = recolorear.recolorear(duotono_azul())
        self.assertEqual(una.convert("RGB").tobytes(), otra.convert("RGB").tobytes())

    def test_mode_invert_da_el_negativo(self):
        salida = recolorear.recolorear(duotono_azul(), mode="invert")
        esperado = recolor.apply(duotono_azul().convert("RGBA"), "#000000", {"mode": "invert"})
        self.assertEqual(salida.convert("RGB").tobytes(), esperado.convert("RGB").tobytes())

    def test_mode_invert_ignora_name_y_stops(self):
        con_name = recolorear.recolorear(duotono_azul(), mode="invert", name="viridis")
        sin_name = recolorear.recolorear(duotono_azul(), mode="invert")
        self.assertEqual(con_name.convert("RGB").tobytes(), sin_name.convert("RGB").tobytes())


class CLI(unittest.TestCase):
    def test_guarda_con_sufijo_por_defecto(self):
        origen = RAIZ / "wp_0001_3ba7ff_123456.png"
        duotono_azul(32, 32).save(origen)
        codigo = recolorear.main([str(origen)])
        self.assertEqual(codigo, 0)
        destino = RAIZ / "wp_0001_3ba7ff_123456_inferno.png"
        self.assertTrue(destino.is_file())

    def test_respeta_out_explicito(self):
        origen = RAIZ / "otro.png"
        duotono_azul(32, 32).save(origen)
        destino = RAIZ / "elegido.png"
        codigo = recolorear.main([str(origen), "--out", str(destino)])
        self.assertEqual(codigo, 0)
        self.assertTrue(destino.is_file())

    def test_stops_da_sufijo_personalizado(self):
        origen = RAIZ / "custom.png"
        duotono_azul(32, 32).save(origen)
        codigo = recolorear.main([str(origen), "--stops", "#000000", "#ffffff"])
        self.assertEqual(codigo, 0)
        self.assertTrue((RAIZ / "custom_personalizado.png").is_file())

    def test_invert_da_sufijo_invertido(self):
        origen = RAIZ / "negativo.png"
        duotono_azul(32, 32).save(origen)
        codigo = recolorear.main([str(origen), "--invert"])
        self.assertEqual(codigo, 0)
        self.assertTrue((RAIZ / "negativo_invertido.png").is_file())

    def test_archivo_inexistente(self):
        codigo = recolorear.main([str(RAIZ / "no_existe.png")])
        self.assertEqual(codigo, 2)

    def test_name_invalido(self):
        origen = RAIZ / "malo.png"
        duotono_azul(8, 8).save(origen)
        codigo = recolorear.main([str(origen), "--name", "arcoiris"])
        self.assertEqual(codigo, 2)


if __name__ == "__main__":
    unittest.main()
