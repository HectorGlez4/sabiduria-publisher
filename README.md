# Sabiduría De Bolsillo — publicador multiplataforma

Una investigación verificada entra. Cinco textos y una imagen salen. Se publican solos.

Sustituye al montaje anterior, donde tres tareas en la nube preparaban contenido
en un documento de prosa y **nadie lo publicaba**: entre el 10 y el 17 de agosto
de 2026 se acumularon 39 piezas listas y solo salieron cinco, todas a mano.

---

## Por qué existe

El problema nunca fue generar contenido. Las tareas programadas investigaban,
verificaban fuentes y redactaban sin fallar un solo día. El problema era el
último paso: **una sesión en la nube no puede alcanzar el navegador del usuario**,
así que la publicación exigía a una persona con Chrome abierto tres veces al día.

Este repo elimina esa dependencia usando la Graph API, que es la vía oficial de
Meta para publicar sin un humano delante, y GitHub Actions como reloj.

Diferencias de fondo con el sistema anterior:

| Antes | Ahora |
|---|---|
| La cola era prosa en markdown | La cola son datos con esquema validado |
| Copy escrito a mano por red | Un solo contenido canónico → variantes derivadas |
| Reconciliación manual cada lunes | Una pieza publicada se mueve sola de directorio |
| Publicar exigía tu Mac encendido | Corre en los servidores de GitHub |
| El token no tenía dónde vivir | Secrets cifrados de Actions |
| Un clic mal puesto podía activar promoción de pago | La API no expone esa superficie |

---

## Cómo está montado

```
content/
  schema.json          Contrato de la unidad de contenido
  queue/*.json         Pendiente. Un archivo por pieza
  published/*.json     Publicado, con los ids de cada red
src/
  variants.py          Canónico → facebook / instagram / threads / x / linkedin
  publish.py           Orquestador y CLI
  render/*.py          Generadores de tarjeta (deterministas)
  platforms/meta.py    Facebook + Instagram + Threads por Graph API
  platforms/_pending.py Lo que está bloqueado y por qué
assets/fonts/          Lora y Poppins (OFL). Estas SÍ se versionan
assets/*.png           Tarjetas generadas. No: se reproducen del JSON
```

El principio que sostiene todo: **la imagen y los textos son funciones puras del
JSON**. Nada se escribe dos veces, así que nada puede desincronizarse. La
asimetría que tuvimos —Instagram con tarjeta y Facebook con texto pelado— es
imposible de reproducir aquí por construcción.

### Uso

```bash
python3 -m src.publish --due --dry-run     # valida y enseña, sin publicar
python3 -m src.publish --due               # publica lo vencido
python3 -m src.publish --id 2026-08-18-tarde
```

`--dry-run` genera la tarjeta, deriva los cinco textos y pasa las comprobaciones
previas sin tocar la red. Úsalo siempre antes de un cambio.

### Comprobaciones previas

`variants.preflight()` bloquea la publicación si: falta verificación de fuentes,
hay una cita sin atribución confirmada, falta la tarjeta, el subtítulo repite el
gancho, el cuerpo pasa de 300 caracteres, hay etiquetas prohibidas, o algún texto
excede el límite de su plataforma. Probado con casos negativos: los cuatro fallos
típicos se detectan.

**Lo que todavía NO comprueba**, y conviene tener presente al migrar el contenido
pendiente:

- el máximo de 3 al día y el mínimo de 4 horas entre publicaciones
- la no repetición de tema o cita en 90 días
- la alternancia cream/gold contra la última publicación real

`content/published/` hoy solo se escribe, nunca se lee, así que las tres reglas
dependen de que alguien se acuerde. La alternancia se lleva a mano: la pieza de
Séneca trae un campo `_nota_variante` donde alguien anotó que corrigió gold→cream
después de que ya se hubiera cometido el error una vez. Con una sola pieza en cola
no se nota; con 38, sí. Pendiente para después de la primera publicación.

---

## Hosting de imágenes

Instagram y Threads no aceptan subida binaria: Meta **descarga** la imagen desde
una URL HTTPS pública. `src/hosting.py` lo resuelve con dos backends:

- **`github`** (por defecto) — hace commit del PNG y usa la URL de
  `raw.githubusercontent.com`. **Cero credenciales nuevas.** Solo exige que el
  repo sea público, lo cual no es un problema: las tarjetas se publican igual.
- **`r2`** — Cloudflare R2 o cualquier S3, para cuando prefieras el repo privado
  o no quieras imágenes en el historial de git.

Se elige con `SDB_HOSTING`. Antes de pasarle la URL a Meta se comprueba que
responde 200 con `Content-Type: image/*`; si no, falla con un mensaje claro en
vez de dejar que Meta devuelva su error opaco
(`Param image_url is not a valid URI`), que cuesta media hora diagnosticar.

## Pruebas

```bash
python3 tests/test_end_to_end.py
```

Levanta un doble de la Graph API y recorre el camino real completo:
comprobaciones previas → tarjeta → los tres textos → hosting → Facebook →
Instagram → Threads → cambio de estado → movimiento del archivo.

Reproduce a propósito los dos comportamientos que es imposible acertar a ciegas:
el contenedor de Instagram que tarda en procesarse (obliga a hacer polling) y el
error `9007 / subcode 2207006` "Media ID is not available" en el primer intento
de `media_publish` (obliga a reintentar). Catorce comprobaciones, incluidas la
idempotencia (una pieza con `post_id` no se reenvía nunca) y las dos de la
tarjeta: que las fuentes se resuelvan dentro del repo y que una atribución larga
quepa en el marco.

