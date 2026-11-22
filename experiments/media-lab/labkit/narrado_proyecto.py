"""
Generador del proyecto HyperFrames de un reel narrado.

`html` convierte un guion validado y su línea de tiempo en una sola página (HTML/CSS más una línea de
tiempo GSAP en pausa) que `hyperframes render` convierte en vídeo de 1080×1920. `escribir` deja el
proyecto en disco con la voz, las fuentes y GSAP como archivos locales: al renderizar no hay red.
Todo es determinista: sin `Date.now()`, sin `Math.random()`.

La pantalla sale solo de `pantalla`, nunca de `voz`. El movimiento se limita a fundidos, subidas de
40 px como máximo y un único cambio de fondo (la escena `contraste`).
"""
from __future__ import annotations

import json
import shutil
from html import escape
from pathlib import Path

RAIZ_LAB = Path(__file__).resolve().parent.parent
RAIZ_REPO = RAIZ_LAB.parent.parent
PLANTILLA = RAIZ_LAB / "narrados" / "plantilla"
FUENTES = RAIZ_REPO / "assets" / "fonts"
ARCHIVOS_FUENTES = ("Lora-Variable.ttf", "Lora-Italic-Variable.ttf",
                    "Poppins-Medium.ttf", "Poppins-Light.ttf")

CITA_MAX_GRANDE = 70     # hasta aquí la cita va a 84 px
CITA_MAX = 200           # más largo no cabe
CITA_PX_GRANDE = 84
CITA_PX_MINIMO = 56
SALIDA = 0.3             # duración del fundido de salida de cada escena


class NoCabe(Exception):
    """Un texto de la pantalla es demasiado largo para su caja."""

    def __init__(self, campo: str, n_caracteres: int, maximo: int = CITA_MAX, escena: int | None = None):
        self.campo = campo
        self.n_caracteres = n_caracteres
        self.maximo = maximo
        self.escena = escena
        super().__init__(campo, n_caracteres)

    def __str__(self) -> str:
        donde = f" en la escena {self.escena}" if self.escena else ""
        return (f"«{self.campo}»{donde} no cabe en pantalla: {self.n_caracteres} caracteres "
                f"(máximo {self.maximo})")


def tamano_cita(texto: str) -> int:
    """84 px hasta 70 caracteres; baja linealmente hasta 56 px a los 200. Más largo: NoCabe."""
    n = len(texto)
    if n > CITA_MAX:
        raise NoCabe("cita", n, CITA_MAX)
    if n <= CITA_MAX_GRANDE:
        return CITA_PX_GRANDE
    paso = (CITA_PX_GRANDE - CITA_PX_MINIMO) * (n - CITA_MAX_GRANDE) / (CITA_MAX - CITA_MAX_GRANDE)
    return round(CITA_PX_GRANDE - paso)


def _disenos() -> dict:
    return json.loads((PLANTILLA / "disenos.json").read_text(encoding="utf-8"))


def _n(x: float) -> str:
    """Número para HTML/JS: 3 decimales como máximo, sin ceros sobrantes."""
    return f"{round(x, 3):g}"


def _txt(s: str) -> str:
    """Texto de pantalla: escapado, y el salto de línea pasa a <br />."""
    return escape(s, quote=True).replace("\n", "<br />")


# ── escenas: marcado ────────────────────────────────────────────────────────────────────────

def _marcado_tachado(i: int, p: dict, t: dict, d: dict) -> str:
    return (f'<div class="et" id="s{i}a">{_txt(p["etiqueta"])}</div>\n'
            f'        <div id="s{i}t" class="tachado grande"><span id="s{i}b">{_txt(p["nombre"])}</span>'
            f'<span class="raya" id="s{i}r"></span></div>')


def _marcado_cita(i: int, p: dict, t: dict, d: dict) -> str:
    palabras = " ".join(f'<span class="p">{_txt(w)}</span>' for w in p["texto"].split())
    try:
        px = tamano_cita(p["texto"])
    except NoCabe as e:
        raise NoCabe(e.campo, e.n_caracteres, e.maximo, escena=i + 1) from None
    return (f'<div class="comilla" id="s{i}q">“</div>\n'
            f'        <div class="cita" id="s{i}c" style="font-size:{px}px">{palabras}</div>')


