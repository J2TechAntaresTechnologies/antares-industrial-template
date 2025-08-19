# Antares Industrial UI Starter

Este proyecto es un starter kit para construir interfaces de usuario (UI) para aplicaciones industriales. Utiliza un frontend moderno con **React, Vite y Tailwind CSS**, y lo combina con un **backend de Python (Flask)** que permite ejecutar y visualizar los resultados de scripts de Python directamente en la UI.

Es ideal para crear dashboards de monitoreo, paneles de control para maquinaria, o cualquier aplicación que necesite una interfaz web para interactuar con procesos de backend.

## Características Principales

- **Stack Frontend Moderno:** React + Vite para una experiencia de desarrollo rápida y eficiente.
- **Estilos con Tailwind CSS:** Framework CSS "utility-first" para crear diseños personalizados rápidamente.
- **Backend Integrado:** Servidor Flask (Python) listo para ejecutar aplicaciones y scripts.
- **Arquitectura Modular para Apps:** Permite añadir nuevas "aplicaciones" de Python de forma sencilla, las cuales se pueden ejecutar desde la UI.
- **Páginas Incluidas:**
  - **Dashboard:** Vista general del estado del sistema.
  - **Parámetros:** Visualización y edición de parámetros.
  - **Diagnóstico PLC:** Herramientas para verificar la comunicación con dispositivos.
  - **Logs:** Visualizador de eventos.
- **Variables de Entorno:** Fácil configuración para apuntar a diferentes backends.

## Requisitos Previos

- **Node.js v18+:** Obligatorio para el frontend.
- **Python 3.8+:** Obligatorio para el backend.

## Guía de Inicio Rápido

Sigue estos pasos para poner en marcha el entorno de desarrollo completo (frontend y backend).

### 1. Clonar y Configurar el Proyecto

```bash
# Clona este repositorio
git clone <URL_DEL_REPOSITORIO>
cd antares-industrial-ui-starter

# Instala las dependencias del frontend
npm install

# Instala las dependencias del backend
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

Debes iniciar tanto el servidor de desarrollo del frontend como el servidor del backend.

**En una terminal, inicia el frontend:**

```bash
# Inicia el servidor de desarrollo de Vite en http://localhost:5173
npm run dev
```

**En otra terminal, inicia el backend:**

```bash
# Inicia el servidor de Flask en http://localhost:5000
python backend_server.py
```

Ahora puedes abrir tu navegador en `http://localhost:5173` para ver la aplicación.

## Cómo Añadir Nuevas Aplicaciones Python

Este starter kit está diseñado para ser modular. Puedes añadir tus propios scripts de Python y ejecutarlos desde la interfaz. Para una guía detallada, consulta el documento:

**[Guía para Integrar Nuevas Aplicaciones](INTEGRATING_NEW_APPS.md)**

El proceso se resume en:
1.  Crear una nueva carpeta en `backend_apps/` con tu script `main.py`.
2.  Crear un nuevo componente de React en `src/components/` para tu nueva página.
3.  Añadir la ruta en `src/App.jsx` y un enlace en `src/components/Sidebar.jsx`.

## Estructura del Proyecto

```
.
├── backend_apps/         # Contenedor para tus aplicaciones de Python
│   └── argneg_contornos/
│       └── main.py
├── src/                  # Código fuente del frontend (React)
│   ├── components/       # Componentes de React (páginas, botones, etc.)
│   ├── hooks/            # Hooks personalizados
│   └── ...
├── .env                  # Variables de entorno (no subir a Git)
├── backend_server.py     # El servidor de API (Flask)
├── index.html            # Punto de entrada para Vite
├── package.json          # Dependencias y scripts del frontend
├── requirements.txt      # Dependencias del backend (Python)
└── vite.config.js        # Configuración de Vite
```

## Despliegue (Deploy)

Para desplegar la aplicación en un entorno de producción:

1.  **Compila el frontend:**
    ```bash
    npm run build
    ```
    Esto generará una carpeta `dist/` con los archivos estáticos de la UI.

2.  **Sirve los archivos estáticos:**
    Puedes configurar un servidor web como Nginx o Apache para servir los archivos de la carpeta `dist/`.

3.  **Ejecuta el backend en producción:**
    Utiliza un servidor de aplicaciones WSGI como Gunicorn o uWSGI para ejecutar `backend_server.py` de forma robusta.
    ```bash
    # Ejemplo con Gunicorn
    gunicorn --workers 4 --bind 0.0.0.0:5000 backend_server:app
    ```

## Notas de Seguridad

- **HTTPS:** Utiliza siempre HTTPS en entornos de producción.
- **CORS:** En producción, ajusta la configuración de CORS en `backend_server.py` para permitir solo el dominio de tu frontend, en lugar de `*`.
- **Validación de Entradas:** El endpoint `/api/run/<app_name>` tiene una validación básica para prevenir ataques de *path traversal*. Revísala y adáptala si es necesario.
- **Datos Sensibles:** Nunca expongas claves de API, tokens u otras credenciales en el código del frontend.
