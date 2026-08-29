"""Pruebas de proun.cli."""

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from PIL import Image

from proun import cli, naming

RAIZ = Path(tempfile.mkdtemp(prefix="proun-cli-"))
FUENTES = RAIZ / "fuentes"


def setUpModule():
    FUENTES.mkdir(parents=True)
    Image.linear_gradient("L").resize((200, 200)).convert("RGB").save(FUENTES / "a.png")
    Image.new("RGB", (300, 150), (200, 60, 60)).save(FUENTES / "b.png")


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


def correr(*extra, salida=None):
    """Corre el CLI en silencio y devuelve (código, directorio de salida)."""
    destino = salida or Path(tempfile.mkdtemp(dir=RAIZ))
    argv = ["--images", str(FUENTES), "--out", str(destino), "--quiet", *extra]
    return cli.main(argv), destino


def generados(destino, ext="png"):
    return sorted(p.relative_to(destino).as_posix() for p in destino.rglob(f"*.{ext}"))


class Corrida(unittest.TestCase):
    def test_lo_minimo(self):
        codigo, destino = correr()
        self.assertEqual(codigo, 0)
        self.assertEqual(len(generados(destino)), 1)

    def test_una_carpeta_por_resolucion(self):
        codigo, destino = correr("--resolutions", "400x300", "800x600")
        self.assertEqual(codigo, 0)
        self.assertEqual(generados(destino),
                         sorted(["400x300/" + generados(destino)[0].split("/")[1],
                                 "800x600/" + generados(destino)[1].split("/")[1]]))
        self.assertEqual({p.split("/")[0] for p in generados(destino)}, {"400x300", "800x600"})

    def test_cuenta_completa(self):
        _, destino = correr("--resolutions", "200x150", "300x200",
                            "--colors", "3ba7ff", "--spectrum", "2",
                            "--count", "2", "--seed", "42")
        self.assertEqual(len(generados(destino)), 2 * 2 * 3)

    def test_nombres_legibles_por_naming(self):
        _, destino = correr("--resolutions", "200x150", "--count", "2", "--seed", "1")
        for ruta in generados(destino):
            datos = naming.parse(Path(ruta).name)
            self.assertIn(datos["index"], (1, 2))

    def test_start_index(self):
        _, destino = correr("--resolutions", "200x150", "--start-index", "50")
        self.assertEqual(naming.parse(generados(destino)[0])["index"], 50)

    def test_formato_de_salida(self):
        _, destino = correr("--resolutions", "200x150", "--format", "jpg")
        self.assertEqual(len(generados(destino, "jpg")), 1)


class Reproducibilidad(unittest.TestCase):
    def test_la_misma_semilla_da_el_mismo_archivo(self):
        args = ("--resolutions", "200x150", "--colors", "ff8800", "--seed", "77")
        _, uno = correr(*args)
        _, dos = correr(*args)
        self.assertEqual((uno / generados(uno)[0]).read_bytes(),
                         (dos / generados(dos)[0]).read_bytes())

    def test_regenerar_por_la_semilla_del_nombre(self):
        _, destino = correr("--resolutions", "200x150", "--colors", "ff8800", "--seed", "77")
        original = destino / generados(destino)[0]
        copia = original.read_bytes()
        semilla = naming.parse(original.name)["seed"]
        original.unlink()
        correr("--resolutions", "200x150", "--colors", "ff8800", "--seeds", str(semilla),
               salida=destino)
        self.assertEqual(original.read_bytes(), copia)

    def test_seeds_pisa_a_count(self):
        _, destino = correr("--resolutions", "200x150", "--count", "5", "--seeds", "123")
        self.assertEqual(len(generados(destino)), 1)
        self.assertEqual(naming.parse(generados(destino)[0])["seed"], 123)


class Existentes(unittest.TestCase):
    def test_no_sobrescribe_por_defecto(self):
        args = ("--resolutions", "160x100", "--colors", "00ff00", "--seed", "5")
        _, destino = correr(*args)
        archivo = destino / generados(destino)[0]
        marca = archivo.stat().st_mtime_ns
        correr(*args, salida=destino)
        self.assertEqual(archivo.stat().st_mtime_ns, marca)

    def test_overwrite_rehace(self):
        args = ("--resolutions", "160x100", "--colors", "00ff00", "--seed", "5")
        _, destino = correr(*args)
        archivo = destino / generados(destino)[0]
        archivo.write_bytes(b"basura")
        correr(*args, "--overwrite", salida=destino)
        self.assertNotEqual(archivo.read_bytes(), b"basura")


