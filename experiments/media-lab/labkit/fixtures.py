"""
Fixtures del teléfono: volcados reales podados de datos personales.

`podar` quita los nodos de otros paquetes (sistema, notificaciones, teclado) y cualquier elemento que no sea
`<hierarchy>` ni `<node>`, y vacía cualquier atributo de texto que no esté en `textos` (interfaz, marca, envío,
descarte) ni case con sus patrones de fixture (fechas de miniatura, edades cortas, recuentos y, solo en `text`,
hashtags), y cualquier `resource-id` que no sea un id limpio del paquete de la app. `revisar` comprueba lo mismo
sin cambiar nada: lo usan `lab.py fixture-podar` antes de escribir y la prueba que recorre
tests/fixtures/telefono/. Un fixture nunca se edita a mano: se vuelve a volcar.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from labkit import textos

ESTRUCTURALES = frozenset({"index", "class", "package", "checkable", "checked", "clickable",
                           "enabled", "focusable", "focused", "scrollable", "long-clickable", "password",
                           "selected", "bounds", "drawing-order", "display-id", "visible-to-user",
                           "important-for-accessibility"})
CABECERA = "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
_RID = re.compile(r"[a-z0-9_.]+:id/[a-z0-9_]+")


def _raiz(xml: str) -> ET.Element:
    """Lanza `xml.etree.ElementTree.ParseError` si el volcado no es XML legible."""
    return ET.fromstring(xml.lstrip().encode("utf-8"))


def _valor_permitido(atributo: str, valor: str, app: str, paquete: str) -> bool:
    if atributo in ESTRUCTURALES or not valor:
        return True
    if atributo == "resource-id":
        return bool(_RID.fullmatch(valor)) and valor.startswith(f"{paquete}:id/")
    return textos.permitido(valor, app, atributo)


def podar(xml: str, app: str) -> str:
    paquete = textos.PAQUETES[app]
    raiz = _raiz(xml)

    def limpiar(padre: ET.Element) -> None:
        padre.text = None
        for hijo in list(padre):
            if hijo.tag != "node" or hijo.get("package") != paquete:
                padre.remove(hijo)
                continue
            hijo.tail = None
            for atributo, valor in list(hijo.attrib.items()):
                if not _valor_permitido(atributo, valor, app, paquete):
                    hijo.set(atributo, "")
            limpiar(hijo)

    limpiar(raiz)
    return CABECERA + ET.tostring(raiz, encoding="unicode")


def revisar(xml: str, app: str) -> list[str]:
    paquete = textos.PAQUETES[app]
    raiz = _raiz(xml)
    problemas = []
    if raiz.tag != "hierarchy":
        problemas.append(f"la raíz es <{raiz.tag}>, no <hierarchy>")
    for el in raiz.iter():
        if (el.text or "").strip() or (el.tail or "").strip():
            problemas.append(f"texto suelto dentro o detrás de <{el.tag}> ({el.get('bounds')})")
        if el is raiz:
            continue
        if el.tag != "node":
            problemas.append(f"elemento <{el.tag}> que uiautomator no escribe")
            continue
        pkg = el.get("package", "")
        if pkg != paquete:
            problemas.append(f"nodo de {pkg or 'sin paquete'} en un fixture de {app} ({el.get('bounds')})")
            continue
        for atributo, valor in el.attrib.items():
            if not _valor_permitido(atributo, valor, app, paquete):
                problemas.append(f"{atributo}={valor[:40]!r} no está en textos.py ({el.get('bounds')})")
    return problemas


def vacio(xml: str, app: str) -> str | None:
    """Por qué el volcado podado no sirve como fixture de `app` (ningún nodo de su paquete, o ningún texto de la
    tabla: suele ser un volcado de otra app), o None si sirve."""
    paquete = textos.PAQUETES[app]
    conocidos = textos.conocidos(app)
    nodos = [el for el in _raiz(xml).iter("node") if el.get("package") == paquete]
    if not nodos:
        return f"el volcado podado no tiene ningún nodo de {paquete}: ¿es de otra app?"
    if not any(v and v in conocidos for el in nodos for v in (el.get("text"), el.get("content-desc"))):
        return f"el volcado podado no tiene ningún texto conocido de {app} ({paquete}): ¿es de otra app?"
    return None
