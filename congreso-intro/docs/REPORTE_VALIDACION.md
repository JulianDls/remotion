# Reporte de validación técnica

## intro_congreso.mp4 — APROBADO

- Video: h264 · 1920×1080 · 30.000 fps · yuv420p · 13.1 Mb/s
- Audio: aac · 48000 Hz · 2 canales
- Sonoridad integrada: -14.0 LUFS · pico real: -0.9 dBTP

| Comprobación | Resultado | Detalle |
|---|---|---|
| Contenedor MP4 | ✅ | mov,mp4,m4a,3gp,3g2,mj2 |
| Códec de video H.264 | ✅ | h264 High yuv420p |
| Frecuencia 30 fps | ✅ | 30.000 fps |
| Duración ≈ 90 s | ✅ | 90.005 s |
| Resolución 16:9 | ✅ | 1920×1080 |
| Color BT.709 en rango limitado (estándar HD) | ✅ | yuv420p · bt709 · rango tv |
| Audio AAC estéreo 48 kHz | ✅ | aac 48000 Hz 2 canales |
| Audio cubre todo el video | ✅ | audio 90.005 s / video 90.005 s |
| Sonoridad integrada (−16…−12 LUFS) | ✅ | -14.0 LUFS |
| Sin saturación (pico real ≤ −0,5 dBTP) | ✅ | -0.9 dBTP |
| Sin silencios accidentales | ✅ | silencios: [(75.02, 75.8)] |
| Sin pantallas negras accidentales | ✅ | tramos negros: [(0.0, 0.9), (75.13, 75.8)] |

Tramos oscuros detectados (intencionales: fundido de entrada y silencio previo al título): 0.00–0.90 s, 75.13–75.80 s

## intro_congreso_4k.mp4 — APROBADO

- Video: h264 · 3840×2160 · 30.000 fps · yuv420p · 32.2 Mb/s
- Audio: aac · 48000 Hz · 2 canales
- Sonoridad integrada: -14.0 LUFS · pico real: -0.9 dBTP

| Comprobación | Resultado | Detalle |
|---|---|---|
| Contenedor MP4 | ✅ | mov,mp4,m4a,3gp,3g2,mj2 |
| Códec de video H.264 | ✅ | h264 High yuv420p |
| Frecuencia 30 fps | ✅ | 30.000 fps |
| Duración ≈ 90 s | ✅ | 90.005 s |
| Resolución 16:9 | ✅ | 3840×2160 |
| Color BT.709 en rango limitado (estándar HD) | ✅ | yuv420p · bt709 · rango tv |
| Audio AAC estéreo 48 kHz | ✅ | aac 48000 Hz 2 canales |
| Audio cubre todo el video | ✅ | audio 90.005 s / video 90.005 s |
| Sonoridad integrada (−16…−12 LUFS) | ✅ | -14.0 LUFS |
| Sin saturación (pico real ≤ −0,5 dBTP) | ✅ | -0.9 dBTP |
| Sin silencios accidentales | ✅ | silencios: [(75.02, 75.8)] |
| Sin pantallas negras accidentales | ✅ | tramos negros: [(0.0, 0.9), (75.13, 75.8)] |

Tramos oscuros detectados (intencionales: fundido de entrada y silencio previo al título): 0.00–0.90 s, 75.13–75.80 s

## intro_congreso_preview_540p.mp4 — APROBADO

- Video: h264 · 960×540 · 30.000 fps · yuv420p · 0.8 Mb/s
- Audio: aac · 48000 Hz · 2 canales
- Sonoridad integrada: -14.0 LUFS · pico real: -0.8 dBTP

| Comprobación | Resultado | Detalle |
|---|---|---|
| Contenedor MP4 | ✅ | mov,mp4,m4a,3gp,3g2,mj2 |
| Códec de video H.264 | ✅ | h264 High yuv420p |
| Frecuencia 30 fps | ✅ | 30.000 fps |
| Duración ≈ 90 s | ✅ | 90.005 s |
| Resolución 16:9 | ✅ | 960×540 |
| Color BT.709 en rango limitado (estándar HD) | ✅ | yuv420p · bt709 · rango tv |
| Audio AAC estéreo 48 kHz | ✅ | aac 48000 Hz 2 canales |
| Audio cubre todo el video | ✅ | audio 90.005 s / video 90.005 s |
| Sonoridad integrada (−16…−12 LUFS) | ✅ | -14.0 LUFS |
| Sin saturación (pico real ≤ −0,5 dBTP) | ✅ | -0.8 dBTP |
| Sin silencios accidentales | ✅ | silencios: [(75.02, 75.8)] |
| Sin pantallas negras accidentales | ✅ | tramos negros: [(0.0, 0.93), (75.13, 75.8)] |

