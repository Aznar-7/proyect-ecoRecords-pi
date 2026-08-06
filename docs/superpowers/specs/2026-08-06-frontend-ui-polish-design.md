# Eco Records — Pulido de UI/UX del frontend

**Fecha:** 2026-08-06
**Estado:** Aprobado, pendiente de plan de implementación

## Contexto

Eco Records corre en una Raspberry Pi Zero 2W (backend Flask + daemon, ver
`README.md`). El frontend es una PWA vanilla (HTML/CSS/JS, sin build step)
servida desde la Pi y renderizada en el teléfono del usuario — las
restricciones de recursos de la Pi aplican al *servidor* (no agregar
dependencias pesadas, no procesos adicionales constantes), no al *cliente*
que renderiza; aun así el frontend se mantiene deliberadamente liviano y sin
frameworks, siguiendo el patrón ya establecido.

Este trabajo es una pasada de UI/UX sobre un frontend ya funcional:
eliminar una feature vestigial (iluminación), arreglar una animación de
cambio de disco que se intentó una vez y se sacó por verse mal, y corregir
un puñado de bugs/detalles de pulido menores encontrados al revisar el
código. No se toca la lógica de audio, motor, NFC ni GPIO.

## No-objetivos

- No se cambia la paleta de colores (crema/marrón/ámbar) ni la tipografía
  (Playfair Display + Inter).
- No se rediseña la estructura de vistas (Inicio / Discos / Agregar).
- No se toca `daemon.py`, control de motor, NFC ni audio.
- No se agregan frameworks JS, librerías de animación, ni build pipeline.

## 1. Eliminar Iluminación (frontend + backend puntual)

**Diagnóstico:** `/api/lights` en `app.py` y la clave `"lights"` en
`config.json` no tienen ningún consumidor real — no existe driver de
NeoPixel/WS2812B en `app.py` ni `daemon.py`. Es remanente del hardware de
iluminación que se sacó del proyecto.

**Cambios:**
- `templates/index.html`: quitar el bloque `.control-row` de "Iluminación"
  y `.lights-row` (botones Apagado/Cálida/Suave) dentro de `.controls-card`.
- `static/css/style.css`: quitar `.lights-row`, `.light-btn`,
  `.light-btn.active` y cualquier regla que solo exista para esos
  elementos.
- `static/js/app.js`: quitar `state.lights`, `LIGHT_LABELS`,
  `renderLights()`, `setLights()`, el listener de `.light-btn`, y la
  llamada a `renderLights()` dentro de `renderAll()`.
- `app.py`: quitar la ruta `/api/lights` (`set_lights`) y la clave
  `"lights"` del payload de `/api/status`.
- `config.json` (el de ejemplo versionado, si existe una clave `lights`):
  quitarla.

**Riesgo:** bajo. Es remoción de código muerto sin efecto funcional.

## 2. Animación de cambio de disco

### Diagnóstico del intento anterior

En el commit `fe89974` hubo una función `animateDiscChange()` que:
1. Comparaba por `trackName` (cambia en cada pista) en vez de por álbum —
   la animación se disparaba en cada cambio de pista, no solo al apoyar un
   disco físico distinto.
2. Animaba `disc.style.transform = 'scale(...)'` directamente sobre el
   mismo elemento `#disc` que ya tiene `animation: spin ... infinite`
   corriendo por CSS (`@keyframes spin`, también sobre `transform`). Un
   `transform` inline y una animación CSS peleando por la misma propiedad
   del mismo elemento produce saltos/choques visuales — la causa raíz de
   que "se viera feo" y se terminara sacando.

Ambos problemas se resuelven con el diseño de abajo.

### Arquitectura

- El slide anima **`#disc-wrapper`** (`translateX` + `opacity`), no
  `#disc`. El giro (`@keyframes spin`) sigue viviendo exclusivamente en
  `#disc` sin que nada JS le toque `transform` inline. Un `transform` en
  el padre y otro en el hijo no compiten — cada uno resuelve su propio
  espacio de transformación — así que el giro nunca se interrumpe ni
  salta.
- Toda la animación usa `transform`/`opacity` vía transiciones CSS
  (clases toggleadas desde JS), no JS-driven (no `requestAnimationFrame`
  loop, no recalculo de estilos por frame). Barato para el teléfono y
  simple de mantener.

### Disparo

- Se dispara **solo cuando cambia `state.coverAlbumId`** (identidad de
  álbum, viene de `data.raw_album` en `/api/status`), nunca por cambio de
  `trackName`/pista dentro del mismo álbum.
- No se dispara en la carga inicial de la página — se usa el flag
  `state.initialized` ya existente para distinguir "primer render" de
  "cambio real detectado en un poll posterior".
- Se dispara tanto para álbum → álbum distinto, como para álbum → vacío
  (disco retirado) y vacío → álbum (disco apoyado). Ver estado "plato
  vacío" abajo.

### Secuencia

1. **Sale**: `.disc-wrapper` desliza hacia la izquierda
   (`translateX(-140%)`) con fade-out simultáneo, ~250ms,
   `ease-in` (`--ease-in-soft`).
2. Al terminar el paso 1: sin transición (`transition: none` momentáneo +
   reflow forzado), se teleporta el wrapper a `translateX(140%)` del lado
   opuesto y se actualiza el contenido (tag del disco, `disc-cover`,
   estado vacío/con-disco).
