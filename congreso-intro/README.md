# Intro cinematográfica — Congreso juvenil

Intro de 90 segundos para abrir un congreso cristiano de jóvenes: narración en español latinoamericano, banda sonora original, diseño sonoro e imagen cinematográfica, todo generado por código y sincronizado en una sola línea de tiempo.

- **Video final:** `output/intro_congreso.mp4` (1920×1080, 30 fps, H.264 BT.709 rango limitado, AAC estéreo 48 kHz, −14 LUFS)
- **Versión de prueba:** `output/intro_congreso_preview_540p.mp4` (960×540)
- **Versión 4K (opcional):** `output/intro_congreso_4k.mp4` (3840×2160, se genera con `bun run render:4k`)
- **Guion definitivo:** [`docs/GUION.md`](docs/GUION.md)
- **Inventario de recursos y licencias:** [`docs/INVENTARIO_RECURSOS.md`](docs/INVENTARIO_RECURSOS.md)
- **Reporte de validación técnica:** [`docs/REPORTE_VALIDACION.md`](docs/REPORTE_VALIDACION.md)
- **Sobre el video de referencia:** [`docs/REFERENCIA.md`](docs/REFERENCIA.md)

> Los videos `.mp4` no se guardan en git (pesan demasiado). Se entregan aparte o se regeneran con `bun run render`.

## Cambiar el nombre del congreso y los textos

Todo se controla desde **`config/intro.config.json`**:

| Qué | Dónde |
|---|---|
| Nombre del congreso, subtítulo, lema | `evento.nombre`, `evento.subtitulo`, `evento.lema` |
| Versículo (texto, referencia, traducción) | `evento.versiculo` |
| Paleta de colores | `paleta` (fondos de escena, textos, destellos y halos; los paisajes generados la usan al regenerarlos con `scripts/generate_plates.py`) |
| Intensidad de efectos, partículas, niebla, grano, destellos | `estilo` |
| Velocidad de cámara y cortes del montaje final | `estilo.velocidadCamara` (amplitud de los movimientos), `estilo.velocidadEdicion` (1 = 4 cortes en el montaje de 73–75 s; 2 = 8 cortes) |
| Volumen de voz, música y efectos | `audio` |
| Franjas de cine, final sostenido o fundido a negro | `video.franjasCine`, `video.finalSostenido` |
| Resolución | `video.ancho`/`video.alto` (o `bun run render:4k` para 4K) |
| Narración, palabras clave, escenas, planos y sincronía | `narracion`, `palabrasClave`, `escenas`, `planos`, `sincronia` |

El título se ajusta solo al ancho de la pantalla, sea corto («DESPERTAR») o largo.

Después de editar: `bun run render`.

## Instalación

Requisitos: **Node 18+** (o **Bun**), **FFmpeg** y, solo para regenerar audio o fondos, **Python 3.11+**.

```bash
cd congreso-intro
bun install            # o: npm install
```

