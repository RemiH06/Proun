"""Lo que publica docs/: specs reproducibles y enlaces locales que existen."""

import importlib.util
import re
import unittest
from pathlib import Path

from proun import spec

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"


@unittest.skipUnless((RAIZ / "fuentes").is_dir(), "fuentes/ no se versiona")
class SpecsDelRepo(unittest.TestCase):
    def test_cada_spec_de_json_construye(self):
        # filtros.json es de calendario.py, no un spec completo
        for ruta in sorted((RAIZ / "json").glob("*.json")):
            if ruta.name == "filtros.json":
                continue
            with self.subTest(ruta.name):
                spec.build(spec.load(ruta))


class EnlacesDeLaLanding(unittest.TestCase):
    def test_cada_ruta_local_existe(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        rutas = set()
        for atributo in re.findall(r'(?:src|href|srcset)="([^"]+)"', html):
            for parte in atributo.split(","):
                ruta = parte.strip().split(" ")[0]
                if ruta and not re.match(r"(https?:|mailto:|#|data:)", ruta):
                    rutas.add(ruta)
        self.assertTrue(rutas)
        faltan = sorted(r for r in rutas if not (DOCS / r).exists())
        self.assertEqual(faltan, [])

    def test_las_obras_que_cuelgan_las_genera_obras_py(self):
        modulo = importlib.util.spec_from_file_location("obras", DOCS / "obras.py")
        obras = importlib.util.module_from_spec(modulo)
        modulo.loader.exec_module(obras)
        generadas = (set(obras.OBRAS) - obras.SIN_EXHIBIR) | set(obras.DERIVADAS)
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        colgadas = set(re.findall(r"images/obras/([a-z_]+)-\d+\.webp", html))
        self.assertTrue(colgadas)
        self.assertEqual(sorted(colgadas - generadas), [])


if __name__ == "__main__":
    unittest.main()
