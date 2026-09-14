# Compuerta visual antes de publicar

Vigente desde 2026-09-14, por decisión del usuario: **no hay confirmación humana antes de publicar**. Se publica cuando un agente revisor independiente devuelve PASS.

Antes de cualquier envío público, por API o por teléfono:

1. Captura la composición final tal como va a salir (recorte, texto superpuesto, etiqueta de música, stickers y controles de la plataforma) y ten a mano el máster.
2. Encarga a un agente independiente que la revise. Debe devolver `VERDICT: PASS` o `VERDICT: FAIL` para esa captura concreta.
3. Guarda en el run la ruta de la captura y el dictamen antes de enviar.

El revisor solo comprueba esto:

- Ningún texto (de la imagen o del pie visible) está cortado o se sale del encuadre.
- La imagen no está recortada de forma que se pierda una parte esencial: marco, texto o firma de marca.
- Nada tapa texto ni imagen: etiqueta de música, stickers, encuestas, desplegables, teclado o controles de la aplicación.

Un FAIL, o no tener dictamen, bloquea el envío. Se corrige y se revisa otra vez; si vuelve a fallar, se abandona la celda y se registra.

La música elegida dentro de la aplicación sigue siendo obligatoria en toda foto publicada por teléfono, pero no la valora el revisor: la comprueba el propio flujo (`compositor_listo` exige el tema en el compositor antes de pulsar Compartir).
