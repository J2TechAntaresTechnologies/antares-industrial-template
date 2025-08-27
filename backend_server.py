# Mini servidor Flask para ejecutar aplicaciones Python como backend para Antares UI

import os
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from backend_apps.ptz.ptz_service import PTZCameraService
from backend_apps.argneg_contornos.argneg_service import ArgnegService

# --- Forzar TCP para el stream RTSP de OpenCV ---
# Esto a menudo soluciona problemas de conexión cuando UDP está bloqueado o no es fiable.
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'

# Crear la aplicación de Flask
app = Flask(__name__)

# --- Configuración de la cámara para Arneg ---
# CAMBIAR ESTE VALOR si la cámara que quieres usar no es la 0.
# Puedes probar con 0, 1, 2, etc.
ARNEG_CAMERA_INDEX = 1

# Inicializar las instancias de los servicios a None
ptz_service_instance = None
argneg_service_instance = None

# --- Configuración de CORS ---
# Permite que el frontend (ej. http://localhost:5173) se comunique con este backend.
CORS(app, resources={
    r"/api/*": {"origins": ["http://localhost:5173", "http://192.168.1.9:5173"]}, 
    r"/ptz_feed": {"origins": ["http://localhost:5173", "http://192.168.1.9:5173"]}, 
    r"/arneg_feed": {"origins": ["http://localhost:5173", "http://192.168.1.9:5173"]}
}) # En producción, restringe el origen

# Directorio base donde se encuentran las `backend_apps`
# Se asume que este servidor se ejecuta desde la raíz del proyecto.
BASE_APPS_DIR = os.path.join(os.path.dirname(__file__), 'backend_apps')

# ===================== Rutas para la aplicación ARNEG (argneg_contornos) =====================
@app.route('/api/arneg/start', methods=['POST'])
def arneg_start():
    """Inicializa el servicio de Arneg Contornos."""
    global argneg_service_instance
    if argneg_service_instance is None:
        argneg_service_instance = ArgnegService(camera_index=ARNEG_CAMERA_INDEX)
        return jsonify({"status": "Arneg service started"}), 200
    return jsonify({"status": "Arneg service already running"}), 200

@app.route('/api/arneg/stop', methods=['POST'])
def arneg_stop():
    """Detiene y libera los recursos del servicio de Arneg Contornos."""
    global argneg_service_instance
    if argneg_service_instance:
        argneg_service_instance.release_resources()
        argneg_service_instance = None
        return jsonify({"status": "Arneg service stopped"}), 200
    return jsonify({"status": "Arneg service not running"}), 200

