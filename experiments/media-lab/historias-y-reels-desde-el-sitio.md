# Stories y Reels desde «Compartir» de sabiduriadebolsillo.net

Receta para publicar una cita del sitio en Instagram desde un Samsung del laboratorio,
usando la función de compartir de la propia página de la cita. Desde el 2026-11-04 el
teléfono es el SM-S918B (`RFCW117Q7FA`, 1080×2316); el SM-S721B (`R5CXB1AWYNF`, 1080×2340)
sigue valiendo: `labkit/telefono.py` usa el primero de los dos que adb vea autorizado
(`MEDIA_LAB_SERIAL` manda sobre ambos). Las coordenadas cambian con el teléfono y con cada
versión de Instagram: confirmar siempre con una captura antes de tocar.

Estado (2026-11-04): **automatizado**. `lab.py sitio` hace cada paso y el bucle lo lanza
cada 90 min entre las 08:00 y las 23:00 (hora de Madrid) con el encargo
[`sitio-instagram/ciclo-prompt.md`](sitio-instagram/ciclo-prompt.md). Las secciones «paso a paso» de
abajo son la receta a mano en la que se basa el script: sirven para depurarlo cuando una
pantalla cambie.

| Formato | Cita | Diseño / formato | Música («Populaires») | Hora (UTC) | Cómo |
|---|---|---|---|---|---|
| Story | Ovidio, *El remedio del amor* | Papel / Cuadrado | Emilia · BODYPAINTING (n.º 3) | 2026-11-03 18:36 | a mano |
| Reel | José Ingenieros, *Hacia una Moral sin Dogmas* | Tinta / Vertical | Ray Parker Jr. · Ghostbusters (n.º 6) | 2026-11-03 20:42 | a mano |
| Feed | Jaime Balmes, *El Criterio* | Tinta / Cuadrado | Michael Jackson · Thriller (n.º 1) | 2026-11-03 21:16 | script |
| Reel | Jaime Balmes, *El Criterio* | Papel / Vertical | Carmen Goett · La Llorona (n.º 10) | 2026-11-03 21:18 | script |
| Story | Jaime Balmes, *El Criterio* | Papel / Vertical | SENDA SAGRADA Project · LA CATRINA Y LA LLORONA (n.º 7) | 2026-11-03 21:32 | script |
| Feed | Francisco de Quevedo, *El alguacil endemoniado* | Papel / Cuadrado | Róisín Murphy · Ramalama (Bang Bang) (n.º 5) | 2026-11-04 18:51 | script, SM-S918B |
| Reel | Francisco de Quevedo, *El alguacil endemoniado* | Siena / Vertical | Emilia · BODYPAINTING (n.º 4) | 2026-11-04 18:58 | script, SM-S918B |
| Story | Francisco de Quevedo, *El alguacil endemoniado* | Tinta / Vertical | Guns N' Roses · November Rain (n.º 3) | 2026-11-04 19:03 | script, SM-S918B |

## El bucle

Cada ciclo: una cita al azar (dominio público, ≤140 caracteres, sin repetir en 90 días ni
estar en `content/published/`) sale en **feed, Reel y Story**. Cada formato lleva un
diseño al azar (Papel · Tinta · Siena) y un sonido al azar del **top 10 de «Populaires»**,
sin «Audio d'origine» y sin repetir la pista anterior (decisiones del usuario del
2026-11-03). El feed va en **Cuadrado** (lo enseña entero); Reel y Story, en **Vertical**.

```
lab.py lock-tomar --dueno sitio          # dueño propio: no se pisa con la ventana del laboratorio
lab.py sitio elegir                      # run, slug, url y un diseño por formato
lab.py sitio compartir --run R --superficie feed|reel|story --url U --plantilla P
lab.py sitio musica    --run R --superficie …
lab.py sitio pie       --run R --superficie feed|reel --pie <pie.txt de compartir>
lab.py sitio enlace    --run R --superficie story --url U
lab.py sitio publicar  --run R --superficie … --veredicto PASS --slug S --pista "T"
lab.py sitio verificar --run R --superficie … --pista "T" [--pie …]
lab.py lock-soltar --dueno sitio
```