Tramos oscuros detectados (intencionales: fundido de entrada y silencio previo al título): 0.00–0.93 s, 75.13–75.80 s

## Inteligibilidad de la narración en la mezcla final

Cada frase se transcribió con Whisper (modelo small, español) directamente desde `.cache/qa/audio_del_mp4_final.wav` (con música y efectos). WER medio: **0.006**.

| Frase | WER | Transcripción automática |
|---|---|---|
| vo01 | 0.00 | Hay momentos en los que el ruido del mundo intenta apagar lo que Dios encendió en nosotros. |
| vo02 | 0.00 | Generaciones enteras han buscado respuestas. |
| vo03 | 0.00 | Han perseguido sueños, identidad y propósito. |
| vo04 | 0.00 | Pero hay una voz que sigue llamando. |
| vo05 | 0.00 | No fuimos creados para vivir dormidos. |
| vo06 | 0.00 | fuimos llamados a conocerle, a seguirle y a vivir para algo mucho más grande que nosotros mismos. |
| vo07 | 0.00 | No se trata solamente de reunirnos. |
| vo08 | 0.00 | se trata de responder a su llamado. |
| vo09 | 0.00 | Una generación. |
| vo10 | 0.00 | Una fe. |
| vo11 | 0.00 | Una respuesta. |
| vo12 | 0.08 | y si éste fuera el momento de dejar de mirar desde lejos. |
| vo13 | 0.00 | y comenzar a vivir aquello para lo que fuimos llamados. |

## Mezcla de audio

- Sonoridad integrada de `public/audio/mix.wav`: -14.03 LUFS · pico de muestra: -1.0 dBFS.
- Arco dinámico por escena (sonoridad integrada de cada tramo):

| Escena | LUFS |
|---|---|
| 1. El silencio | -17.5 |
| 2. La búsqueda | -17.2 |
| 3. El llamado | -16.4 |
| 4. La Palabra y la promesa | -14.1 |
| 5. El despertar | -13.4 |
| 6. La revelación | -11.4 |
| 7. El impacto final | -12.6 |

## Narración generada

Motor: supertonic · estilo M2 · 6 tomas por frase, selección automática.

| Frase | Toma elegida | Duración | Whisper (toma) | Whisper (procesada) |
|---|---|---|---|---|
| vo01 | 5 | 6.99 s | 0.00 | 0.00 |
| vo02 | 0 | 3.08 s | 0.00 | 0.00 |
| vo03 | 3 | 3.35 s | 0.00 | 0.00 |
| vo04 | 5 | 1.93 s | 0.00 | 0.00 |
| vo05 | 4 | 2.68 s | 0.00 | 0.00 |
| vo06 | 5 | 6.87 s | 0.00 | 0.00 |
| vo07 | 5 | 2.28 s | 0.00 | 0.00 |
| vo08 | 5 | 2.32 s | 0.00 | 0.00 |
| vo09 | 5 | 1.18 s | 0.00 | 0.00 |
| vo10 | 0 | 0.82 s | 0.00 | 0.00 |
| vo11 | 0 | 1.14 s | 0.00 | 0.00 |
| vo12 | 5 | 4.17 s | 0.00 | 0.00 |
| vo13 | 1 | 3.92 s | 0.00 | 0.00 |

## Revisión visual

- Se renderizaron y revisaron fotogramas de todos los planos (hojas de contactos) en varias iteraciones; se corrigieron: cielos sobreexpuestos, nubes planas, iluminación de bordes del terreno, disco solar en la tormenta, anatomía de siluetas, perfil y mano, palabras que se salían del cuadro, contraste de textos sobre fondos claros, inicio oscuro de la puerta y del plano de transición.
- Textos en español revisados contra la configuración (tildes y signos de apertura incluidos); el versículo respeta la Reina-Valera 1960.
- Ninguna palabra queda fuera del cuadro visible con las franjas de cine (área útil 1920×803 px); el título se ajusta automáticamente al 84 % del ancho.
- Sincronía: la voz, la música y los cortes comparten `config/intro.config.json`; las palabras clave usan marcas de tiempo por palabra (Parakeet) y los pasos, truenos, puerta y focos coinciden con su imagen.
- Versión 4K: se revisaron recortes a tamaño real. Textos, siluetas, partículas y destellos se dibujan a resolución nativa y se ven nítidos; los paisajes se generaron a 3200×1800 y se escalan, así que se ven algo más suaves que el texto. Para paisajes 4K nativos se pueden regenerar los fondos a doble escala (`PLATE_SCALE=2 .venv/bin/python scripts/generate_plates.py`, unas 4 veces más cálculo; esa escala no se probó en esta entrega) antes de `bun run render:4k`.