class DryRun(unittest.TestCase):
    def test_no_escribe_nada(self):
        _, destino = correr("--resolutions", "200x150", "--count", "3", "--dry-run")
        self.assertEqual(generados(destino), [])

    def test_lista_lo_que_haria(self):
        destino = Path(tempfile.mkdtemp(dir=RAIZ))
        salida = io.StringIO()
        with redirect_stdout(salida):
            cli.main(["--images", str(FUENTES), "--out", str(destino),
                      "--resolutions", "200x150", "--count", "2", "--dry-run"])
        self.assertIn("se generarían", salida.getvalue())
        self.assertEqual(salida.getvalue().count("wp_"), 2)


class Fusion(unittest.TestCase):
    def test_las_banderas_pisan_al_archivo(self):
        destino = Path(tempfile.mkdtemp(dir=RAIZ))
        archivo = RAIZ / "config.json"
        archivo.write_text(json.dumps({
            "sources": ["fuentes/a.png"],
            "resolutions": ["800x600"],
            "colors": ["#ff0000"],
        }), encoding="utf-8")
        codigo = cli.main(["--spec", str(archivo), "--out", str(destino),
                           "--resolutions", "200x150", "--quiet"])
        self.assertEqual(codigo, 0)
        self.assertTrue(generados(destino)[0].startswith("200x150/"))
        self.assertIn("ff0000", generados(destino)[0])

    def test_solo_archivo(self):
        destino = Path(tempfile.mkdtemp(dir=RAIZ))
        archivo = RAIZ / "solo.json"
        archivo.write_text(json.dumps({
            "sources": ["fuentes"], "resolutions": ["200x150"], "output": str(destino),
        }), encoding="utf-8")
        self.assertEqual(cli.main(["--spec", str(archivo), "--quiet"]), 0)
        self.assertEqual(len(generados(destino)), 1)

    def test_no_tones_apaga_la_normalizacion(self):
        datos = cli.to_data(cli.parse_args(["--images", str(FUENTES), "--no-tones"]))
        self.assertIs(datos["defaults"]["tones"], False)

    def test_mode_y_strength_van_a_recolor(self):
        datos = cli.to_data(cli.parse_args(
            ["--images", str(FUENTES), "--mode", "tint", "--strength", "0.5"]))
        self.assertEqual(datos["defaults"]["recolor"], {"mode": "tint", "strength": 0.5})

    def test_background_none(self):
        datos = cli.to_data(cli.parse_args(["--images", str(FUENTES), "--background", "none"]))
        self.assertIsNone(datos["background"])

    def test_layers_en_sus_dos_formas(self):
        self.assertEqual(cli._layers("5"), 5)
        self.assertEqual(cli._layers("3-8"), {"min": 3, "max": 8})


class Errores(unittest.TestCase):
    def silencioso(self, argv):
        error = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(error):
            codigo = cli.main(argv)
        return codigo, error.getvalue()

    def test_sin_imagenes(self):
        codigo, error = self.silencioso(["--out", str(RAIZ / "vacio"), "--quiet"])
        self.assertEqual(codigo, 2)
        self.assertIn("imágenes", error)

    def test_resolucion_invalida(self):
        codigo, error = self.silencioso(
            ["--images", str(FUENTES), "--resolutions", "grande", "--quiet"])
        self.assertEqual(codigo, 2)
        self.assertIn("error:", error)

    def test_color_invalido(self):
        codigo, _ = self.silencioso(
            ["--images", str(FUENTES), "--colors", "azulito", "--quiet"])
        self.assertEqual(codigo, 2)

    def test_layers_mal_escrito(self):
        codigo, _ = self.silencioso(
            ["--images", str(FUENTES), "--layers", "tres-ocho", "--quiet"])
        self.assertEqual(codigo, 2)

    def test_archivo_de_especificacion_inexistente(self):
        codigo, _ = self.silencioso(["--spec", str(RAIZ / "fantasma.json"), "--quiet"])
        self.assertEqual(codigo, 2)

    def test_no_escribe_nada_si_la_especificacion_falla(self):
        destino = Path(tempfile.mkdtemp(dir=RAIZ))
        self.silencioso(["--images", str(FUENTES), "--out", str(destino),
                         "--resolutions", "grande", "--quiet"])
        self.assertFalse(destino.exists() and any(destino.iterdir()))


if __name__ == "__main__":
    unittest.main()