Para regenerar voz, música o fondos:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/setup_assets.sh      # modelos de voz y samples orquestales (≈1,5 GB en .cache/)
```

## Renderizar

```bash
bun run render           # final 1080p  -> output/intro_congreso.mp4
bun run render:preview   # prueba 540p  -> output/intro_congreso_preview_540p.mp4
bun run render:4k        # 4K           -> output/intro_congreso_4k.mp4
bun run studio           # vista previa interactiva en el navegador (Remotion Studio)
```

`scripts/render.sh` primero rehace la mezcla de audio con los volúmenes de la configuración (si existe el entorno Python), luego renderiza con Remotion (H.264, color BT.709 en rango limitado, el estándar HD que esperan proyectores y procesadores LED) y deja el MP4 listo para reproducirse en cualquier equipo.

Tiempos de referencia en una máquina de 4 núcleos sin GPU: prueba 540p ≈ 5 min, final 1080p ≈ 13 min, 4K ≈ 50 min. No fuerces el renderizador `swangle` (`REMOTION_GL`): en máquinas sin GPU multiplica el tiempo por ~5.

En 4K, textos, siluetas y destellos salen nítidos porque se dibujan a resolución nativa; los paisajes se generaron a 3200×1800 y se escalan, así que se ven algo más suaves. Para paisajes 4K nativos se pueden regenerar a doble escala con `PLATE_SCALE=2 .venv/bin/python scripts/generate_plates.py` (unas 4 veces más cálculo; esa escala no se probó en esta entrega).

Variables opcionales en `.env.example` (no hace falta ninguna API key).

## Cómo está hecho

```
congreso-intro/
├─ config/intro.config.json     configuración central (textos, paleta, volúmenes, línea de tiempo)
├─ src/                         composición Remotion (React)
│  ├─ Intro.tsx                 montaje: planos, palabras clave, versículo, destellos, grano, franjas, audio
│  ├─ scenes/                   escenas (paisajes, personas, textos y título)
│  ├─ components/               cámara con parallax, partículas, niebla, siluetas, efectos
│  └─ lib/                      siluetas humanas procedurales, primeros planos, utilidades
├─ public/
│  ├─ images/plates/            fondos generados (paisajes 3D, ciudad, calle, puerta)
│  ├─ images/textures/          niebla y grano
│  ├─ audio/voice/              narración por bloques + manifiesto con marcas de tiempo por palabra
│  ├─ audio/mix.wav             mezcla final masterizada
│  ├─ audio/stems/              pistas separadas: voz, música, efectos
│  └─ fonts/                    Bebas Neue y Montserrat (OFL)
├─ scripts/                     generación y control de calidad (Python / Node / Bash)
├─ docs/                        guion, inventario, validación, referencia
└─ output/                      videos renderizados
```

### Imagen
- **Paisajes** (horizonte, acantilado, tormenta, cumbre, cresta, campo, rayos, cielo, amanecer): render 3D propio por *raymarching* de terreno con sombras suaves, niebla atmosférica, nubes iluminadas y rayos volumétricos (`scripts/terrain.py`). Cada paisaje se exporta en capas por distancia para moverlas con parallax.
- **Ciudad** desde lo alto y **azotea**: render 3D de una ciudad nocturna con retícula de calles, farolas, autos y ventanas (`scripts/city3d.py`).
- **Calle mojada** y **salón con la puerta**: perspectiva 2D procedural (`scripts/generate_plates.py`).
- **Siluetas humanas**: esqueleto 2D con poses (caminar, manos alzadas, mirar arriba), ropa y peinados variados, contraluz y halo (`src/lib/figure.ts`). Perfil y mano en primer plano dibujados a mano en código (`src/lib/closeups.ts`).
- **Remotion** compone todo con movimientos de cámara 2.5D, partículas, niebla, grano, viñeta, destellos y tipografía animada.

### Voz
- Supertonic 3 (local, sin internet), estilo **M2**: voz masculina grave y serena. Se generan 6 tomas por frase y se elige automáticamente la que Whisper transcribe sin errores y es menos atípica en tono y energía (`scripts/generate_voice.py`).
- Para asegurar el seseo latinoamericano, el texto que se envía al sintetizador escribe *c/z* como *s* (luz → *lus*); los textos en pantalla no cambian.
- Procesado: limpieza, EQ de calidez y presencia, de-esser, compresión y sonoridad por registro (íntimo / firme / clímax).

### Música y sonido
- Banda sonora original compuesta por código en Re menor → Re mayor, 120 BPM (`scripts/compose_score.py`): cuerdas, metales, timbales, platos y gong sampleados (VS Chamber Orchestra 2 CE, CC0), coro sintético por formantes, *braams*, *booms*, *risers*, *whooshes*, viento, truenos, pasos y focos sincronizados con la imagen.
- Mezcla (`scripts/mix_audio.py`): la música baja automáticamente bajo la voz (compresión por sidechain adaptativa), arco dinámico por escenas, limitador a −1 dBFS y −14 LUFS integrados.

## Cambiar la narración

1. Edita `narracion` en `config/intro.config.json` (texto e instante `inicio`).
2. `.venv/bin/python scripts/generate_voice.py --only vo05` (o sin `--only` para todas).
3. Ajusta `inicio` si cambian las duraciones (ver `public/audio/voice/manifest.json`).
4. `.venv/bin/python scripts/mix_audio.py && .venv/bin/python scripts/check_intelligibility.py`
5. `.venv/bin/python scripts/export_docs.py` para actualizar el guion, y `bun run render`.

Si cambias tiempos clave (golpes, título), vuelve a componer la música: `.venv/bin/python scripts/compose_score.py`.

## Control de calidad

| Herramienta | Qué hace |
|---|---|
| `scripts/check_intelligibility.py` | Transcribe cada frase desde la mezcla final con Whisper y calcula el WER |
| `scripts/audio_report.py` | Gráfica de sonoridad por pista y espectrograma (`.cache/qa/audio_report.png`) |
| `node scripts/stills.mjs <dir> <seg…>` | Renderiza fotogramas sueltos en una sola sesión |
| `scripts/contact_sheet.py` | Hoja de contactos de esos fotogramas |
| `scripts/validate_video.py` | Comprueba el MP4 final (duración, resolución, fps, códecs, sonoridad, picos) |

## Licencias

- Imagen, música, efectos y guion: obra original de este proyecto.
- Samples orquestales: VS Chamber Orchestra 2 Community Edition — CC0 1.0.
- Voz: modelo Supertonic 3 (OpenRAIL-M; código MIT).
- Tipografías: SIL Open Font License 1.1.
- Versículo: Reina-Valera 1960 © Sociedades Bíblicas en América Latina, 1960; © renovado Sociedades Bíblicas Unidas, 1988 (cita breve dentro de sus condiciones de uso).
- **Remotion** tiene licencia propia: gratuita para personas, organizaciones sin fines de lucro y empresas de hasta 3 empleados. Una iglesia o ministerio sin fines de lucro puede usarla gratis; una empresa más grande necesitaría una licencia de empresa (remotion.pro).

## Limitaciones

- La narración es una voz sintética de alta calidad, no un locutor humano. Para una voz humana, reemplaza los archivos de `public/audio/voice/` respetando los nombres y tiempos, y ejecuta `scripts/mix_audio.py`.
- Las imágenes son generadas por procedimiento (paisajes 3D, siluetas, luz); no hay metraje filmado.
- El nombre del congreso y el lema son marcadores provisionales hasta que se definan.
