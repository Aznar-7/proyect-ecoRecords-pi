# Spec — Mejoras Eco Records (volumen, filtro de audio, batería, historial, estadísticas, UI)

**Fecha:** 2026-09-14
**Origen:** Requerimientos dictados directamente por el usuario en conversación (brainstorming saltado a pedido explícito).

## Arquitectura actual (contexto, no cambia)

- `app.py`: servidor Flask (puerto 5000), rutas API REST.
- `daemon.py`: proceso separado — NFC (PN532, I2C 0x24), motor paso a paso (GPIO 5/6/13/26), reproducción de audio real vía `mpg123` (subprocess nuevo por pista, no modo remoto).
- Ambos corren como servicios systemd independientes.
- Comunicación Flask ↔ daemon: exclusivamente vía `config.json` compartido (Flask escribe `command`, daemon lo lee y limpia; daemon escribe `now_playing`, Flask lo lee para `/api/status`).
- Frontend: HTML/CSS/JS vanilla, PWA instalable, polling cada ~1s a `/api/status`.
- Audio: 2× MAX98357A (I2S). Sensor Hall ya descartado — el NFC dispara la reproducción directo.
- Raspberry Pi Zero 2W, 512MB RAM — mantener todo liviano.

## Tarea 1 — Control de volumen por software

- El MAX98357A no tiene volumen por hardware.
- `app.py` ya tiene `/api/volume` (POST) que guarda `"volume"` (0-100) en `config.json`.
- En `daemon.py`, al cargar pista (`load_track`) y al reanudar (`_resume_now`), leer el volumen de `config.json` y pasarlo a `mpg123` con `-f` (factor 0-32768, 100% = 32768). Fórmula: `factor = int((volumen_pct / 100) * 32768)`.
- Limitación aceptable: el cambio no es instantáneo a mitad de canción.
- Confirmar que el slider de volumen del frontend ya esté bien conectado a la ruta.

## Tarea 2 — Filtro de audio (reducir distorsión en graves)

- Parlantes 52mm + amplis 3W: temas con mucho grave distorsionan.
- Agregar pasa-altos suave (~100-150Hz) antes de reproducir.
- Evaluar: EQ nativo de mpg123 por línea de comandos, o `sox` como paso intermedio generando un archivo temporal filtrado, evaluando impacto de performance en Pi Zero 2W.

## Tarea 3 — Indicador de batería (UPS HAT Waveshare C, INA219)

Ya verificado en la Pi:
```python
from ina219 import INA219
ina = INA219(shunt_ohms=0.1, address=0x43, busnum=1)
ina.configure()
voltage = ina.voltage()   # ~3.0V (vacía) a ~4.2V (llena)
current = ina.current()   # negativo = descargando, positivo = cargando
```
- Fórmula: `pct = max(0, min(100, round((voltage - 3.0) / (4.2 - 3.0) * 100)))`.
- Agregar a `config.json`: `"battery": {"percent": X, "charging": bool}`, actualizado periódicamente desde `daemon.py` (mismo patrón que `progress_ticker`, cada 5-10s alcanza).
- Exponer en `/api/status`.
- Ícono + porcentaje en la webapp, con indicador visual de "cargando" cuando `current > 0`.
- Opcional: aviso visual si el porcentaje cae por debajo de ~15-20%.

## Tarea 4 — Historial de reproducción

- Cada vez que se carga una pista nueva (`load_track`), agregar entrada con: álbum, nombre de pista, timestamp. Archivo aparte (`history.json`) para no sobrecargar `config.json`.
- Limitar a los últimos 50 eventos.
- Nueva ruta `/api/history` en `app.py`.
- Sección "Escuchado recientemente" en la webapp.

## Tarea 5 — Estadísticas de uso

- Contar reproducciones totales por álbum, incrementado cada vez que se carga la **primera pista de un álbum** (no cada cambio de pista dentro del mismo álbum).
- Objeto simple `{"album_id": contador}` (archivo aparte, ej. `stats.json`).
- Mostrar en la webapp "álbum más escuchado" / ranking básico.

## Consideraciones generales (todas las tareas)

- Pi Zero 2W, 512MB RAM — liviano, evitar dependencias pesadas nuevas si se puede resolver con lo ya instalado.
- Cualquier polling nuevo (batería, etc.) debe seguir el patrón de thread `daemon=True` con su propio `sleep`, sin bloquear el loop principal de NFC.
- Todo cambio en `config.json` debe mantener compatibilidad con las claves existentes (`albums`, `now_playing`, `command`, `volume`, `lights`).
- Probar cada feature de forma aislada antes de integrar con las demás.

## Calidad de código

- Nombres descriptivos, funciones cortas de una sola responsabilidad, comentarios solo donde algo no sea obvio.
- Seguir el estilo ya presente: `threading.Lock()` para estado compartido, manejo de excepciones explícito en loops principales, logs con prefijo `[ECO]`.
- No introducir abstracciones innecesarias — proyecto personal de tamaño acotado, no over-engineering (evitar clases nuevas si una función simple alcanza).

## Tarea 6 — Pulido de UI (empezando por el modal de reinicio)

- Modal de Ajustes: el botón "Reiniciar" debe sentirse como una acción distinta ("seria"/destructiva) del resto de los controles, con separación visual clara.
- Estado de carga más claro durante el reinicio: no solo cambiar el texto — spinner/animación, y deshabilitar visualmente el resto del modal mientras reinicia.
- Mantener paleta y tipografía existentes (`style.css`: paleta cálida marrón/ámbar, tipografía serif para títulos) — no introducir un estilo distinto.
- Aplicar el mismo criterio de pulido (jerarquía visual, feedback de estado) a los nuevos elementos de UI de las tareas anteriores (batería, historial, estadísticas) para que se sientan parte de la misma app.

## Restricción del usuario

- No usar el plugin de brainstorming para este trabajo (el resto de los flujos/skills sí).