def _marcado_nombre_ano(i: int, p: dict, t: dict, d: dict) -> str:
    nota = (f'\n        <div class="nota" id="s{i}e" style="margin-top:40px">{_txt(p["nota"])}</div>'
            if p.get("nota") else "")
    return (f'<div class="et" id="s{i}a">{_txt(p["etiqueta"])}</div>\n'
            f'        <div class="grande" id="s{i}b" style="margin-top:28px">{_txt(p["nombre"])}</div>\n'
            f'        <div class="filete" id="s{i}f"></div>\n'
            f'        <div class="ano" id="s{i}y">{_txt(p["ano"])}</div>{nota}')


def _marcado_contraste(i: int, p: dict, t: dict, d: dict) -> str:
    return (f'<div class="grande" id="s{i}a">{_txt(p["claro"])}</div>\n'
            f'        <div class="filete" id="s{i}f"></div>\n'
            f'        <div class="grande noche-tinta" id="s{i}b">{_txt(p["oscuro"])}</div>')


def _marcado_texto(i: int, p: dict, t: dict, d: dict) -> str:
    return f'<div class="texto" id="s{i}a">{_txt(p["texto"])}</div>'


def _marcado_pregunta(i: int, p: dict, t: dict, d: dict) -> str:
    return f'<div class="pregunta" id="s{i}a">{_txt(p["texto"])}</div>'


# ── escenas: GSAP ──────────────────────────────────────────────────────────────────────────

def _gsap_tachado(i: int, p: dict, t: dict, d: dict, palabras) -> list[str]:
    t0, dur = t["inicio"], t["fin"] - t["inicio"]
    lineas = [f'tl.fromTo("#s{i}r", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.45, ease: "power2.inOut" }}, '
              f'{_n(t0 + 0.8 * dur)});']
    if i > 0:  # en la primera escena el nombre ya está en pantalla: es la portada
        lineas.insert(0, f'sube("#s{i}b", {_n(t0 + 0.55 * dur)});')
    return lineas


def _gsap_cita(i: int, p: dict, t: dict, d: dict, palabras) -> list[str]:
    if i == 0:  # portada: la cita entera visible desde el primer fotograma
        return []
    n = len(p["texto"].split())
    if not palabras or len(palabras) != n:
        paso = (t["fin"] - t["inicio"]) / n
        palabras = [t["inicio"] + k * paso for k in range(n)]
    lista = ", ".join(_n(x) for x in palabras)
    lineas = [f'const palabras{i} = [{lista}];',
              f'document.querySelectorAll("#s{i}c .p").forEach((p, k) =>',
              f'  tl.fromTo(p, {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }}, '
              f'palabras{i}[k]));']
    if i > 0:
        lineas.insert(0, f'tl.fromTo("#s{i}q", {{ opacity: 0, y: 24 }}, '
                         f'{{ opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }}, '
                         f'{_n(max(t["escena_desde"], palabras[0] - 0.15))});')
    return lineas


def _gsap_nombre_ano(i: int, p: dict, t: dict, d: dict, palabras) -> list[str]:
    t0, dur = t["inicio"], t["fin"] - t["inicio"]
    filete = f'tl.fromTo("#s{i}f", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {_n(t0 + 0.3 * dur)});'
    if i == 0:  # portada: todo el texto ya está en pantalla; solo el filete entra
        return [filete]
    lineas = [f'sube("#s{i}a", {_n(t0)});',
              f'sube("#s{i}b", {_n(t0 + 0.12 * dur)});',
              filete,
              f'sube("#s{i}y", {_n(t0 + 0.38 * dur)}, 0.6);']
    if p.get("nota"):
        lineas.append(f'sube("#s{i}e", {_n(t0 + 0.7 * dur)});')
    return lineas


def _gsap_contraste(i: int, p: dict, t: dict, d: dict, palabras) -> list[str]:
    t0, dur = t["inicio"], t["fin"] - t["inicio"]
    giro = t0 + 0.5 * dur
    lineas = [f'sube("#s{i}a", {_n(t0)});',
              f'tl.to("#noche", {{ opacity: 1, duration: 0.7, ease: "power2.inOut" }}, {_n(giro)});',
              f'tl.to("#s{i}a", {{ color: "{d["giro"]}", duration: 0.7 }}, {_n(giro)});',
              f'tl.fromTo("#s{i}f", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {_n(giro + 0.1)});',
              f'sube("#s{i}b", {_n(giro + 0.3)}, 0.6);',
              f'tl.to("#noche", {{ opacity: 0, duration: 0.5 }}, {_n(t["escena_hasta"] - SALIDA)});']
    if i == 0:  # portada: sin entradas de texto (el giro de color y de fondo se conserva)
        lineas = [l for l in lineas if not l.startswith("sube(")]
    return lineas