Lo publicado queda en `sitio-instagram/registro.jsonl` (comiteado); las capturas, en
`evidence/android/<run>/` (fuera de git). Código: `labkit/sitio_instagram.py` y
`labkit/cdp.py`; pruebas en la sección 27 de `tests/test_media_lab.py`.

Lo que se aprendió al automatizar (todo está ya en el código):
- **Chrome por DevTools** (`adb forward tcp:9222 localabstract:chrome_devtools_remote`):
  solo responde con Chrome en primer plano. `Runtime.evaluate` con `userGesture: true`
  basta para que `navigator.share` abra la hoja. El pie sale de `data-texto-plano`, la
  atribución canónica del sitio.
- **Feed**: la píldora «Audio suggéré» de arriba aplica una pista sugerida sin preguntar;
  el buscador se abre desde la herramienta «Audio» de abajo. En el feed no hay editor de
  clip, y el selector es una hoja a media altura: la lista se desliza entre los centros
  de sus filas visibles, nunca con coordenadas fijas.
- **Sticker**: el mapa del texto se mide en una captura **antes** de ponerlo. El
  arrastre recorre ~70 % de lo pedido, así que se corrige en varias pasadas. Si no cabe
  con 40 px de aire, `SinHueco` y la Story no sale.
- **Publicar**: en el Reel el botón azul (`share_button`) publica aunque diga «Suivant».
  En el feed el botón es `share_footer_button`.
- **Verificar**: nunca cerrar Instagram mientras sube (lo hace `PendingMediaWorker` en
  segundo plano). Al perfil se va por `instagram://user?username=…`. Un Reel en marcha no
  deja volcar la pantalla: un toque en el centro lo pausa. En la pestaña Reels, tocarla ya
  elegida abre el orden («Les plus récents»). Las destacadas del perfil también empiezan
  por «Story de <cuenta>,»: el visor se reconoce por «il y a …».
- **El contador de publicaciones del perfil va con caché**: no sirve para verificar. En el
  SM-S918B ni la baldosa nueva ni el aro de la Story salen hasta tirar del perfil hacia
  abajo: `verificar` lo refresca siempre antes de mirar.
- **Copia del Reel en la Story**: no es un ajuste de Paramètres. Está en el composer del
  Reel, «Partager aussi sur… → Votre story», encendido por defecto. Al apagarlo Instagram
  pregunta y «Arrêter pour tous les reels» lo quita para la cuenta (hecho el 2026-11-04,
  decisión del usuario). `escribir_pie` lo comprueba en cada Reel por si vuelve. Threads y
  Facebook, en la misma lista, siguen encendidos a propósito (decisión del usuario del
  2026-11-04): cada Reel sale también allí.
- **Instagram en francés**: todo el kit lee textos en francés. En un teléfono en otro
  idioma se pone solo Instagram en francés con
  `adb shell cmd locale set-app-locales com.instagram.android --locales fr-FR` (Android 13+);
  Chrome y la hoja de compartir pueden quedarse en inglés.
- **Hoja de compartir del SM-S918B**: dos filas horizontales con el mismo id; la de arriba
  son **contactos reales** (WhatsApp, Messages) y la de abajo, apps. Instagram no sale en
  la primera pantalla: se desliza solo la fila de apps, a pasos cortos.
- **Volcado comprimido**: `uiautomator dump --compressed` a veces quita el interruptor de
  una fila y deja la fila como `Switch` con su `checked`.

## Por qué así

- La imagen la compone el sitio (`src/islands/ImagenDeCita.astro`) y viaja a la hoja de
  Android por `navigator.share({files})`. Es la misma imagen que vería un visitante: no
  hay un renderer paralelo que mantener.
- El sticker de enlace solo existe en Stories. En Reels no hay enlace clicable.
- La música «en tendencia» es la pestaña «Populaires» del selector de música de
  Instagram (ranking numerado, flecha ↗ = tendencia).

## Elegir la cita

Del corpus `~/dev/sitio-sdb/corpus/citas/*.md`: `estadoDerechos: dominio-público`, texto
corto (< 140 caracteres para que la tarjeta respire) y que no esté ya en
`content/published/` ni en la cola. URL: `https://sabiduriadebolsillo.net/cita/{slug}/`
— comprobar que responde 200 antes de usarla.

