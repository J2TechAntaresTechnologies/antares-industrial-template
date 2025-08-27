# Antares Industrial UI Starter

Este proyecto es un starter kit para construir interfaces de usuario (UI) para aplicaciones industriales. Utiliza un frontend moderno con **React, Vite y Tailwind CSS**, y lo combina con un **backend de Python (Flask)** que permite ejecutar y visualizar los resultados de scripts de Python directamente en la UI.

Es ideal para crear dashboards de monitoreo, paneles de control para maquinaria, o cualquier aplicación que necesite una interfaz web para interactuar con procesos de backend.

## Características Principales

- **Stack Frontend Moderno:** React + Vite para una experiencia de desarrollo rápida y eficiente.
- **Estilos con Tailwind CSS:** Framework CSS "utility-first" para crear diseños personalizados rápidamente.
- **Backend Integrado:** Servidor Flask (Python) listo para ejecutar aplicaciones y scripts.
- **Control de Cámara PTZ:** Integración avanzada para control de cámaras Pan-Tilt-Zoom (PTZ) con detección de objetos (YOLO) y seguimiento facial/corporal (MediaPipe) directamente desde la UI.
- **Arquitectura Modular para Apps:** Permite añadir nuevas "aplicaciones" de Python de forma sencilla, las cuales se pueden ejecutar desde la UI.

## Requisitos Previos

- **Node.js v18+:** Para el frontend.
- **Python 3.8+:** Para el backend.
- **FFmpeg:** Para el procesamiento de video RTSP. Debe estar instalado y accesible en el PATH del sistema.

## Arquitectura de la Aplicación

La aplicación sigue un modelo cliente-servidor desacoplado, ideal para desarrollo y despliegue flexibles.

-   **Frontend:** Una aplicación de una sola página (SPA) construida con React y Vite. Se ejecuta en el navegador del usuario y es servida por un servidor de desarrollo de Vite en el puerto `5173`. Se encarga de toda la interfaz de usuario.
-   **Backend:** Un servidor de API construido con Python y Flask. Se ejecuta en el puerto `5000` y expone varios endpoints para controlar la lógica de negocio, como el control de la cámara PTZ.
-   **Comunicación:** El frontend se comunica con el backend a través de llamadas API REST. Para el video, el backend utiliza `ffmpeg` para capturar el stream RTSP de la cámara y lo retransmite al frontend como un stream MJPEG.

Aquí un diagrama de flujo simplificado:

```ascii
 [ Usuario en Navegador (localhost:5173) ]
         |
         | HTTP (HTML/CSS/JS)
         v
 +---------------------------------+
 | Frontend Dev Server (Vite)      |
 | (npm run dev) @ :5173           |
 +-----------------+---------------+
         |         ^
 (API Calls) |         | (Video Stream /ptz_feed)
         v         |
 +-----------------+---------------+
 | Backend Server (Python/Flask)   |-----> [ ONVIF (Comandos PTZ) ] --->+
 | (backend_server.py) @ :5000     |                                    |
 +---------------------------------+                                    |
         |                                                              |
         | (Lanza FFMPEG)                                               v
         |                                                        +-----------+
         +-----> [ FFMPEG Subproceso ] -> [ RTSP (Video Stream) ] ->| Cámara IP |
                                                                  +-----------+
```

## Guía de Inicio Rápido

Sigue estos pasos para poner en marcha el entorno de desarrollo completo.

### 1. Clonar y Configurar el Proyecto

```bash
# Clona este repositorio
git clone <URL_DEL_REPOSITORIO>
cd antares-industrial-ui-starter

# Instala las dependencias del frontend
npm install

# Crea un entorno virtual para Python e instala las dependencias del backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuración del Entorno

El frontend necesita saber dónde se está ejecutando el backend.

```bash
# 1. Copia el archivo de ejemplo .env.sample a .env
cp .env.sample .env

# 2. Abre el archivo .env y asegúrate de que la variable VITE_API_BASE
# apunte a la URL de tu backend.
# Por defecto, es http://localhost:5000, que es donde correrá el servidor de Python.
VITE_API_BASE=http://localhost:5000
```

### 3. Ejecución

Debes iniciar tanto el servidor de desarrollo del frontend como el servidor del backend, cada uno en su propia terminal.

**Terminal 1: Iniciar Frontend**

```bash
# Inicia el servidor de desarrollo de Vite en http://localhost:5173
npm run dev
```

**Terminal 2: Iniciar Backend**

```bash
# Activa el entorno virtual (si no lo has hecho)
source .venv/bin/activate

# Inicia el servidor de Flask en http://localhost:5000
python backend_server.py
```

Ahora puedes abrir tu navegador en `http://localhost:5173` para ver la aplicación.

## Cómo Añadir Nuevas Aplicaciones Python

Este starter kit está diseñado para ser modular. Puedes añadir tus propios scripts de Python y ejecutarlos desde la interfaz. Para una guía detallada, consulta el documento:

**[Guía para Integrar Nuevas Aplicaciones](INTEGRATING_NEW_APPS.md)**

## Estructura del Proyecto

```
├── backend_apps/
│   ├── argneg_contornos/ # Aplicación de análisis de contornos
│   │   └── argneg_service.py
│   └── ptz/              # Aplicación de control de cámara PTZ
│       └── ptz_service.py
├── src/                  # Código fuente del frontend (React)
│   ├── components/
│   │   ├── PagePtzCamera.jsx
│   │   └── PageArneg.jsx
│   ├── App.jsx
│   └── main.jsx
├── .env
├── backend_server.py     # Servidor principal de la API (Flask)
├── package.json
├── requirements.txt      # Dependencias del backend (pip)
└── MANUAL.md             # Este manual