def _gsap_texto(i: int, p: dict, t: dict, d: dict, palabras) -> list[str]:
    if i == 0:  # portada: el texto ya está en pantalla en el primer fotograma
        return []
    return [f'sube("#s{i}a", {_n(t["inicio"])}, 0.6);']


def _gsap_pregunta(i: int, p: dict, t: dict, d: dict, palabras) -> list[str]:
    t0 = t["inicio"]
    if i == 0:  # portada: texto, firma y aviso ya están en pantalla en el primer fotograma
        return []
    return [f'sube("#s{i}a", {_n(t0)}, 0.6);',
            f'sube("#firma", {_n(t0 + 1.2)});',
            f'sube("#aviso", {_n(t0 + 1.5)});']


ESCENAS = {
    "tachado": (_marcado_tachado, _gsap_tachado),
    "cita": (_marcado_cita, _gsap_cita),
    "nombre_ano": (_marcado_nombre_ano, _gsap_nombre_ano),
    "texto": (_marcado_texto, _gsap_texto),
    "contraste": (_marcado_contraste, _gsap_contraste),
    "pregunta": (_marcado_pregunta, _gsap_pregunta),
}


def _seccion(i: int, escena: dict, t: dict, d: dict) -> str:
    marcado = ESCENAS[escena["tipo"]][0](i, escena["pantalla"], t, d)
    es_ultima = escena["tipo"] == "pregunta"
    cierre = ('\n        <div id="firma">Sabiduría de Bolsillo</div>\n'
              '        <div id="aviso">Voz sintética</div>' if es_ultima else "")
    return (f'      <section id="e{i}" class="clip" data-start="{_n(t["escena_desde"])}" '
            f'data-duration="{_n(t["escena_hasta"] - t["escena_desde"])}" data-track-index="0">'
            f'<div class="caja">\n        {marcado}\n      </div>{cierre}</section>')


def _animaciones(i: int, escena: dict, t: dict, d: dict, palabras, ultima: bool) -> str:
    lineas = [f'// {i + 1} · {escena["tipo"]}'] + ESCENAS[escena["tipo"]][1](i, escena["pantalla"], t, d, palabras)
    if not ultima:
        lineas.append(f'sale("#e{i} .caja", {_n(t["escena_hasta"] - SALIDA)});')
    return "\n      ".join(lineas)


