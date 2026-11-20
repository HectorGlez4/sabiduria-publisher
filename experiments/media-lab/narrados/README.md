# Reels narrados: entorno de voz

La voz de producción es Kokoro (`em_santa`, español, velocidad 0,95), que `labkit/narrado_voz.py`
lanza a través de `hyperframes tts`. Necesita un entorno de Python 3.12 propio, sin comitear
(`experiments/media-lab/.venv-voz`). Con Python 3.14 falla con un error de `phontab` que no se
encuentra. Desde la raíz del repo:

```
uv venv --python 3.12 experiments/media-lab/.venv-voz
uv pip install --python experiments/media-lab/.venv-voz/bin/python kokoro-onnx soundfile
npx --yes hyperframes@0.9.70 telemetry disable
```

Los modelos se descargan solos la primera vez en `~/.cache/hyperframes/tts`.

Comprobación rápida:

```
cd experiments/media-lab && ../../.venv/bin/python -c "
from pathlib import Path
from labkit.narrado_voz import sintetizar
print(sintetizar('Esta frase no es de Viktor Frankl.', Path('/tmp/prueba-voz.wav')))"
```

Debe imprimir una duración entre 1,5 y 3,5 s. `say -v Paulina -r 165` existe solo como motor de
pruebas y de último recurso (`motor="say"`).
