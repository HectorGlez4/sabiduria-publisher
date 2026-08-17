# Cómo generar una pieza nueva

Para las tareas programadas que investigan y redactan. Sustituye al formato de
prosa en markdown.

## La división del trabajo

Tú produces **solo contenido verificado**. No calculas turno, ni hora, ni
variante de tarjeta: eso lo hace `scripts/programar.py`, que es determinista.

La razón es concreta. La alternancia `cream`/`gold` se calcula contra la
**última publicación real**, no contra la entrada anterior de la cola, y ya se
calculó mal una vez: hubo que reescribir 39 entradas para arreglarlo. Llevar esa
cuenta a mano es un error esperando a ocurrir. Un contador determinista no se
equivoca y no se cansa.

Lo mismo con el turno y el jitter de 5-50 minutos: el script busca el primer
hueco futuro libre y lo calcula.

## Lo que entregas

Un JSON con estos campos, y ninguno más:

```json
{
  "pillar": "figura | cita | civilizacion | filosofia | curiosidad | arte-ciencia",
  "core": {
    "subject": "Tema, para el control anti-repetición. Específico.",
    "hook": "La promesa en una línea. Es lo único que se ve antes del corte.",
    "body": ["El hecho con cifras.", "El giro.", "Qué significa hoy."],
    "question": "¿Una sola pregunta abierta y breve?",
    "quote": {
      "text": "Solo para el pilar 'cita'.",
      "author": "Nombre",
      "work": "Obra y referencia",
      "attribution_verified": true
    }
  },
  "card": {
    "renderer": "text_card | quote_card",
    "title": "SOLO text_card. En versalitas.",
    "subtitle": "SOLO text_card. No puede repetir literalmente el hook.",
    "body": "SOLO text_card. Máximo 300 caracteres."
  },
  "tags": {
    "primary": "#SabiduriaDeBolsillo",
    "topic": ["2-4 específicas del tema; son las que van a Facebook"],
    "extended": ["las adicionales hasta 8-12 para Instagram"]
  },
  "sources": [
    {"claim": "Qué se comprobó exactamente", "source": "Dónde", "url": "opcional"}
  ],
  "do_not_use": [
    "Cada dato falso o disputado que circula sobre este tema, con el porqué."
  ]
}
```

Después:

```bash
python3 scripts/programar.py borrador.json --dry-run   # enseña qué haría
python3 scripts/programar.py borrador.json             # lo mete en la cola
```

El script rechaza la pieza si no pasa las comprobaciones previas, y dice cuál
falló.

## Reglas que el código hace cumplir

No hace falta que las vigiles, pero saberlas evita que te rechacen la pieza:

- **Ninguna cita sin `attribution_verified`.** Es el peor error posible en esta
  página.
- Al menos una fuente. Sin verificación no se publica.
- Máximo 5 etiquetas en Facebook, 8-12 en Instagram. Prohibidas `#viral`,
  `#parati`, `#follow4follow`, `#sigueme`, `#f4f`.
- El subtítulo de la tarjeta no puede repetir literalmente el gancho.
- Cuerpo de tarjeta, máximo 300 caracteres.
- Sin repetir tema ni cita de los últimos 90 días.
- Máximo 3 al día, mínimo 4 horas entre publicaciones.

## `do_not_use` no es opcional

Guarda los datos falsos que circulan sobre el tema: la fortuna inventada de
Mansa Musa, el "solo sé que no sé nada" que Sócrates nunca dijo, la frase de
Policarpa que escribió un presidente cuarenta años después.

Es memoria institucional. Impide que una sesión futura reintroduzca un error ya
cazado, y en las 41 piezas migradas hay 150 entradas acumuladas. Si al
investigar descartas una versión, anótala aquí con el motivo: el descarte vale
tanto como el dato.

## Voz

Español neutro latinoamericano. Reposado, respetuoso, ligeramente solemne.
Sabiduría, no *coaching*. Frases cortas. Cero emojis. Ningún modismo de España.
El dato concreto —fecha, cifra, nombre— es lo que da autoridad: siempre al menos
uno. Cerrar con una pregunta abierta, nunca pidiendo comentarios ni compartidos.
