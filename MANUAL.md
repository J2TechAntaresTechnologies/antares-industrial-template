# Manual del Desarrollador: Antares Industrial UI

Este documento proporciona una guía completa para desarrolladores que deseen programar, configurar, extender y mantener la aplicación Antares Industrial UI.

## 1. Visión General de la Arquitectura

La aplicación se compone de un frontend moderno y un backend de Python que sirve a dos aplicaciones especializadas: **Control de Cámara PTZ** y **Análisis de Contornos (Arneg)**.

*   **Frontend**: Una aplicación de una sola página (SPA) construida con **React**, **Vite** y estilizada con **Tailwind CSS**. Es la interfaz con la que el usuario interactúa.
*   **Backend**: Un servidor API construido con **Python** y **Flask**. Gestiona la lógica de las aplicaciones, la comunicación con hardware (cámaras IP, cámaras locales) y el procesamiento de video.

### Diagrama de Flujo de la Arquitectura

```ascii
 [ Usuario en Navegador (localhost:5173) ]
         |
         | HTTP (HTML/CSS/JS)
         v
 +---------------------------------+
 | Frontend Dev Server (Vite)      |
 | (npm run dev) @ :5173           |
 +---------------------------------+
         |
         | API Calls (ej. /api/ptz/move, /api/arneg/set_param)
         v
 +------------------------------------------------+
 | Backend Server (Python/Flask) @ :5000          |
 | (backend_server.py)                            |
 |                                                |
 |  +------------------+  +---------------------+ |
 |  | PTZCameraService |  |    ArgnegService    | |
 |  +------------------+  +---------------------+ |
 +---------+----------+-------------+------------+
           |                        |
(ONVIF/RTSP) |                        | (OpenCV)
           v                        v
     +-----------+            +-----------------+
     | Cámara IP |            | Cámara Local (0,1..)|
     +-----------+            +-----------------+
```

-   El **Frontend** (servido por Vite en el puerto 5173) renderiza la UI.
-   Las acciones del usuario generan **llamadas API** a los endpoints específicos del **Backend** (`/api/ptz/...` o `/api/arneg/...`).
-   El **Backend** (servidor Flask en el puerto 5000) direcciona cada petición al servicio correspondiente:
    -   `PTZCameraService`: Controla una cámara IP vía ONVIF, procesa su stream de video RTSP y ejecuta modelos de IA (YOLO, MediaPipe).
    -   `ArgnegService`: Accede a una cámara local (ej. USB), y realiza análisis de contornos en tiempo real.

---

## 2. Configuración del Entorno de Desarrollo

Para levantar el entorno completo, necesitas tener dos terminales abiertas: una para el frontend y otra para el backend.

### Requisitos Previos

-   **Node.js v18+**
-   **Python 3.8+**
-   **FFmpeg** (debe estar en el PATH del sistema para el stream de la cámara PTZ).

### Pasos de Configuración

1.  **Clonar el Repositorio**:
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd antares-industrial-ui-starter_v1.01
    ```

2.  **Configurar Backend (Python)**:
    ```bash
    # Crear un entorno virtual
    python3 -m venv .venv

    # Activar el entorno virtual
    source .venv/bin/activate

    # Instalar dependencias de Python
    # (Nota: El archivo requirements.txt ha sido actualizado)
    pip install -r requirements.txt
    ```

3.  **Configurar Frontend (Node.js)**:
    ```bash
    # Instalar dependencias de Node.js
    npm install
    ```

4.  **Configurar Variables de Entorno**:
    El frontend necesita saber la dirección del backend.
    ```bash
    # Copia el archivo de ejemplo
    cp .env.sample .env

    # Abre .env y asegúrate de que la URL coincida con tu backend
    # El valor por defecto suele ser correcto.
    VITE_API_BASE=http://localhost:5000
    ```

5.  **Ejecutar la Aplicación**:
    -   **Terminal 1 (Backend)**:
        ```bash
        source .venv/bin/activate
        python backend_server.py
        ```
    -   **Terminal 2 (Frontend)**:
        ```bash
        npm run dev
        ```

Ahora puedes acceder a la aplicación en `http://localhost:5173`.

---

## 3. Estructura del Proyecto

```
.
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
```

---

## 4. Aplicaciones del Backend

El backend gestiona dos aplicaciones principales. La configuración de cada una se encuentra en su respectivo archivo de servicio.

### 4.1. Aplicación de Control de Cámara PTZ

-   **Archivo de Servicio**: `backend_apps/ptz/ptz_service.py`
-   **Descripción**: Controla una cámara IP con capacidades Pan-Tilt-Zoom (PTZ) a través del protocolo ONVIF. Procesa el stream de video RTSP de la cámara para aplicar detección de objetos (YOLO) y seguimiento de personas (MediaPipe). También gestiona audio bidireccional.

#### **Configuración (`ptz_service.py`)**

Debes editar las constantes al principio de este archivo para que coincidan con tu hardware:

-   `ONVIF_IP`, `ONVIF_PORT`, `ONVIF_USER`, `ONVIF_PASS`: Credenciales de acceso ONVIF de la cámara.
-   `RTSP_URL`: URL del stream de video RTSP de la cámara.
-   `YOLO_MODEL_PATH`: Ruta al archivo de pesos del modelo YOLO (`.pt`).
-   `YOLO_CONFIDENCE_THRESHOLD`: Umbral de confianza para la detección de objetos.
-   `LINE_THICKNESS`: Grosor de las cajas de detección.
-   `YOLO_ENABLED`, `FACE_DETECTION_ENABLED`, `BODY_DETECTION_ENABLED`: Banderas para activar/desactivar los modelos de IA.

#### **API Endpoints (`backend_server.py`)**

-   `POST /api/ptz/start`: Inicia el servicio y la conexión con la cámara.
-   `POST /api/ptz/stop_service`: Detiene el servicio y libera los recursos.
-   `GET /ptz_feed`: Stream de video MJPEG para el frontend.
-   `GET /api/ptz/status`: Devuelve el estado actual de los detectores y parámetros.
-   `POST /api/ptz/set_param`: Ajusta un parámetro (ej. `yolo_confidence`).
-   `POST /api/ptz/toggle_feature`: Activa/desactiva una feature (ej. `yolo`, `face`).
-   `POST /api/ptz/move`: Mueve la cámara (`w`, `a`, `s`, `d`, `i` para zoom in, `o` para zoom out).
-   `POST /api/ptz/stop`: Detiene el movimiento.
-   `POST /api/ptz/home`: Mueve la cámara a la posición de inicio.
-   `POST /api/ptz/toggle_mic`: Activa/desactiva el envío de audio del micrófono a la cámara.
-   `POST /api/ptz/toggle_cam_audio`: Activa/desactiva la recepción de audio desde la cámara.

### 4.2. Aplicación de Análisis de Contornos (Arneg)

-   **Archivo de Servicio**: `backend_apps/argneg_contornos/argneg_service.py`
-   **Descripción**: Captura video desde una cámara conectada localmente (ej. una webcam USB) y realiza un análisis de contornos para detectar objetos basándose en su área, brillo y contraste.

#### **Configuración (`backend_server.py` y `argneg_service.py`)**

-   **Índice de la Cámara**: En `backend_server.py`, la variable `ARNEG_CAMERA_INDEX` define qué cámara usar (0 para la primera, 1 para la segunda, etc.).
-   **Parámetros de Detección**: En `argneg_service.py`, puedes ajustar los valores iniciales de los parámetros:
    -   `area_threshold`: Área mínima del contorno para ser considerado válido.
    -   `brightness_threshold`: Umbral de brillo para la binarización de la imagen.
    -   `contrast_value`: Nivel de contraste a aplicar.

#### **API Endpoints (`backend_server.py`)**

-   `POST /api/arneg/start`: Inicia el servicio y la captura de la cámara.
-   `POST /api/arneg/stop`: Detiene el servicio.
-   `GET /arneg_feed`: Stream de video MJPEG para el frontend.
-   `GET /api/arneg/status`: Devuelve el estado actual de los parámetros.
-   `POST /api/arneg/set_param`: Ajusta un parámetro en tiempo real (`area_threshold`, `brightness_threshold`, `contrast_value`).

---

## 5. Gestión de Dependencias

### Frontend (npm)

-   **Añadir**: `npm install <nombre-del-paquete>`
-   **Remover**: `npm uninstall <nombre-del-paquete>`

### Backend (pip)

Asegúrate de tener tu entorno virtual activado (`source .venv/bin/activate`).

-   **Añadir un paquete**:
    ```bash
    pip install <nombre-del-paquete>
    ```
-   **Actualizar `requirements.txt`**:
    ```bash
    pip freeze > requirements.txt
    ```

---

## 6. Troubleshooting Común

-   **Error de CORS**: Si ves errores de CORS en la consola del navegador, asegúrate de que el servidor backend (`backend_server.py`) esté corriendo y que la variable `VITE_API_BASE` en tu archivo `.env` apunte a la dirección correcta (`http://localhost:5000`).

-   **El video de la cámara PTZ no se muestra**:
    1.  Verifica que `ffmpeg` está instalado y accesible en el PATH de tu sistema.
    2.  Asegúrate de que la `RTSP_URL` en `ptz_service.py` es correcta y que la cámara es accesible desde la máquina donde corre el backend.
    3.  Revisa la consola del backend en busca de errores de `ffmpeg` o de conexión.

-   **Comandos PTZ no funcionan**:
    1.  Verifica las credenciales ONVIF (`IP`, `puerto`, `usuario`, `contraseña`) en `ptz_service.py`.
    2.  Asegúrate de que el protocolo ONVIF esté habilitado en la configuración de la cámara.

-   **La cámara Arneg no se encuentra**:
    1.  Asegúrate de que la cámara esté conectada correctamente.
    2.  Prueba cambiar el valor de `ARNEG_CAMERA_INDEX` en `backend_server.py` (puede ser 0, 1, 2...).