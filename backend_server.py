# Mini servidor Flask para ejecutar aplicaciones Python como backend para Antares UI

import subprocess
import os
from flask import Flask, jsonify
from flask_cors import CORS

# Crear la aplicación de Flask
app = Flask(__name__)

# --- Configuración de CORS ---
# Permite que el frontend (ej. http://localhost:5173) se comunique con este backend.
CORS(app, resources={r"/api/*": {"origins": "*"}}) # En producción, restringe el origen

# Directorio base donde se encuentran las `backend_apps`
# Se asume que este servidor se ejecuta desde la raíz del proyecto.
BASE_APPS_DIR = os.path.join(os.path.dirname(__file__), 'backend_apps')

@app.route('/api/run/<app_name>', methods=['POST'])
def run_python_app(app_name):
    """Ejecuta el script main.py de una app específica."""
    try:
        # --- Medida de Seguridad: Sanear el input ---
        # Solo permite nombres de app alfanuméricos para evitar ataques de "path traversal".
        if not app_name.replace('_', '').isalnum():
            return jsonify({"error": f"Nombre de aplicación inválido: {app_name}"}), 400

        app_dir = os.path.join(BASE_APPS_DIR, app_name)
        script_path = os.path.join(app_dir, 'main.py')

        if not os.path.isfile(script_path):
            return jsonify({"error": f"Aplicación no encontrada: {app_name}"}), 404

        # --- Ejecución Segura del Script ---
        result = subprocess.run(
            ['python3', script_path],
            capture_output=True,
            text=True,
            timeout=60  # Timeout de 60 segundos para evitar procesos colgados
        )

        if result.returncode == 0:
            return jsonify({"output": result.stdout})
        else:
            return jsonify({"error": result.stderr}), 500

    except subprocess.TimeoutExpired:
        return jsonify({"error": "La ejecución del script tardó demasiado (timeout)."}), 500
    except Exception as e:
        return jsonify({"error": f"Ocurrió un error inesperado en el servidor: {str(e)}"}), 500

# Endpoint de salud para verificar que el servidor está corriendo
@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("--- Servidor Backend de Antares --- ")
    print(f"Sirviendo aplicaciones desde: {os.path.abspath(BASE_APPS_DIR)}")
    print("Endpoint disponible en: POST http://localhost:5000/api/run/<app_name>")
    print("Para detener el servidor, presiona CTRL+C")
    app.run(host='0.0.0.0', port=5000, debug=True)
