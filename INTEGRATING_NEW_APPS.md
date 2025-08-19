# Guía para Integrar Nuevas Aplicaciones Python en la UI

Este documento describe el procedimiento para añadir una nueva página (solapa) en la interfaz de Antares que permita ejecutar un script de Python alojado en el servidor y visualizar el resultado. El objetivo es crear un método modular y escalable.

## Arquitectura General

La integración se basa en tres partes principales:

1.  **Frontend (React)**: Un nuevo componente de React que define la página, un botón para iniciar la acción y un área para mostrar los resultados.
2.  **Backend (API)**: Un endpoint genérico en la API del backend (hecho en Flask/Python) que recibe la solicitud del frontend, ejecuta el script de Python correspondiente y devuelve la salida.
3.  **Scripts de Aplicación**: Los scripts de Python que se quieren ejecutar, organizados en una estructura de carpetas específica.

---

## Paso 1: Estructura de Directorios para las Apps

Para mantener el proyecto organizado, todos los scripts de las nuevas aplicaciones se alojarán en un directorio principal llamado `backend_apps` en la raíz del proyecto.

Cada nueva aplicación debe tener su propio subdirectorio dentro de `backend_apps`. El nombre de este subdirectorio servirá como su identificador único (`app_name`).

**Estructura Requerida:**

```
/home/jim/enviroments/antares_app/v1/antares-industrial-ui-starter_v1.01/
├── backend_apps/
│   ├── mi_primera_app/
│   │   └── main.py
│   └── otra_app/
│       └── main.py
├── src/
│   └── ...
└── README.md
```

- **`backend_apps/`**: Directorio contenedor en la raíz del proyecto.
- **`<app_name>/`** (ej. `mi_primera_app`): Directorio para una aplicación específica.
- **`main.py`**: El script de Python que se ejecutará. Debe ser el punto de entrada principal.

## Paso 2: Creación del Endpoint Genérico en el Backend

En tu aplicación de backend (asumimos que es Flask), necesitas un endpoint dinámico que pueda ejecutar cualquier script de las `backend_apps` basándose en su nombre.

**Ejemplo de endpoint en Flask (`app.py` del backend):**

```python
import subprocess
import os
from flask import Flask, jsonify

# Asume que esta es tu app de Flask
app = Flask(__name__)

# Directorio base donde se encuentran las apps
# La ruta debe ser absoluta o relativa al script del backend
BASE_APPS_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend_apps')

@app.route('/api/run/<app_name>', methods=['POST'])
def run_python_app(app_name):
    """Ejecuta el script main.py de una app específica."""
    try:
        app_path = os.path.join(BASE_APPS_DIR, app_name)

        # --- Medida de Seguridad --- #
        # Validar que el app_name sea alfanumérico para evitar ataques de path traversal
        if not app_name.isalnum() or not os.path.isdir(app_path):
            return jsonify({"error": f"Aplicación no encontrada o nombre inválido: {app_name}"}), 404

        script_path = os.path.join(app_path, 'main.py')

        # Ejecutar el script usando subprocess
        # Se recomienda usar un timeout
        result = subprocess.run(
            ['python3', script_path],
            capture_output=True,
            text=True,
            timeout=30 # Timeout de 30 segundos
        )

        # Devolver la salida estándar o el error
        if result.returncode == 0:
            return jsonify({"output": result.stdout})
        else:
            return jsonify({"error": result.stderr}), 500

    except FileNotFoundError:
        return jsonify({"error": f"El script main.py no se encontró para la app: {app_name}"}), 404
    except subprocess.TimeoutExpired:
        return jsonify({"error": "La ejecución del script tardó demasiado tiempo."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ... resto de tu app Flask
```

**⚠️ Advertencia de Seguridad:** Ejecutar scripts a través de `subprocess` es una operación delicada. Asegúrate de validar y sanear siempre el `app_name` para prevenir que un usuario malicioso pueda ejecutar comandos arbitrarios en tu servidor.

## Paso 3: Modificaciones en el Frontend (React)

Ahora, vamos a crear la página en la interfaz de React.

### 3.1. Crear el Componente para la Nueva Página

Crea un nuevo archivo para tu componente en `src/components/`. Por ejemplo, `MiPrimeraApp.jsx`.

**`src/components/MiPrimeraApp.jsx`:**
```jsx
import React, { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000';

export default function MiPrimeraApp() {
  const [output, setOutput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleExecute = async () => {
    setIsLoading(true);
    setOutput('');
    try {
      const response = await fetch(`${API_BASE}/api/run/mi_primera_app`, {
        method: 'POST',
      });
      const data = await response.json();
      if (response.ok) {
        setOutput(data.output);
      } else {
        setOutput(`Error: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Error de conexión: ${error.message}`);
    }
    setIsLoading(false);
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Mi Primera Aplicación</h1>
      <p className="mb-4">Haz clic en el botón para ejecutar el script `main.py` en el backend.</p>
      <button
        onClick={handleExecute}
        disabled={isLoading}
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:bg-gray-400"
      >
        {isLoading ? 'Ejecutando...' : 'Ejecutar Script'}
      </button>
      <div className="mt-4 p-2 bg-gray-900 text-white font-mono rounded">
        <h2 className="font-bold">Resultado:</h2>
        <pre>{output}</pre>
      </div>
    </div>
  );
}
```

### 3.2. Añadir el Enlace en la Barra de Navegación

Modifica el archivo `src/components/Sidebar.jsx` para añadir un nuevo objeto al array `LINKS`.

**`src/components/Sidebar.jsx`:**
```jsx
// ... import

const LINKS = [
  { path: '/', label: 'Dashboard' },
  { path: '/test', label: 'test' },
  { path: '/parameters', label: 'Parámetros' },
  { path: '/plc', label: 'Diagnóstico PLC' },
  { path: '/logs', label: 'Logs' },
  // --- AÑADIR ESTA LÍNEA ---
  { path: '/mi-primera-app', label: 'Mi Primera App' },
];

// ... resto del componente
```

### 3.3. Añadir la Ruta en el Enrutador Principal

Finalmente, modifica `src/App.jsx` para que renderice tu nuevo componente cuando la ruta coincida.

**`src/App.jsx`:**
```jsx
// ... imports
import Logs from './components/Logs.jsx';
import Login from './components/Login.jsx';
// --- AÑADIR ESTA LÍNEA ---
import MiPrimeraApp from './components/MiPrimeraApp.jsx';

export default function App(){
  // ... hooks y lógica existente

  const render = () => {
    if(route === '/') return <Dashboard />;
    if(route === '/parameters') return <Parameters />;
    if(route === '/plc') return <PlcDiag />;
    if(route === '/logs') return <Logs />;
    // --- AÑADIR ESTA LÍNEA ---
    if(route === '/mi-primera-app') return <MiPrimeraApp />;
    return <div className="p-4">Pantalla en construcción</div>;
  };

  // ... resto del componente
}
```

---

## Resumen del Flujo de Trabajo

Una vez completada la configuración inicial (Pasos 1 y 2), el proceso para añadir nuevas aplicaciones es el siguiente:

1.  **Crear la App Python**: Crea una nueva carpeta `backend_apps/<nueva_app>` con su `main.py`.
2.  **Crear Componente React**: Crea el archivo `.jsx` para la nueva página en `src/components/`.
3.  **Añadir Enlace**: Agrega la ruta y el nombre en el array `LINKS` de `Sidebar.jsx`.
4.  **Añadir Ruta**: Agrega la condición `if` en la función `render` de `App.jsx`.

¡Y eso es todo! Con esta estructura, puedes añadir tantas aplicaciones como necesites de manera ordenada.