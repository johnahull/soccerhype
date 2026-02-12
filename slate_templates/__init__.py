# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Slate template registry.

Import a template by name::

    from slate_templates import get_template
    tpl = get_template("modern")          # returns ModernTemplate instance
    img = tpl.render_image_slate(player, intro_path)
"""

from __future__ import annotations

from .base import SlateTemplate
from .classic import ClassicTemplate
from .modern import ModernTemplate
from .bold import BoldTemplate
from .cinematic import CinematicTemplate
from .clean import CleanTemplate

# Ordered list – this order is used in the chooser GUI
_TEMPLATE_CLASSES: list[type[SlateTemplate]] = [
    ClassicTemplate,
    ModernTemplate,
    BoldTemplate,
    CinematicTemplate,
    CleanTemplate,
]

TEMPLATES: dict[str, SlateTemplate] = {cls.name: cls() for cls in _TEMPLATE_CLASSES}

DEFAULT_TEMPLATE = "classic"


def get_template(name: str | None) -> SlateTemplate:
    """Return a template instance by name, falling back to classic."""
    if name and name in TEMPLATES:
        return TEMPLATES[name]
    return TEMPLATES[DEFAULT_TEMPLATE]


def list_templates() -> list[SlateTemplate]:
    """Return all templates in display order."""
    return list(TEMPLATES.values())