## Story paso a paso

1. `adb shell am start -n com.android.chrome/com.google.android.apps.chrome.Main -a android.intent.action.VIEW -d <URL>`
   - **Chrome, no Samsung Internet**: Samsung Internet sale negro en `screencap` y su
     WebView no aparece en `uiautomator dump`, así que no hay evidencia visual posible.
   - Chrome puede abrirse en el selector de pestañas: tocar la pestaña de la cita.
     Cuidado: el toque puede caer después en la página (pulsó «Copiar» una vez; inocuo).
2. Bajar hasta los botones y tocar **«Compartir como imagen»** (no «Compartir la cita»,
   que manda solo texto + enlace). Abre el diálogo «Elige un diseño»: elegir diseño
   (Papel · Tinta · Siena) y formato (**Vertical** para Stories y Reels) → «Compartir»
   → hoja de compartir de Android. Si la hoja tapa el diálogo nada más abrirlo, es
   que el toque llegó dos veces: no pasa nada.
3. En la hoja, mantener pulsado el icono de Instagram → menú **Stories · Messages · Feed
   · Reels** → **Stories**.
4. Editor de Stories: la imagen llena el lienzo. Columna derecha: Aa, stickers, música,
   dibujo.
5. **Música**: icono de nota → pestaña **«Populaires»** → elegir al azar del top 9
   descartando las filas «Audio d'origine» (audio de usuarios, no canciones) → primer
   toque = vista previa; la flecha de la barra inferior confirma. En el editor del clip
   dejar el estilo **«Musique uniquement»** (sin sticker visible) y confirmar con ✓.
   ids útiles: `com.instagram.android:id/track_container`, `audio_browser_track_<n>_<id>`.
6. **Enlace**: stickers → **LIEN** → el campo URL ya tiene el foco → `adb shell input text
   <URL>` (es ASCII, no hace falta `phone_clipboard.py`) → «Personnaliser le texte du
   sticker» → `Leer%sla%scita` → «Terminé».
7. **Regla dura: el sticker nunca tapa la cita** (ni la atribución ni la firma). Aparece
   centrado, **encima de la cita**: arrastrarlo (`input swipe` lento, 900 ms) al hueco
   entre la obra y la firma «SABIDURÍA DE BOLSILLO» (centro y≈1290 en el editor). Un
   arrastre puede quedarse corto: volver a capturar y repetir hasta que quede con aire
   por arriba y por abajo. Si no hay hueco (cita larga), no se publica esa cita.
8. Captura a resolución completa → revisor independiente con `visual-qa-gate.md`
   (decirle explícitamente que el sticker tapando cita/atribución/firma es FAIL) → solo
   con `VERDICT: PASS` se pulsa «Vos stories» (abajo a la izquierda). Ese toque publica
   y vuelve al feed.
   - «Vos stories» lleva la insignia de Facebook: la Story sale también en la Página.
9. **Comprobar**: no fiarse de la bandeja de la portada (caché, y se desplaza). Ir a
   perfil → tocar la foto → recorrer con `input tap 1000 1000` + `uiautomator dump`
   hasta un `content-desc="Story de sabiduriabolsillo, il y a N minutes"` → captura.
   En logcat la subida deja `PendingMediaWorker: doWork` y luego
   `ConfigureResponseHelper` (unos 20 s después).

Primera publicación: 2026-11-03 18:36Z, cita de Ovidio, diseño Papel, música «Emilia ·
BODYPAINTING» (n.º 3 de «Populaires»). QA PASS, verificada en el visor.

## Reel paso a paso

Probado el 2026-11-03 con José Ingenieros, diseño Tinta y formato Vertical, música
«Ghostbusters (Instrumental Version)» (n.º 6 de «Populaires»).

1. Igual que la Story hasta el diálogo «Elige un diseño». Desde el 2026-11-03 tiene dos
   grupos: **diseño** (Papel · Tinta · Siena) y **formato** (Cuadrado · Vertical).
   Elegir **Vertical** (1080×1920; desplegado en `sitio-sdb` 43209d4322). Con el cuadrado
   la portada y la cuadrícula cortan el texto (ver «Bloqueo resuelto»).
