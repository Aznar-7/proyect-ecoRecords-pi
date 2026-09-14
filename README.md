<div align="center">

# 🎵 Eco Records

### Un tocadiscos NFC hecho a mano, disco por disco

*Apoyás un disco. Bajás el brazo. Suena la música.*

[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Zero%202W-C51A4A?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Status](https://img.shields.io/badge/status-en%20construcción-C4956A?style=flat-square)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)]()

</div>

---

## ✦ Qué es esto

**Eco Records** es un tocadiscos físico construido desde cero: cada disco representa un álbum completo. Lo apoyás sobre el plato, un lector NFC oculto identifica cuál es, y cuando bajás el brazo mecánico hasta el borde del disco —como en un tocadiscos real— arranca a girar y suena la música en estéreo.

No hay pantalla obligatoria. No hace falta el celular para usarlo — apoyás el disco, bajás el brazo, y listo. La webapp existe como panel de control opcional (biblioteca de álbumes, agregar música nueva), no como forma principal de uso.

Diseñado, programado y construido enteramente a mano como regalo personalizado, con estética vintage de madera. Sin compras de productos terminados — cada decisión de hardware, cada línea de código, cada pieza de la carcasa es parte del proyecto.

<br>

## ✦ Cómo funciona

```
   disco apoyado
        │
        ▼
  lector NFC (PN532) identifica el álbum — pero no reproduce todavía
        │
        ▼
  se baja el brazo hasta el borde del disco
        │
        ▼
  sensor Hall detecta el imán de la punta
        │
        ├──► motor gira el plato
        └──► arranca el audio en estéreo (2× MAX98357A)

  se levanta el brazo → pausa · se retira el disco → corte total
```

Cada disco es un **álbum completo**, con sus pistas en orden. El gesto de bajar el brazo es el que dispara la reproducción — igual que "poner la aguja" en un tocadiscos real, no un simple sensor de presencia.

<br>

## ✦ Stack técnico

| Capa | Tecnología | Por qué |
|---|---|---|
| **Cerebro** | Raspberry Pi Zero 2W · Raspberry Pi OS Lite | Linux real, manejo simple de archivos y audio, WiFi integrado |
| **Alimentación** | UPS HAT (batería LiPo + Pogo Pin) | Apagado seguro ante cortes de luz, sin perder la SD |
| **Identificación** | PN532 (NFC) vía I2C | Identifica el álbum; el sensor Hall dispara la reproducción real |
| **Gatillo mecánico** | Sensor Hall + imán en la punta del brazo | Replica el gesto de "bajar la aguja" de un tocadiscos real |
| **Audio** | 2× MAX98357A (DAC + ampli I2S) | Un canal por chip, audio digital limpio vía I2S |
| **Movimiento** | Motor paso a paso 28BYJ-48 + ULN2003 | Giro sincronizado con la reproducción, controlado por GPIO |
| **Backend** | Python · Flask · systemd | Liviano, ideal para una Pi Zero; arranca solo al encender, se autorecupera de fallos |
| **Frontend** | HTML / CSS / JS vanilla · PWA instalable | Biblioteca de álbumes y descarga de música nueva desde el celular, con HTTPS propio |
| **Acceso remoto** | Cloudflare Tunnel + dominio propio | HTTPS automático, instalable como app real en cualquier celular |
| **Estructura física** | Carcasa impresa en 3D (diseño propio en Fusion 360) + tapa de acrílico con bisagra | Estética cálida de madera, cámaras acústicas selladas para cada parlante |

<br>

## ✦ La interfaz

Una PWA instalable (sin necesidad de tienda de apps) — biblioteca de discos y descarga de álbumes nuevos pegando un link de YouTube. El uso diario del objeto no depende de ella: se usa apoyando discos y bajando el brazo.

<br>

## ✦ Estado del proyecto

> 🚧 **En construcción activa** — el software y la electrónica funcionan de punta a punta; queda terminar el armado físico definitivo.

- [x] Raspberry Pi Zero 2W configurada (headless, SSH, WiFi, servicios systemd)
- [x] Backend Flask con API REST completa
- [x] Interfaz PWA instalable con HTTPS (Cloudflare Tunnel + dominio propio)
- [x] Integración del lector NFC (PN532), detección estable con debounce
- [x] Audio real vía I2S, 2 amplificadores (MAX98357A) para estéreo
- [x] Control del motor paso a paso, sincronizado con la reproducción
- [x] Sensor Hall integrado como gatillo real de play/pausa (needle down/up)
- [x] UPS HAT con batería de respaldo, para apagado seguro ante cortes de luz
- [x] Descarga de álbumes vía YouTube directo desde la webapp
- [x] Diseño 3D completo de la carcasa (Fusion 360): cámaras acústicas selladas, plataforma del disco, pivote del brazo, tapa con bisagra
- [x] Discos personalizados (vinilos decorativos + tag NFC + imán pegados abajo)
- [x] Impresión 3D final y armado de la carcasa
- [x] Ajuste fino de estéreo real (selección de canal izquierdo/derecho)
- [ ] Mejoras UI (porcentaje bateria, mejoras de QOL, estadisticas)
- [ ] Panel de conexion WIFI como puerto de conexion cuando no esta conectado a nada
- [ ] Control de volumen por software
- [ ] Packaging de los álbumes (fundas tipo vinilo)

<br>

## ✦ Estructura del repo

```
eco/
├── app.py                  # Servidor Flask — rutas y lógica de la API
├── daemon.py                # Daemon principal — NFC, Hall, audio, motor
├── config.json               # Mapeo UID de disco → álbum, estado en vivo
├── templates/
│   └── index.html            # Interfaz principal (PWA)
├── static/
│   ├── css/style.css         # Estilos — paleta cálida, tipografía serif/sans
│   ├── js/app.js              # Lógica del front: estado, polling, controles
│   ├── manifest.json          # Manifest de la PWA
│   ├── sw.js                  # Service worker (caché offline)
│   └── icons/                 # Íconos de la PWA (no versionados, se regeneran)
└── albums/                   # Carpetas de música (no versionado — ver .gitignore)
```

<br>

## ✦ Corriendo el proyecto

```bash
# Clonar
git clone https://github.com/Aznar-7/proyect-ecoRecords-pi.git eco
cd eco

# Entorno virtual
python3 -m venv venv
source venv/bin/activate
sudo apt install -y sox libsox-fmt-mp3
pip install flask adafruit-circuitpython-pn532 mutagen RPi.GPIO gpiozero lgpio yt-dlp pi-ina219

# Levantar el servidor y el daemon
python3 app.py        # en una terminal
python3 daemon.py     # en otra
```

En producción, ambos corren como servicios `systemd` que arrancan solos al encender la Pi.

<br>

## ✦ Por qué este proyecto

Construido desde cero como regalo personalizado — sin atajos de productos comerciales. Cada disco representa algo elegido a propósito; cada parte del dispositivo, desde el circuito hasta el gesto de bajar el brazo, fue decidida, no comprada hecha.

> *"El objetivo no es solo que funcione — es que se sienta hecho con intención, de principio a fin."*

<br>

---

<div align="center">
<sub>Construido con 🟤 en Córdoba, Argentina</sub>
</div>
