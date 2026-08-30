"""Pruebas de proun.cleanup."""

import shutil
import tempfile
import unittest
from pathlib import Path

from proun import cleanup, naming
from proun.errors import SpecError

RAIZ = Path(tempfile.mkdtemp(prefix="proun-clean-"))


def poblar(destino: Path):
    """Un directorio de salida típico: dos resoluciones, dos colores, dos semillas."""
    for resolucion in ("320x200", "400x300"):
        carpeta = destino / resolucion
        carpeta.mkdir(parents=True, exist_ok=True)
        for indice, semilla in enumerate((111, 222), start=1):
            for color in ("ff0000", "00ff00"):
                (carpeta / naming.filename(indice, color, semilla)).write_bytes(b"x")
    return destino


def nuevo():
    return poblar(Path(tempfile.mkdtemp(dir=RAIZ)))


def tearDownModule():
    shutil.rmtree(RAIZ, ignore_errors=True)


class Busqueda(unittest.TestCase):
    def test_sin_filtros_los_encuentra_todos(self):
        self.assertEqual(len(cleanup.find(nuevo())), 8)

    def test_por_resolucion(self):
        encontrados = cleanup.find(nuevo(), resolutions=[(320, 200)])
        self.assertEqual(len(encontrados), 4)
        self.assertTrue(all(p.parent.name == "320x200" for p in encontrados))

    def test_por_color(self):
        encontrados = cleanup.find(nuevo(), palette=["#ff0000"])
        self.assertEqual(len(encontrados), 4)
        self.assertTrue(all("ff0000" in p.name for p in encontrados))

    def test_el_color_se_normaliza(self):
        for entrada in ("#ff0000", "FF0000", "f00", [255, 0, 0]):
            self.assertEqual(len(cleanup.find(nuevo(), palette=[entrada])), 4, entrada)

    def test_por_semilla(self):
        encontrados = cleanup.find(nuevo(), seeds=[111])
        self.assertEqual(len(encontrados), 4)
        self.assertTrue(all(naming.parse(p.name)["seed"] == 111 for p in encontrados))

    def test_los_filtros_se_combinan(self):
        encontrados = cleanup.find(nuevo(), resolutions=[(320, 200)],
                                   palette=["#ff0000"], seeds=[111])
        self.assertEqual(len(encontrados), 1)

    def test_filtro_sin_coincidencias(self):
        self.assertEqual(cleanup.find(nuevo(), seeds=[999]), [])

    def test_ignora_archivos_ajenos(self):
        destino = nuevo()
        (destino / "notas.txt").write_text("hola", encoding="utf-8")
        (destino / "320x200" / "captura.png").write_bytes(b"x")
        (destino / "320x200" / "wp_mal_puesto.png").write_bytes(b"x")
        encontrados = cleanup.find(destino)
        # Los nombres se repiten entre carpetas de resolución, así que se
        # cuentan rutas, no nombres.
        self.assertEqual(len(encontrados), 8)
        self.assertNotIn("captura.png", {p.name for p in encontrados})
        self.assertNotIn("notas.txt", {p.name for p in encontrados})

    def test_directorio_inexistente(self):
        self.assertEqual(cleanup.find(RAIZ / "fantasma"), [])

    def test_directorio_vacio(self):
        vacio = Path(tempfile.mkdtemp(dir=RAIZ))
        self.assertEqual(cleanup.find(vacio), [])


class Borrado(unittest.TestCase):
    def test_borra_lo_que_recibe(self):
        destino = nuevo()
        objetivo = cleanup.find(destino, palette=["#ff0000"])
        self.assertEqual(cleanup.remove(objetivo, destino), 4)
        self.assertEqual(len(cleanup.find(destino)), 4)

    def test_no_toca_lo_ajeno(self):
        destino = nuevo()
        ajeno = destino / "notas.txt"
        ajeno.write_text("hola", encoding="utf-8")
        cleanup.remove(cleanup.find(destino), destino)
        self.assertTrue(ajeno.is_file())

    def test_quita_directorios_que_quedan_vacios(self):
        destino = nuevo()
        cleanup.remove(cleanup.find(destino, resolutions=[(320, 200)]), destino)
        self.assertFalse((destino / "320x200").exists())
        self.assertTrue((destino / "400x300").is_dir())

    def test_conserva_la_raiz(self):
        destino = nuevo()
        cleanup.remove(cleanup.find(destino), destino)
        self.assertTrue(destino.is_dir())

    def test_conserva_directorios_con_algo_dentro(self):
        destino = nuevo()
        (destino / "320x200" / "captura.png").write_bytes(b"x")
        cleanup.remove(cleanup.find(destino), destino)
        self.assertTrue((destino / "320x200").is_dir())

    def test_lista_vacia(self):
        destino = nuevo()
        self.assertEqual(cleanup.remove([], destino), 0)
        self.assertEqual(len(cleanup.find(destino)), 8)

    def test_archivo_que_ya_no_esta(self):
        destino = nuevo()
        objetivo = cleanup.find(destino)
        objetivo[0].unlink()
        with self.assertRaises(SpecError):
            cleanup.remove(objetivo, destino)


if __name__ == "__main__":
    unittest.main()