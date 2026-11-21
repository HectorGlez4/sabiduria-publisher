"""
Qué publicaciones se salen de lo normal de SU cuenta, y qué tienen en común.

La idea viene de `ig-viral` (Jake Schincariol, instagram-agent-skill, MIT): las vistas en
bruto no son evidencia. Lo que enseña algo es el múltiplo sobre la mediana de la propia
cuenta: por encima de 3× hay señal; por debajo de 1,5× es un día normal, por grande que
parezca el número. Aquí solo está el cálculo; los datos se leen a mano y a ritmo humano
(el perfil propio o una docena de cuentas del nicho), nunca con un rastreador.

Cada fila es un dict con `vistas` (int) y, si se conocen, `cuenta` y atributos libres
(`diseno`, `autor`, `pista`…). La mediana se calcula por cuenta, sin las filas marcadas
`fijada` (un Reel fijado de otra época hunde la comparación) ni las que aún no han
madurado (`madura: False`).
"""
from __future__ import annotations

import re
import statistics

SENAL = 3.0      # a partir de aquí la pieza encontró algo
NORMAL = 1.5     # por debajo de esto no enseña nada
MINIMO = 12      # con menos filas maduras por cuenta la mediana no es fiable

_VISTAS = re.compile(r"^\s*([0-9][0-9.,]*)\s*([kKmM]?)\s*$")


def leer_vistas(texto: str) -> int:
    """«247», «1,150», «781k», «1.2M» → entero. Lo que no se entiende es un error, no un 0."""
    m = _VISTAS.match(texto or "")
    if not m:
        raise ValueError(f"vistas ilegibles: {texto!r}")
    numero, sufijo = m.group(1), m.group(2).lower()
    if sufijo:
        return round(float(numero.replace(",", ".")) * (1_000 if sufijo == "k" else 1_000_000))
    return int(re.sub(r"[.,]", "", numero))


def _cuentan(filas: list[dict]) -> list[dict]:
    return [f for f in filas if not f.get("fijada") and f.get("madura", True)]


def clasificar(filas: list[dict]) -> list[dict]:
    """Copia de las filas con `mediana`, `multiplo` y `nivel` (senal|medio|normal), de mayor a menor."""
    medianas: dict[str, float] = {}
    por_cuenta: dict[str, list[int]] = {}
    for f in _cuentan(filas):
        por_cuenta.setdefault(f.get("cuenta", ""), []).append(f["vistas"])
    for cuenta, vistas in por_cuenta.items():
        if len(vistas) < MINIMO:
            raise ValueError(f"la cuenta {cuenta or '(única)'} tiene {len(vistas)} filas maduras; "
                             f"hacen falta {MINIMO} para una mediana fiable")
        medianas[cuenta] = statistics.median(vistas)
    salida = []
    for f in _cuentan(filas):
        mediana = medianas[f.get("cuenta", "")]
        multiplo = round(f["vistas"] / mediana, 2) if mediana else 0.0
        nivel = "senal" if multiplo >= SENAL else "normal" if multiplo < NORMAL else "medio"
        salida.append({**f, "mediana": mediana, "multiplo": multiplo, "nivel": nivel})
    return sorted(salida, key=lambda f: -f["multiplo"])


def por_atributo(clasificadas: list[dict], atributo: str) -> list[dict]:
    """Por cada valor del atributo: cuántas filas, su múltiplo mediano y cuántas pasan de NORMAL.

    Ordenado por múltiplo mediano. Un valor con menos de 5 filas va marcado `pocas`: se
    enseña, pero no sostiene ninguna conclusión.
    """
    grupos: dict[str, list[float]] = {}
    for f in clasificadas:
        valor = f.get(atributo)
        if valor not in (None, ""):
            grupos.setdefault(str(valor), []).append(f["multiplo"])
    resumen = [{"valor": v, "n": len(m), "multiplo_mediano": round(statistics.median(m), 2),
                "sobre_normal": sum(1 for x in m if x >= NORMAL), "pocas": len(m) < 5}
               for v, m in grupos.items()]
    return sorted(resumen, key=lambda r: -r["multiplo_mediano"])


def tercios(clasificadas: list[dict], atributo: str) -> dict:
    """Cuántas veces sale cada valor en el tercio alto y en el bajo: lo que separa a unos de otros."""
    n = len(clasificadas) // 3
    if n == 0:
        return {"alto": {}, "bajo": {}}
    cuenta = lambda filas: {v: sum(1 for f in filas if str(f.get(atributo)) == v)
                            for v in sorted({str(f.get(atributo)) for f in filas if f.get(atributo) not in (None, "")})}
    return {"alto": cuenta(clasificadas[:n]), "bajo": cuenta(clasificadas[-n:])}
