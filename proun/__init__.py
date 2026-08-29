"""Proun: generador de wallpapers tipo collage con paleta normalizada."""

from .errors import SourceError, SpecError
from .spec import Layer, Spec, build, load

__version__ = "1.0.0"
__all__ = ["Layer", "Spec", "SourceError", "SpecError", "build", "load", "__version__"]