Si esto pasa, lo único que puede fallar en producción son credenciales y
permisos, no la orquestación.

## Tipografía

Las fuentes van **empaquetadas en `assets/fonts/`**, no instaladas del sistema.
Lora y Poppins son OFL-1.1, así que redistribuirlas en un repo público es
legítimo; sus licencias están junto a los archivos.

La razón no es comodidad: es el mismo principio que sostiene el resto. Si la
fuente la pone el sistema operativo, la tarjeta deja de ser una función pura del
JSON y la misma pieza sale distinta en tu Mac y en Actions, sin que nadie se
entere hasta que está publicada.

Antes esto eran rutas absolutas a `/usr/share/fonts/truetype/google-fonts`, el
sandbox donde se redactó el repo. Fuera de ahí, PIL levantaba `OSError: cannot
open resource` y la publicación moría en el primer paso. El workflow creía
cubrirlo con `apt-get install fonts-lora fonts-poppins || true`, pero ninguno de
los dos paquetes existe en Ubuntu y el `|| true` se tragaba el fallo: el paso
salía en verde y reventaba después, al renderizar.

`src/render/fonts.py` busca en `SDB_FONT_DIR` (para probar otra tipografía sin
tocar código), luego en `assets/fonts/`, y si no las encuentra dice dónde buscó
en vez de dejar el error de PIL.

---

## Credenciales

Ninguna vive en el repo. En local, `.env`; en Actions, secrets cifrados.

| Variable | De dónde sale |
|---|---|
| `SDB_PAGE_ID` | `GET /me/accounts` |
| `SDB_PAGE_TOKEN` | Token de página de larga duración, de la misma llamada |
| `SDB_IG_USER_ID` | Campo `instagram_business_account` de esa llamada |
| `SDB_THREADS_USER_ID` / `SDB_THREADS_TOKEN` | App de Threads |
| `R2_*` | El hosting de imágenes que elijas |

Para obtenerlos, una sola vez:

```bash
python3 -c "from src.platforms.meta import discover; discover('TOKEN_DE_USUARIO')"
```

**No hace falta crear una app de Meta.** Ya existe una, funcionando y con
publicaciones reales, en `WorkItContentCreation` (`FACEBOOK_APP_ID` /
`FACEBOOK_APP_SECRET` en `server/.env`, API `v24.0`). Basta con añadir la página
de Sabiduría y su cuenta de Instagram Business a esa app: te ahorras el App
Review, que es lo que suele costar semanas.

Scopes necesarios: `pages_show_list`, `pages_read_engagement`,
`pages_manage_posts`, `instagram_basic`, `instagram_content_publish`.

---

## Estado por plataforma

| Plataforma | Estado | Qué falta |
|---|---|---|
| **Facebook** | Probado end-to-end | Token de página |
| **Instagram** | Probado end-to-end | Token de página + repo público |
| **Threads** | Probado end-to-end | Token de Threads |
| **X** | Texto derivado listo | Acceso de escritura a la API, que es de pago |
| **LinkedIn** | Texto derivado listo | App con "Share on LinkedIn" aprobado |
| **TikTok** | Bloqueado | Auditoría + generar vídeo |
| **YouTube** | Bloqueado | Auditoría + generar vídeo |

### Sobre TikTok y YouTube

Los dos están bloqueados por trámite, no por código, y conviene saberlo antes de
invertir tiempo. Verificado contra la documentación oficial el 17 de agosto de 2026:

- **TikTok:** todo lo que publica un cliente sin auditar queda en `SELF_ONLY`.
  El endpoint `/creator_info/query` no ofrece otra opción de privacidad hasta que
  TikTok audite la app. Publicarías, pero no lo vería nadie.
- **YouTube:** todo vídeo subido con `videos.insert` desde un proyecto de API no
  verificado creado después del 28 de julio de 2020 queda en **privado** hasta
  pasar la auditoría de cumplimiento. La cuota (1 unidad, 100 al día) no es el
  problema; la verificación sí.

Y hay un segundo obstáculo, independiente del trámite: **las dos consumen vídeo**.
La tarjeta 1080×1350 no sirve. Habría que generar vídeo desde la tarjeta —
ffmpeg con un paneo suave, voz sintetizada y música sin derechos es viable, pero
es un proyecto en sí mismo, no una plataforma más en la lista.

Recomendación: empezar por las tres de Meta, que funcionan esta semana, y abrir
el expediente de auditoría de TikTok y YouTube en paralelo, porque tardan.

---

## De dónde sale el contenido

Las tres tareas de Cowork siguen siendo lo que mejor funciona de todo el montaje:
investigan, verifican con búsqueda web y redactan sin fallar. Lo natural es que
sigan haciéndolo y escriban un JSON conforme a `content/schema.json` en vez de un
bloque de markdown.

`do_not_use` en el esquema merece una nota: guarda los datos falsos que circulan
sobre cada tema —la fortuna inventada de Mansa Musa, el "solo sé que no sé nada"
que Sócrates nunca dijo, la frase de Policarpa que escribió un presidente cuarenta
años después—. Es memoria institucional: impide que una sesión futura reintroduzca
un error ya cazado.
