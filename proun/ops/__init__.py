"""Operaciones sobre una capa. Cada módulo es independiente y se prueba solo.

A propósito no se importa nada aquí: `from proun.ops import crop` funciona sin
declararlo, y hacerlo obligaría a cargar Pillow y los nueve módulos aunque solo
se necesite uno. Además, un archivo faltante fallaba con un error que culpaba a
un import circular inexistente, porque Python agrega esa nota cuando el fallo
ocurre mientras el paquete se está inicializando.
"""