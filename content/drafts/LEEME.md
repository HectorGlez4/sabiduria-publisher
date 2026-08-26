# content/drafts/ — bandeja de entrada de piezas nuevas

Aquí se dejan piezas redactadas fuera de este repo (p. ej. desde un proyecto de
Cowork). **El publicador no mira esta carpeta.** `src/publish.py` solo recorre
`content/queue/`, así que nada de lo que caiga aquí sale a Facebook, Instagram
ni Threads hasta que alguien lo revise y lo mueva.

Eso es a propósito. Una pieza escrita en otro contexto no ha pasado por
`variants.preflight_separado` —verificación, fuentes, la lista de lo que no se
puede decir, la regla de no repetir tema en 90 días, la alternancia de variante
contra la última publicación REAL— y esas comprobaciones son la diferencia
entre publicar y publicar algo falso.

## Cómo se escribe una pieza aquí

Un fichero JSON por pieza, conforme a `content/schema.json`, con:

    "status": "draft"

y **sin** `publish_at` ni `results`. Las fechas se asignan al importar, contra
los huecos que de verdad estén libres.

### El `id` no puede pisar nada

El esquema obliga a `AAAA-MM-DD-(manana|tarde|noche)`, y ese id es también el
nombre del PNG y la clave del historial. Un id que ya exista en
`content/published/` **sobrescribiría una publicación real**: `2026-08-18-manana`,
por ejemplo, ya está publicado.

Usa franjas futuras y libres. Para ver cuáles:

    ls content/published content/queue | sed 's/.json//' | sort

Si dudas, escribe el id que sea y avisa: al importar se renombra. Lo que no se
puede es escribir directamente en `content/queue/`.

## Lo que no se acepta

- Piezas sin `sources`. El esquema pide mínimo una, y no es formalismo: sin
  fuente la pieza no es publicable, punto.
- Datos que "suenan bien". Si un dato circula pero está disputado, va en
  `do_not_use` con su matiz, no en `core.body`.
- Copy por plataforma. `core` se redacta una vez; el texto de Facebook, de
  Instagram y del reel lo deriva `src/variants.py`. Escribirlo a mano garantiza
  que un día digan cosas distintas.

## Qué pasa después

Se valida contra el esquema, se le pasa el preflight, se le asigna franja libre
y se hace un dry-run de cada formato. Solo entonces pasa a `content/queue/`.
