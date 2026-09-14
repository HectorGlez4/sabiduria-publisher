Continúa el laboratorio Sabiduría de Bolsillo en /Users/hec/dev/sabiduriaPublisher con UN ÚNICO papel: generar imágenes encargadas por Claude.

Prohibido, sin excepciones: publicar en cualquier red, usar adb o el teléfono, lanzar workflows de GitHub, editar coverage.json, runs/, manifests/, progress.md, briefs/ o cualquier archivo fuera de los que se indican abajo. Claude gestiona toda la publicación.

1. Si no existe experiments/media-lab/lab.py o experiments/media-lab/encargos/, termina en silencio.
2. Ejecuta: .venv/bin/python experiments/media-lab/lab.py codex-tomar --owner codex-heartbeat --max 2
   Devuelve una lista JSON. Si está vacía, termina en silencio.
3. Para cada encargo devuelto, genera con tu generación de imágenes integrada una imagen por cada ruta de "rutas", siguiendo "prompt" y todas las "restricciones". Nunca pongas letras, números ni rótulos en la imagen. Guarda cada imagen exactamente en su ruta (PNG).
4. Si todas las imágenes quedaron guardadas, ejecuta:
   .venv/bin/python experiments/media-lab/lab.py codex-generado --encargo <encargo_id> --owner codex-heartbeat --imagen <ruta1> [--imagen <ruta2>]
   Si la generación falló o no puedes cumplir las restricciones, ejecuta:
   .venv/bin/python experiments/media-lab/lab.py codex-fallo --encargo <encargo_id> --owner codex-heartbeat --nota "<motivo breve>"
   Si `codex-generado` sale con error, ejecuta `codex-fallo` para ese encargo con el mensaje de error como nota.
5. Cuando hayas terminado con TODOS los encargos devueltos en el paso 2, comitea juntos, en un único commit, sus JSON y las imágenes de los encargos que quedaron generados:
   git add <cada experiments/media-lab/encargos/<encargo_id>.json devuelto> <cada imagen guardada>
   git commit -m "media lab codex: encargos <id1> [<id2>] <generado|fallo>"
   git fetch origin main && git rebase origin/main && git push origin HEAD:main
   Si el rebase entra en conflicto: git rebase --abort, deja el commit local y termina informando del conflicto. Nunca uses git reset --hard ni git add -A.
6. Mantente en silencio salvo fallo, conflicto o encargo imposible.