@app.route('/arneg_feed')
def arneg_feed():
    """Ruta para el streaming de video MJPEG de la cámara Arneg."""
    if argneg_service_instance is None:
        return Response("Arneg service not started", status=503, mimetype='text/plain')
    return Response(argneg_service_instance.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/arneg/status', methods=['GET'])
def arneg_status():
    """Obtiene el estado actual de la aplicación Arneg (parámetros)."""
    if argneg_service_instance is None:
        return jsonify({"status": "stopped", "message": "Arneg service not running."})
    return jsonify(argneg_service_instance.get_status())

@app.route('/api/arneg/set_param', methods=['POST'])
def arneg_set_param():
    """Establece un parámetro específico de la aplicación Arneg."""
    if argneg_service_instance is None:
        return jsonify({"error": "Arneg service not started"}), 400
    data = request.json
    param_name = data.get('param_name')
    value = data.get('value')
    result = argneg_service_instance.set_param(param_name, int(value))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

# ===================== Fin de Rutas para la aplicación ARNEG =====================


# ===================== Rutas para la aplicación PTZ =====================
@app.route('/api/ptz/start', methods=['POST'])
def ptz_start():
    """Inicializa el servicio de la cámara PTZ."""
    global ptz_service_instance
    if ptz_service_instance is None:
        ptz_service_instance = PTZCameraService()
        return jsonify({"status": "PTZ service started"}), 200
    return jsonify({"status": "PTZ service already running"}), 200

@app.route('/api/ptz/stop_service', methods=['POST'])
def ptz_stop_service():
    """Detiene y libera los recursos del servicio de la cámara PTZ."""
    global ptz_service_instance
    if ptz_service_instance:
        ptz_service_instance.release_resources()
        ptz_service_instance = None
        return jsonify({"status": "PTZ service stopped"}), 200
    return jsonify({"status": "PTZ service not running"}), 200

@app.route('/ptz_feed')
def ptz_feed():
    """Ruta para el streaming de video MJPEG de la cámara PTZ."""
    if ptz_service_instance is None:
        return Response("PTZ service not started", status=503, mimetype='text/plain')
    return Response(ptz_service_instance.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/ptz/status', methods=['GET'])
def ptz_status():
    """Obtiene el estado actual de la aplicación PTZ (toggles, parámetros)."""
    if ptz_service_instance is None:
        return jsonify({"status": "stopped", "message": "PTZ service not running."})
    return jsonify(ptz_service_instance.get_status())

@app.route('/api/ptz/set_param', methods=['POST'])
def ptz_set_param():
    """Establece un parámetro específico de la aplicación PTZ."""
    if ptz_service_instance is None:
        return jsonify({"error": "PTZ service not started"}), 400
    data = request.json
    param_name = data.get('param_name')
    value = data.get('value')
    
    # El valor de los trackbars de la UI suele venir como string, hay que convertirlo.
    # Intentamos convertir a float, y si no, a int.
    try:
        if '.' in str(value):
            final_value = float(value)
        else:
            final_value = int(value)
    except (ValueError, TypeError):
        return jsonify({"error": f"Valor inválido para {param_name}: {value}"}), 400

    result = ptz_service_instance.set_param(param_name, final_value)
    
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/ptz/toggle_feature', methods=['POST'])
def ptz_toggle_feature():
    """Alterna el estado de una característica (YOLO, Face, Body)."""
    if ptz_service_instance is None:
        return jsonify({"error": "PTZ service not started"}), 400
    data = request.json
    feature_name = data.get('feature_name')
    if feature_name in ['yolo', 'face', 'body']:
        new_state = ptz_service_instance.toggle_feature(feature_name)
        return jsonify({"status": "ok", "feature_name": feature_name, "new_state": new_state})
    return jsonify({"error": "Característica no válida"}), 400

@app.route('/api/ptz/move', methods=['POST'])
def ptz_move():
    """Mueve la cámara PTZ en una dirección específica."""
    if ptz_service_instance is None:
        return jsonify({"error": "PTZ service not started"}), 400
    data = request.json
    direction = data.get('direction')
    if direction in ['w', 'a', 's', 'd', 'i', 'o']:
        ptz_service_instance.move_ptz(direction)
        return jsonify({"status": "ok", "direction": direction})
    return jsonify({"error": "Dirección de movimiento no válida"}), 400

@app.route('/api/ptz/stop', methods=['POST'])
def ptz_stop():
    """Detiene el movimiento de la cámara PTZ."""
    if ptz_service_instance is None:
        return jsonify({"error": "PTZ service not started"}), 400
    ptz_service_instance.stop_ptz()
    return jsonify({"status": "ok"})

@app.route('/api/ptz/home', methods=['POST'])
def ptz_home():
    """Mueve la cámara PTZ a su posición de inicio."""
    if ptz_service_instance is None:
        return jsonify({"error": "PTZ service not started"}), 400
    ptz_service_instance.goto_home_ptz()
    return jsonify({"status": "ok"})

@app.route('/api/ptz/toggle_mic', methods=['POST'])
def ptz_toggle_mic():
    """Alterna el streaming de micrófono a la cámara."""
    if ptz_service_instance is None:
        return jsonify({"error": "PTZ service not started"}), 400
    new_state = ptz_service_instance.toggle_mic_stream()
    return jsonify({"status": "ok", "new_state": new_state})

@app.route('/api/ptz/toggle_cam_audio', methods=['POST'])
def ptz_toggle_cam_audio():
    """Alterna la escucha de audio de la cámara."""
    if ptz_service_instance is None:
        return jsonify({"error": "PTZ service not started"}), 400
    new_state = ptz_service_instance.toggle_camera_audio()
    return jsonify({"status": "ok", "new_state": new_state})

# ===================== Fin de Rutas para la aplicación PTZ =====================

# Endpoint de salud para verificar que el servidor está corriendo
@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("--- Servidor Backend de Antares --- ")
    print(f"Sirviendo aplicaciones desde: {os.path.abspath(BASE_APPS_DIR)}")
    print("Aplicaciones disponibles: argneg_contornos, ptz")
    print("Para detener el servidor, presiona CTRL+C")
    app.run(host='0.0.0.0', port=5000, debug=True)