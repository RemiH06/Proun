"""Excepciones del generador."""


class SpecError(ValueError):
    """La especificación recibida es inválida."""


class SourceError(SpecError):
    """No se pudo usar una imagen de origen."""