2. «Compartir» → mantener pulsado Instagram → **Reels**. **El orden del menú cambia**
   entre usos (una vez Stories·Messages·Feed·Reels, otra Stories·Reels·Messages·Feed):
   localizar la opción por su texto, nunca por posición. Editor: Audio · Texte · Voix ·
   Sous-titres · Stickers.
3. Audio → «Populaires» (la lista muestra además «N K reels» por pista) → elegir al
   azar, sin repetir la pista de la Story → flecha → «Musique uniquement» → ✓.
4. «Suivant» → puede salir un aviso «Nouvelles façons de réutiliser votre contenu»
   (informativo, sobre remix): «OK» lo cierra sin cambiar ajustes.
5. **Comprobar portada y cuadrícula**: «Modifier la couverture» → «Rogner l'image de
   profil» enseña la baldosa 3:4 del perfil. Con Vertical se ven cita, autor y firma
   enteros. Salir con la X las dos veces, sin cambiar nada.
6. **Pie**: tocar «Écrivez une légende…» → `phone_clipboard.py --file pie.txt` (pega
   con tildes y «») → «OK» arriba a la derecha. Plantilla del pie: la cita entre «»,
   «— Autor, Obra» y «La cita, su obra y dónde leerla: sabiduriadebolsillo.net/cita/<slug>».
   Termina en la URL, **no en un hashtag** (un hashtag final abre el desplegable que tapa
   los botones). En Reels la URL no se puede pulsar; solo la Story lleva enlace clicable.
7. «Ajouter une mention IA»: dejarla desactivada. Es para imágenes realistas hechas con
   IA y la tarjeta es tipografía.
8. Revisor independiente sobre el fotograma del editor, la baldosa de la cuadrícula y la
   portada del composer → solo con PASS: «Suivant».
9. Puede salir **«Mise à jour de votre audio d'origine»** (reutilización del audio
   original por otros usuarios y Meta AI). Decisión del usuario del 2026-11-03:
   **«Désactiver et partager»**. Ya no debería volver a salir; si sale, es lo que se
   elige. Ese toque publica y lleva al feed de Reels con la barra «Partage sur Reels…».
10. **Comprobar**: esperar ~40 s → perfil → pestaña Reels → abrir el primero sin chincheta.
    En el volcado, `content-desc="<Artista> · <Pista>"` confirma la música. El contador
    de publicaciones del perfil sube en 1.

Nota del revisor (no bloquea): en el visor de Reels la firma «SABIDURÍA DE BOLSILLO»
(y≈1592 del lienzo) queda justo encima del nombre de la cuenta. No se tapa, pero va
muy justa. Si un día se tapa, subir el límite inferior de la franja vertical en
`imagen.js` (hoy 1680).

**Bloqueo resuelto**: la imagen del sitio era solo cuadrada (1080×1080). La portada del
Reel y la baldosa 3:4 del perfil la ampliaban y **cortaban el texto por los lados**, y
«Rogner l'image de profil» solo desplaza el recorte. Se añadió el formato Vertical al
sitio: todo se compone en la franja central 3:4 (y 240–1680), que conserva la
cuadrícula del perfil y no tapa el visor de Stories.

## Pendiente

- **Vueltas limpias**: los dos ciclos completos (2026-11-03 en el SM-S721B y 2026-11-04 en
  el SM-S918B) salieron enteros, pero con correcciones del script a mitad (el segundo:
  hoja de compartir, refresco del perfil, interruptor de la Story). Hay que mirar los informes de los primeros ciclos programados; si un paso
  vuelve a salir con 4, se depura con las secciones «paso a paso» de arriba.
- **Cadencia con producción**: el ciclo no mira `content/published/`. Las colisiones con
  producción no frenan al laboratorio (decisión del 2026-09-14), pero aquí son 33
  publicaciones al día más las de producción y las copias automáticas en Facebook.
- **Métricas**: el ciclo no recoge vistas. El registro tiene `run` y hora para cruzarlas
  después.