3. **Entra**: desliza desde la derecha hacia `translateX(0)` con
   fade-in, ~300ms, con un ease-out con leve *overshoot*
   (`cubic-bezier(0.34, 1.4, 0.64, 1)` — la misma curva que ya usa
   `card-up` en los modales, para consistencia de "lenguaje de
   movimiento").
4. **Reentrada durante animación en curso**: si llega un nuevo
   `coverAlbumId` mientras el paso 1-3 sigue activo, se cancela lo que
   esté corriendo (se limpian los `setTimeout` pendientes), se salta
   directo al estado final visual sin animar, y recién ahí se evalúa si
   hay que animar hacia el nuevo estado. Evita que se acumulen
   transiciones pisándose entre sí.

### Estado "plato vacío"

Cuando no hay disco apoyado (`coverAlbumId` es `null`), en vez de mostrar
siempre el vinilo negro con tag `"—"` (comportamiento actual), se muestra
una variante visual de plato vacío: mismo tamaño y posición que `.disc`,
pero sin grooves marcados y sin label/tag activo (anillo tenue). Esto le
da sentido físico completo al gesto de deslizar: sacar el disco = desliza
hacia afuera y revela el plato vacío; apoyar uno = desliza para adentro
sobre el plato.

Implementación: una clase modificadora (p. ej. `.disc.is-empty`) que
ajusta `background`/`border`/opacity de `.disc-grooves` y `.disc-label`
sin agregar marcado nuevo pesado — reutiliza la estructura existente.

## 3. Bugs puntuales

- **Prev/next bloqueados en pausa** (`static/js/app.js`,
  `els.prevBtn.disabled` / `els.nextBtn.disabled`): pasan a habilitarse
  según `state.totalTracks > 0` (hay un álbum cargado) en vez de
  `state.playing`. El backend ya lo permite — `/api/next` y `/api/prev`
  no chequean estado de reproducción.
- **Flash de ícono inicial** (`templates/index.html` + `app.js`): el
  HTML hoy arranca con el ícono de "pausa" (asume reproducción) hasta
  que llega el primer `/api/status`. Se cambia el HTML estático a un
  estado neutro (ícono play, controles deshabilitados) y se completa
  `renderInitial()` para dejar el disco en estado "plato vacío" y los
  botones prev/next/play deshabilitados hasta el primer fetch exitoso.

## 4. Pulido menor de animación/consistencia

- **Cierre de modales simétrico**: `#settings-modal` y `#learn-modal`
  hoy abren con `modal-in`/`card-up` (CSS `@keyframes`) pero cierran
  seteando `display:none` de golpe, sin transición de salida. Se agrega
  una clase `.closing` (fade-out del overlay + slide-down corto del
  card, ~180ms) aplicada antes de ocultar, coordinada desde JS con un
  `setTimeout` corto para el `display:none` final.
- **Crossfade de texto en cambio de pista**: `track-name`/`track-sub`
  hacen un fundido corto (~150ms, opacity) al cambiar de pista dentro
  del mismo álbum, en vez de reemplazo instantáneo del texto. Esto es
  independiente del slide de disco (que solo aplica a cambio de álbum).
- **Tokens de duración/easing**: se centralizan las curvas/duraciones
  usadas (nuevas y existentes) como variables CSS en `:root`
  (`--ease-out-soft`, `--ease-in-soft`, `--dur-fast`, `--dur-base`,
  `--dur-slide`) para que el slide de disco, los modales y las
  transiciones de vista compartan el mismo lenguaje de movimiento en
  vez de valores sueltos repetidos por todo `style.css`.
- **Polling**: `setInterval(loadStatus, 500)` pasa a 700ms. El ticker
  local de progreso (`setInterval` que incrementa `state.elapsed` cada
  1s) ya suaviza visualmente entre polls, así que el cambio no se nota
  en la UI pero reduce carga constante contra la Pi.

## Archivos afectados

- `templates/index.html` — quitar bloque Iluminación, ajustar markup
  inicial del disco/ícono play para evitar el flash.
- `static/css/style.css` — quitar reglas de luces, agregar tokens de
  easing/duración, estilos de `.disc.is-empty`, slide de
  `.disc-wrapper`, `.closing` de modales, crossfade de texto.
- `static/js/app.js` — quitar estado/lógica de luces, implementar
  `animateDiscChange()` nuevo (disparado por `coverAlbumId`), fix
  prev/next, completar `renderInitial()`, cierre animado de modales,
  crossfade de track name/sub, intervalo de polling a 700ms.
- `app.py` — quitar ruta `/api/lights` y clave `lights` de
  `/api/status`.
- `config.json` (ejemplo versionado) — quitar clave `lights` si está
  presente.

## Testing / verificación

No hay test automatizado en el repo para el frontend (es vanilla
JS/CSS sin framework de testing). Verificación manual:
- Cargar la app fresca: sin flash de ícono de pausa, disco en estado
  "plato vacío", prev/next deshabilitados.
- Simular cambio de álbum (dos discos NFC distintos, o mockeando
  `/api/status` en devtools): el slide lateral corre sin que el giro
  del disco (`spinning`) se corte ni salte cuando está reproduciendo
  durante la transición.
- Cambiar de pista dentro del mismo álbum: no dispara el slide, solo
  el crossfade de texto.
- Pausar y tocar prev/next: deben funcionar.
- Abrir y cerrar ambos modales: fade-out visible al cerrar, no
  `display:none` abrupto.
- Confirmar que no queda ninguna referencia a "luces"/"lights" ni en
  la UI ni en `app.py`/`config.json` de ejemplo.
