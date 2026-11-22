# Sonda del móvil: un Reel de vídeo propio hasta la pantalla de detalles (sin publicar)

2026-11-22, 14:30–14:34 (Madrid). SM-S918B (`RFCW117Q7FA`), Instagram en francés, cuenta
`sabiduriabolsillo`. Cerrojo `manual`. Vídeo: el build de `2026-08-23-tarde` (27,5 s, 1,9 MB).
Antes y después: 4 191 publicaciones y «Brouillons · 2». Capturas y volcados en
`evidence/android/SONDA-NARRADO-20261122/` (fuera de git).

## Lo que funciona

1. **Subir el vídeo.** `adb push` a `/sdcard/Movies/SabiduriaLab/<nombre>.mp4` y
   `am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://…`. A los 3 s está en
   `content://media/external/video/media` con duración y tamaño correctos (27533 ms, 1080×1920)
   y el sha256 coincide. `telefono.subir` solo mira el MediaStore de imágenes: hace falta la
   variante de vídeo (`URI_VIDEOS`) y aceptar `.mp4` en `telefono-subir`.
2. **Abrir el compositor.** En la portada, «Créer» (`action_bar_left_button`) abre la galería
   «Nouveau reel» con el vídeo recién subido en la primera casilla (`gallery_grid_item_thumbnail`,
   descripción «Miniature de la vidéo du <fecha> <hora>», etiqueta «0:28»). Un toque lo abre en
   el editor.
3. **Editor.** «Suivant» (`clips_right_action_button`). No se añade audio: el propio del vídeo
   queda como «Audio d’origine». Sale un aviso «Explorez l’audio» arriba que no hay que tocar.
4. **Detalles** (`ModalActivity`, título «Nouveau reel»): leyenda (`caption_input_text_view`),
   portada, y, deslizando hacia abajo:
   - «Renommer l’audio · Audio d’origine».
   - **«Ajouter une mention IA»**: interruptor sin id, `android.view.View` `checkable`, a la
     derecha de la fila (en esta pantalla, `[889,971][1035,1106]`). Un toque lo deja
     `checked=true` sin ningún diálogo. Hay que localizarlo por la fila, no por coordenadas.
   - «Essai» (interruptor): Reel de prueba, se enseña primero a no seguidores. Apagado.
   - **«Partager aussi sur…»: Threads y Facebook vienen ENCENDIDOS.** Hay que apagarlos antes
     de compartir, como hace `ajustar_cruces(False)`.
   - Abajo, fijos: «Enregistrer le brouillon» y «Partager» (`share_button`). No se tocaron.
5. **Salir sin publicar.** «Atrás» vuelve al editor; otro «atrás» abre la hoja «Enregistrer le
   brouillon ?» con «Recommencer» / «Enregistrer le brouillon» / «Continuer les modifications».
   «Recommencer» descarta y vuelve a la galería; un «atrás» más, a la portada.

## Lo que no funciona

- **La hoja de compartir de Android** (`ACTION_SEND` con `video/mp4` y el paquete de Instagram)
  solo ofreció «Instagram · Messages», es decir, mandarlo por mensaje directo. No usar.
- **`com.instagram.share.ADD_TO_REEL`** sin identificador de aplicación: Instagram se abre en
  la portada y no hace nada.

## Para el plan de la fase 2

- La portada del Reel es el primer fotograma: hoy solo dice «NO ES DE», sin el nombre. O el
  primer fotograma lleva ya el gancho entero, o `publicar` elige portada.
- La galería enseñaba otro vídeo de 0:28 del 21 de noviembre a las 15:44 que no subió esta
  sonda. Elegir siempre por la hora de la subida propia, nunca «la primera casilla».
- Al empezar, Instagram estaba en primer plano viendo Reels: alguien usaba el teléfono. El
  paso de abrir tiene que partir de un estado conocido.
- Falta por sondear: escribir la leyenda con tildes en esta pantalla, apagar los dos cruces, y
  qué enseña Instagram justo después de «Partager» (el aviso de audio de origen del 3 nov).
- El vídeo de la sonda se borró del teléfono y de MediaStore al terminar.