def _css(d: dict) -> str:
    return f"""
      @font-face {{ font-family: "Lora"; src: url("assets/Lora-Variable.ttf"); font-weight: 400 700; }}
      @font-face {{ font-family: "Lora"; font-style: italic; src: url("assets/Lora-Italic-Variable.ttf"); font-weight: 400 700; }}
      @font-face {{ font-family: "Poppins"; src: url("assets/Poppins-Medium.ttf"); font-weight: 500; }}
      @font-face {{ font-family: "Poppins"; src: url("assets/Poppins-Light.ttf"); font-weight: 300; }}
      :root {{ --fondo: {d["fondo"]}; --fondo2: {d["fondo2"]}; --tinta: {d["tinta"]}; --etiqueta: {d["etiqueta"]};
        --filete: {d["filete"]}; --noche: {d["noche"]}; --noche-tinta: {d["noche_tinta"]}; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: var(--fondo); }}
      #root {{ position: relative; width: 1080px; height: 1920px; color: var(--tinta); font-family: "Lora", serif; }}
      #fondo {{ position: absolute; inset: 0; background: linear-gradient(var(--fondo), var(--fondo2)); }}
      #noche {{ position: absolute; inset: 0; background: var(--noche); opacity: 0; }}
      .clip {{ position: absolute; inset: 0; }}
      /* zona segura común de TikTok, Reels y Shorts (las reglas de `hyperframes check`): x 120–780, y 288–1248 */
      .caja {{ position: absolute; left: 120px; right: 300px; top: 288px; height: 960px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
      .et {{ font-family: "Poppins"; font-weight: 500; font-size: 34px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--etiqueta); }}
      .grande {{ font-size: 92px; font-weight: 600; line-height: 1.1; }}
      .ano {{ font-family: "Poppins"; font-weight: 500; font-size: 250px; line-height: 1; color: var(--etiqueta); letter-spacing: -0.03em; }}
      .nota {{ font-style: italic; font-size: 52px; line-height: 1.3; }}
      .texto {{ font-size: 76px; font-weight: 500; line-height: 1.22; }}
      .filete {{ width: 160px; height: 4px; background: var(--filete); margin: 48px 0; transform-origin: center; }}
      .tachado {{ position: relative; display: inline-block; margin-top: 36px; }}
      .raya {{ position: absolute; left: -24px; right: -24px; top: 54%; height: 10px; background: var(--etiqueta); transform-origin: left center; }}
      .cita {{ font-weight: 500; line-height: 1.22; }}
      .cita .p {{ display: inline-block; }}
      .comilla {{ font-size: 260px; line-height: 0.6; color: var(--filete); height: 150px; }}
      .noche-tinta {{ color: var(--noche-tinta); }}
      .pregunta {{ font-size: 96px; font-weight: 600; line-height: 1.15; }}
      #firma {{ position: absolute; left: 120px; right: 300px; top: 1120px; text-align: center; font-family: "Poppins"; font-weight: 500; font-size: 32px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--etiqueta); }}
      #aviso {{ position: absolute; left: 120px; right: 300px; top: 1175px; text-align: center; font-family: "Poppins"; font-weight: 500; font-size: 28px; color: var(--etiqueta); }}
    """


def html(guion: dict, tiempos: list[dict], total: float, palabras: list[float] | None) -> str:
    """La página completa del reel. Pura: mismo guion y mismos tiempos, mismo HTML."""
    disenos = _disenos()
    nombre = guion.get("diseno")
    if nombre not in disenos:
        raise ValueError(f"diseño desconocido: {nombre!r} (hay {', '.join(sorted(disenos))})")
    escenas = guion["escenas"]
    if len(tiempos) != len(escenas):
        raise ValueError(f"{len(escenas)} escenas y {len(tiempos)} tiempos: deben coincidir")
    for e in escenas:
        if e["tipo"] not in ESCENAS:
            raise ValueError(f"tipo de escena desconocido: {e['tipo']!r}")
    d = disenos[nombre]
    secciones = "\n\n".join(_seccion(i, e, t, d) for i, (e, t) in enumerate(zip(escenas, tiempos)))
    ultima = len(escenas) - 1
    animaciones = "\n\n      ".join(_animaciones(i, e, t, d, palabras, i == ultima)
                                   for i, (e, t) in enumerate(zip(escenas, tiempos)))
    return f"""<!doctype html>
<html lang="es" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/gsap.min.js"></script>
    <style>{_css(d)}</style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{_n(total)}" data-width="1080" data-height="1920">
      <div id="fondo"></div>
      <div id="noche"></div>

{secciones}

      <audio id="voz" src="assets/voz.wav" data-start="0" data-duration="{_n(total)}" data-track-index="1"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      const sube = (sel, t, d = 0.5) => tl.fromTo(sel, {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: d, ease: "power3.out" }}, t);
      const sale = (sel, t) => tl.to(sel, {{ opacity: 0, duration: {SALIDA}, ease: "power1.in" }}, t);

      {animaciones}

      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def escribir(destino: Path, guion: dict, tiempos: list[dict], total: float, palabras, voz: Path) -> Path:
    """Escribe el proyecto en `destino` (sobrescribe si existe) y lo devuelve."""
    destino = Path(destino)
    assets = destino / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    pagina = html(guion, tiempos, total, palabras)
    (destino / "index.html").write_text(pagina, encoding="utf-8")
    (destino / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
    }, indent=2) + "\n", encoding="utf-8")
    (destino / "meta.json").write_text(json.dumps(
        {"id": guion["pieza"], "name": guion["pieza"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for nombre in ARCHIVOS_FUENTES:
        shutil.copyfile(FUENTES / nombre, assets / nombre)
    shutil.copyfile(PLANTILLA / "gsap.min.js", assets / "gsap.min.js")
    shutil.copyfile(voz, assets / "voz.wav")
    return destino
