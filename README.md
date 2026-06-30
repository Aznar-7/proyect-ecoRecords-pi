<div align="center">

# 🎵 Eco Records

### Un tocadiscos NFC hecho a mano, disco por disco

*Apoyás un disco. Empieza a girar. Suena la música. Brillan las luces.*

[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Zero%202W-C51A4A?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Status](https://img.shields.io/badge/status-en%20construcción-C4956A?style=flat-square)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)]()

</div>

---

## ✦ Qué es esto

**Eco Records** es un tocadiscos físico construido desde cero: cada disco de acrílico representa un álbum completo. Lo apoyás sobre la base, un lector NFC oculto detecta cuál es, el plato empieza a girar, suena la música y se enciende una luz cálida alrededor.

No hay pantalla. No hay control remoto. No hace falta el celular para usarlo — apoyás el disco y listo.

Inspirado en el [Echo Spins](https://echospinsofficial.com/), pero diseñado, programado y construido enteramente a mano como regalo personalizado. Sin compras de productos terminados — cada decisión de hardware, cada línea de código y cada corte de acrílico es parte del proyecto.

<br>

## ✦ Cómo funciona

```
   disco apoyado
        │
        ▼
  lector NFC (PN532) identifica el UID
        │
        ▼
  UID → álbum (vía config.json)
        │
        ├──► motor gira el plato
        ├──► se reproduce la carpeta del álbum
        └──► se enciende el anillo de luces
```

Cada disco no es una sola canción — es un **álbum completo**, con sus pistas en orden, organizado en carpetas dentro de la Raspberry Pi. Sacás el disco, la música para. Lo volvés a poner, retoma.

<br>

## ✦ Stack técnico

| Capa | Tecnología | Por qué |
|---|---|---|
| **Cerebro** | Raspberry Pi Zero 2W · Raspberry Pi OS Lite | Linux real, manejo simple de archivos y audio, WiFi integrado |
| **Identificación** | PN532 (NFC) vía I2C | Mejor antena que alternativas más baratas, lee y escribe tags |
| **Audio** | MAX98357A (DAC + ampli I2S) | Audio limpio, sin el ruido del jack analógico del Pi |
| **Movimiento** | Motor paso a paso 28BYJ-48 + ULN2003 | Giro preciso, silencioso, bajo consumo |
| **Iluminación** | Anillo WS2812B (NeoPixel) | Glow cálido controlable por software |
| **Backend** | Python · Flask | Liviano, ideal para una Pi Zero, sin build step |
| **Frontend** | HTML / CSS / JS vanilla · PWA instalable | Sin frameworks pesados — interfaz para administrar volumen, luces y álbumes desde el celular |
| **Estructura física** | Sándwich de acrílico cortado a láser | Acabado premium sin necesitar experiencia previa en impresión 3D |

<br>

## ✦ La interfaz

Una PWA instalable (sin necesidad de tienda de apps) para administrar el dispositivo desde el celular — pensada para que la use alguien sin conocimientos técnicos.

<div align="center">
<img src="docs/screenshot-app.png" width="320" alt="Pantalla principal de la app Eco Records">
</div>

> Volumen, iluminación y biblioteca de discos, todo en lenguaje simple — sin tecnicismos, sin configuración compleja.

<br>

## ✦ Estado del proyecto

> 🚧 **En construcción activa** — este es un proyecto en desarrollo, no un producto terminado.

- [x] Raspberry Pi Zero 2W configurada (headless, SSH, WiFi)
- [x] Estructura del proyecto y entorno virtual
- [x] Backend Flask con API REST (`/api/status`, `/api/volume`, `/api/lights`)
- [x] Interfaz PWA con diseño propio (sin frameworks, SVG icons, tipografía custom)
- [x] Rotación del disco animada, sincronizada con play/pause
- [ ] Integración del lector NFC (PN532) — *lector en camino*
- [ ] Audio real vía I2S (MAX98357A)
- [ ] Control del motor paso a paso
- [ ] Anillo de luces WS2812B
- [ ] Carcasa física en acrílico
- [ ] Discos personalizados (NFC + imán + etiqueta)

<br>

## ✦ Estructura del repo

```
eco/
├── app.py                  # Servidor Flask — rutas y lógica de la API
├── config.json              # Mapeo UID de disco → álbum, volumen, luces
├── templates/
│   └── index.html           # Interfaz principal (PWA)
├── static/
│   ├── css/
│   │   └── style.css        # Estilos — paleta cálida, tipografía serif/sans
│   └── js/
│       └── app.js           # Lógica del front: estado, polling, controles
└── albums/                  # Carpetas de música (no versionado — ver .gitignore)
```

<br>

## ✦ Corriendo el proyecto

```bash
# Clonar
git clone https://github.com/Aznar-7/proyect-ecoRecords-pi.git
cd proyect-ecoRecords-pi

# Entorno virtual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Levantar el servidor
python3 app.py
```

La app queda disponible en `http://<ip-de-la-pi>:5000` desde cualquier dispositivo en la misma red.

<br>

## ✦ Por qué este proyecto

Construido desde cero como regalo personalizado — sin atajos de productos comerciales. Cada disco representa algo elegido a propósito; cada parte del dispositivo fue decidida, no comprada hecha.

> *"El objetivo no es solo que funcione — es que se sienta hecho con intención, de principio a fin."*

<br>

---

<div align="center">
<sub>Construido con 🟤 en Córdoba, Argentina</sub>
</div>
