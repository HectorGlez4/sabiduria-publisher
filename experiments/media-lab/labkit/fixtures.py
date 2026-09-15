"""
Fixtures del teléfono: volcados reales podados de datos personales.

`podar` quita los nodos de otros paquetes (sistema, notificaciones, teclado) y vacía cualquier
atributo de texto que no esté en `textos` (interfaz, marca, envío, descarte) ni case con sus
patrones (fechas de miniatura, edades, recuentos, hashtags). `revisar` comprueba lo mismo sin
cambiar nada: lo usan `lab.py fixture-podar` antes de escribir y la prueba que recorre
tests/fixtures/telefono/. Un fixture nunca se edita a mano: se vuelve a volcar.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from labkit import textos

ESTRUCTURALES = frozenset({"index", "resource-id", "class", "package", "checkable", "checked", "clickable",
                           "enabled", "focusable", "focused", "scrollable", "long-clickable", "password",
                           "selected", "bounds", "drawing-order", "display-id", "visible-to-user",
                           "important-for-accessibility"})
SIEMPRE_AJENOS = ("com.android.systemui",)
CABECERA = "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"


def _raiz(xml: str) -> ET.Element:
    return ET.fromstring(xml.lstrip().encode("utf-8"))


def podar(xml: str, app: str) -> str:
    paquete = textos.PAQUETES[app]
    raiz = _raiz(xml)

    def limpiar(padre: ET.Element) -> None:
        for hijo in list(padre):
            if hijo.tag == "node":
                if hijo.get("package") != paquete:
                    padre.remove(hijo)
                    continue
                for atributo, valor in list(hijo.attrib.items()):
                    if atributo not in ESTRUCTURALES and valor and not textos.permitido(valor, app):
                        hijo.set(atributo, "")
            limpiar(hijo)

    limpiar(raiz)
    return CABECERA + ET.tostring(raiz, encoding="unicode")


def revisar(xml: str, app: str) -> list[str]:
    paquete = textos.PAQUETES[app]
    problemas = []
    for el in _raiz(xml).iter("node"):
        pkg = el.get("package", "")
        if pkg in SIEMPRE_AJENOS or pkg != paquete:
            problemas.append(f"nodo de {pkg or 'sin paquete'} en un fixture de {app} ({el.get('bounds')})")
            continue
        for atributo, valor in el.attrib.items():
            if atributo not in ESTRUCTURALES and valor and not textos.permitido(valor, app):
                problemas.append(f"{atributo}={valor[:40]!r} no está en textos.py ({el.get('bounds')})")
    return problemas
