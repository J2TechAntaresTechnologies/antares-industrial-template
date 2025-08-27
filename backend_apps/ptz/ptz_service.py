import os
import cv2
import time
import sys
import torch
import numpy as np
from onvif import ONVIFCamera
import warnings
import threading
import pyaudio
import wave
import json # Para cargar la configuración
import subprocess

# ===================== CONFIG USUARIO (desde constants.py o similar) =====================
# Por ahora, usaremos valores por defecto o los cargaremos de un archivo de configuración
# que crearemos más adelante.
# Para la refactorización, asumiremos que estos valores se pasarán al servicio o se cargarán.
# Ejemplo de configuración por defecto:
DEFAULT_CONFIG = {
    "IP": "192.168.1.19",
    "USER": "admin",
    "PASS": "uijgbv88",
    "RTSP_PORT": 554,
    "RTSP_PATH": "/12",
    "ONVIF_PORT": 8080,
    "USE_CUSTOM_WEIGHTS": False,
    "WEIGHTS": "/path/a/tu/best.pt", # Asegúrate de que esta ruta sea válida si USE_CUSTOM_WEIGHTS es True
    "MODEL_NAME": "yolov5s",
    "YOLO_CONF_THRESHOLD": 0.4, # Umbral de confianza inicial
    "YOLO_IOU_THRESHOLD": 0.45, # Umbral de IoU inicial
    "YOLO_STRIDE_N": 2, # Stride N inicial
    "PAN_SPEED": 0.5,
    "TILT_SPEED": 0.5,
    "ZOOM_SPEED": 0.5,
    "COLOR_PUNTOS": [0, 255, 0],
    "COLOR_LINEAS": [255, 0, 0],
    "GROSOR_PUNTOS": 1,
    "GROSOR_LINEAS": 1,
    "FRAME_WIDTH": 640,
    "FRAME_HEIGHT": 352,
}

# ===================== LOG FILTERS =====================
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore", category=FutureWarning,
                        message=r".*torch\.cuda\.amp\.autocast.*is deprecated.*")

# ===================== Mediapipe =====================
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def draw_custom_landmarks(image, landmarks, connections, color_puntos, color_lineas, grosor_puntos, grosor_lineas):
    mp_drawing.draw_landmarks(
        image=image,
        landmark_list=landmarks,
        connections=connections,
        landmark_drawing_spec=mp_drawing.DrawingSpec(color=color_puntos,
                                                      thickness=grosor_puntos,
                                                      circle_radius=1),
        connection_drawing_spec=mp_drawing.DrawingSpec(color=color_lineas,
                                                       thickness=grosor_lineas)
    )
    return image

# ===================== PTZ =====================
def clamp(val, lo=-1.0, hi=1.0):
    return max(lo, min(hi, val))

class PTZ:
    def __init__(self, ip, port, user, password):
        self.cam = ONVIFCamera(ip, port, user, password)
        self.media = self.cam.create_media_service()
        self.ptz = self.cam.create_ptz_service()
        profiles = self.media.GetProfiles()
        if not profiles:
            raise RuntimeError("ONVIF: no hay perfiles de media")
        self.profile = profiles[0]
        self.token = self.profile.token
        self.has_home = False
        try:
            _ = self.ptz.GetStatus({'ProfileToken': self.token})
            self.has_home = True
        except Exception:
            pass
    def move(self, vx, vy, vz):
        vx, vy, vz = clamp(vx), clamp(vy), clamp(vz)
        req = self.ptz.create_type('ContinuousMove')
        req.ProfileToken = self.token
        req.Velocity = {}
        if vx or vy:
            req.Velocity['PanTilt'] = {'x': vx, 'y': vy}
        if vz:
            req.Velocity['Zoom'] = {'x': vz}
        try:
            self.ptz.ContinuousMove(req)
        except Exception as e:
            print(f"[PTZ] ContinuousMove error: {e}")
    def stop(self, pan_tilt=True, zoom=True):
        try:
            self.ptz.Stop({'ProfileToken': self.token, 'PanTilt': pan_tilt, 'Zoom': zoom})
        except Exception:
            pass
    def goto_home(self):
        try:
            self.ptz.GotoHomePosition({'ProfileToken': self.token})
        except Exception as e:
            print(f"[PTZ] Home no soportado o error: {e}")

# ===================== YOLOv5 =====================
def load_yolov5(use_custom_weights, weights_path, model_name):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        if use_custom_weights:
            model = torch.hub.load("ultralytics/yolov5", "custom", path=weights_path, verbose=False)
        else:
            model = torch.hub.load("ultralytics/yolov5", model_name, pretrained=True, verbose=False)
    except Exception:
        Y5_DIR = str(__import__("pathlib").Path.home() / "yolov5")
        sys.path.insert(0, Y5_DIR)
        raise RuntimeError("No se pudo cargar YOLOv5 con Torch Hub.")
    model.to(device)
    print(f"[YOLOv5] Cargado en {device}.")
    return model, device

def draw_detections(frame, results, names):
    det = results.xyxy[0]
    if det is None or len(det) == 0:
        return frame
    for *xyxy, conf, cls in det:
        x1, y1, x2, y2 = map(int, xyxy)
        c = int(cls.item()) if hasattr(cls, "item") else int(cls)
        label = f"{names[c]} {float(conf):.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), (0, 255, 0), -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    return frame

# ===================== AUDIO =====================
AUDIO_CHUNK = 1024

class AudioStreamer:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.mic_active = False
        self.mic_thread = None
        self.cam_audio_active = False
        self.cam_audio_thread = None

    def _stream_mic_to_rtsp(self):
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True,
                            frames_per_buffer=AUDIO_CHUNK)
            import subprocess
            cmd = [
                "ffmpeg", "-f", "s16le", "-ar", "16000", "-ac", "1", "-i", "-",
                "-f", "rtsp", self.rtsp_url
            ]
            p_ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            while self.mic_active:
                data = stream.read(AUDIO_CHUNK, exception_on_overflow=False)
                p_ff.stdin.write(data)
            p_ff.stdin.close()
            p_ff.wait()
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception as e:
            print(f"[MIC->RTSP] Error: {e}")

    def toggle_mic_stream(self):
        self.mic_active = not self.mic_active
        print(f"[AUDIO] Enviar mic {'ON' if self.mic_active else 'OFF'}")
        if self.mic_active and not self.mic_thread:
            self.mic_thread = threading.Thread(target=self._stream_mic_to_rtsp)
            self.mic_thread.daemon = True
            self.mic_thread.start()
        elif not self.mic_active and self.mic_thread:
            # Esperar a que el hilo termine si es necesario, o simplemente dejar que termine
            self.mic_thread = None # Resetear el hilo para permitir una nueva ejecución

    def _listen_camera_audio(self):
        try:
            import subprocess
            cmd = [
                "ffmpeg", "-i", self.rtsp_url, "-f", "wav", "-acodec", "pcm_s16le",
                "-ac", "1", "-ar", "16000", "-"
            ]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            pya = pyaudio.PyAudio()
            stream = pya.open(format=pya.get_format_from_width(2), channels=1, rate=16000, output=True)
            while self.cam_audio_active:
                data = p.stdout.read(AUDIO_CHUNK)
                if not data:
                    break
                stream.write(data)
            stream.stop_stream()
            stream.close()
            pya.terminate()
            p.terminate()
        except Exception as e:
            print(f"[AUDIO] Error al escuchar audio: {e}")

    def toggle_cam_audio(self):
        self.cam_audio_active = not self.cam_audio_active
        print(f"[AUDIO] Escuchar cámara {'ON' if self.cam_audio_active else 'OFF'}")
        if self.cam_audio_active and not self.cam_audio_thread:
            self.cam_audio_thread = threading.Thread(target=self._listen_camera_audio)
            self.cam_audio_thread.daemon = True
            self.cam_audio_thread.start()
        elif not self.cam_audio_active and self.cam_audio_thread:
            self.cam_audio_thread = None

class PTZCameraService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PTZCameraService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config=None):
        with PTZCameraService._lock:
            if self._initialized:
                return

            self.config = config if config else DEFAULT_CONFIG
            self.rtsp_url = f"rtsp://{self.config['USER']}:{self.config['PASS']}@{self.config['IP']}:{self.config['RTSP_PORT']}{self.config['RTSP_PATH']}"

            self.ptz = None
            self.ffmpeg_process = None # <--- Proceso para FFMPEG
            self.model = None
            self.names = None
            self.face_mesh = None
            self.pose = None
            self.audio_streamer = None

            # Dimensiones del frame
            self.frame_width = self.config["FRAME_WIDTH"]
            self.frame_height = self.config["FRAME_HEIGHT"]

            # Control de estado de las funcionalidades
            self.do_detect = True
            self.do_face = False
            self.do_body = False

            # Parámetros de la aplicación que se pueden modificar en tiempo real
            self.params = {
                "YOLO_CONF_THRESHOLD": self.config["YOLO_CONF_THRESHOLD"],
                "YOLO_IOU_THRESHOLD": self.config["YOLO_IOU_THRESHOLD"],
                "YOLO_STRIDE_N": self.config["YOLO_STRIDE_N"],
                "PAN_SPEED": self.config["PAN_SPEED"],
                "TILT_SPEED": self.config["TILT_SPEED"],
                "ZOOM_SPEED": self.config["ZOOM_SPEED"],
                "GROSOR_PUNTOS": self.config["GROSOR_PUNTOS"],
                "GROSOR_LINEAS": self.config["GROSOR_LINEAS"],
            }

            # Parámetros de dibujo de Mediapipe (pueden seguir en config si no se cambian en real time)
            self.color_puntos = tuple(self.config["COLOR_PUNTOS"])
            self.color_lineas = tuple(self.config["COLOR_LINEAS"])

            self._initialized = True
            self._running = False
            self._frame_lock = threading.Lock()
            self._current_frame = None
            self._last_move_ts = 0.0
            self._move_timeout = 0.25 # Tiempo para detener el movimiento PTZ continuo

            self._setup_camera()

    def _setup_camera(self):
        print("[INFO] Inicializando PTZCameraService...")
        try:
            self.ptz = PTZ(self.config['IP'], self.config['ONVIF_PORT'], self.config['USER'], self.config['PASS'])
            print("[OK] ONVIF listo.")
        except Exception as e:
            print(f"[WARN] ONVIF no disponible: {e}")
            self.ptz = None

        print(f"[INFO] Abriendo RTSP con FFMPEG: {self.rtsp_url}")
        command = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', self.rtsp_url,
            '-loglevel', 'error',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-' # Salida a stdout
        ]
        self.ffmpeg_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if self.ffmpeg_process.poll() is not None:
            print("[ERR] FFMPEG no pudo iniciar. Asegúrate de que ffmpeg está instalado en el sistema.")
            err = self.ffmpeg_process.stderr.read().decode()
            print(f"[FFMPEG ERR] {err}")
            self.ffmpeg_process = None

        print("[INFO] Cargando YOLOv5...")
        try:
            self.model, _ = load_yolov5(self.config['USE_CUSTOM_WEIGHTS'], self.config['WEIGHTS'], self.config['MODEL_NAME'])
            self.names = self.model.names if hasattr(self.model, "names") else {i: f"id{i}" for i in range(1000)}
            self.model.conf = self.params["YOLO_CONF_THRESHOLD"]
            self.model.iou = self.params["YOLO_IOU_THRESHOLD"]
        except Exception as e:
            print(f"[ERR] No se pudo cargar YOLOv5: {e}")
            self.model = None

        self.face_mesh = mp_face_mesh.FaceMesh(max_num_faces=2, refine_landmarks=True,
                                              min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

        self.audio_streamer = AudioStreamer(self.rtsp_url)
        self._running = True
        threading.Thread(target=self._process_frames, daemon=True).start()
        print("[INFO] PTZCameraService inicializado y procesando frames.")

    def _process_frames(self):
        fcount, t0, fps = 0, time.time(), 0.0
        frame_size = self.frame_width * self.frame_height * 3

        while self._running:
            if self.ffmpeg_process is None:
                time.sleep(0.5)
                continue

            raw_frame = self.ffmpeg_process.stdout.read(frame_size)

            if not raw_frame:
                time.sleep(0.01)
                continue

            frame = np.frombuffer(raw_frame, np.uint8).reshape((self.frame_height, self.frame_width, 3))
            processed_frame = frame.copy()

            # --- PTZ continuo (detener si no hay movimiento reciente) ---
            if self.ptz and (time.time() - self._last_move_ts) > self._move_timeout and self._last_move_ts > 0:
                self.ptz.stop()
                self._last_move_ts = 0

            # --- YOLO ---
            fcount += 1
            if self.do_detect and self.model and (fcount % self.params["YOLO_STRIDE_N"] == 0):
                results = self.model(processed_frame, size=640)
                processed_frame = draw_detections(processed_frame, results, self.names)

            # --- Mediapipe FaceMesh ---
            if self.do_face and self.face_mesh:
                rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                results_face = self.face_mesh.process(rgb)
                if results_face.multi_face_landmarks:
                    for fl in results_face.multi_face_landmarks:
                        draw_custom_landmarks(processed_frame, fl, mp_face_mesh.FACEMESH_TESSELATION, self.color_puntos, self.color_lineas, self.params["GROSOR_PUNTOS"], self.params["GROSOR_LINEAS"])
                        draw_custom_landmarks(processed_frame, fl, mp_face_mesh.FACEMESH_CONTOURS, self.color_puntos, self.color_lineas, self.params["GROSOR_PUNTOS"], self.params["GROSOR_LINEAS"])
                        draw_custom_landmarks(processed_frame, fl, mp_face_mesh.FACEMESH_IRISES, self.color_puntos, self.color_lineas, self.params["GROSOR_PUNTOS"], self.params["GROSOR_LINEAS"])

            # --- Mediapipe Pose ---
            if self.do_body and self.pose:
                rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                results_body = self.pose.process(rgb)
                if results_body.pose_landmarks:
                    draw_custom_landmarks(processed_frame, results_body.pose_landmarks, mp_pose.POSE_CONNECTIONS, self.color_puntos, self.color_lineas, self.params["GROSOR_PUNTOS"], self.params["GROSOR_LINEAS"])

            # --- FPS ---
            dt = time.time() - t0
            if dt >= 0.5:
                fps, fcount, t0 = fcount / dt, 0, time.time()
            hud = f"FPS: {fps:.1f} | YOLO:{'ON' if self.do_detect else 'OFF'} | FACE:{'ON' if self.do_face else 'OFF'} | BODY:{'ON' if self.do_body else 'OFF'}"
            cv2.putText(processed_frame, hud, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2, cv2.LINE_AA)

            with self._frame_lock:
                self._current_frame = processed_frame

    def generate_frames(self):
        while self._running:
            try:
                with self._frame_lock:
                    if self._current_frame is None:
                        time.sleep(0.01) # Esperar si no hay frame
                        continue
                    ret, buffer = cv2.imencode('.jpg', self._current_frame)
                    if not ret:
                        continue
                    frame = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.03)
            except (GeneratorExit, BrokenPipeError):
                # El cliente se ha desconectado.
                print("[INFO] Cliente de streaming desconectado.")
                break

    def get_params(self):
        return self.params

    def set_param(self, param_name, value):
        if param_name in self.params:
            self.params[param_name] = value
            # Actualizar yolo model si es necesario
            if param_name == "YOLO_CONF_THRESHOLD" and self.model:
                self.model.conf = value
            elif param_name == "YOLO_IOU_THRESHOLD" and self.model:
                self.model.iou = value
            return {"status": "ok", "param_name": param_name, "value": value}
        return {"error": "Parámetro no válido"}

    def toggle_feature(self, feature_name):
        if feature_name == "yolo":
            self.do_detect = not self.do_detect
            print(f"[YOLO] {'ON' if self.do_detect else 'OFF'}")
            return self.do_detect
        elif feature_name == "face":
            self.do_face = not self.do_face
            print(f"[Face] {'ON' if self.do_face else 'OFF'}")
            return self.do_face
        elif feature_name == "body":
            self.do_body = not self.do_body
            print(f"[Body] {'ON' if self.do_body else 'OFF'}")
            return self.do_body
        return None

    def move_ptz(self, direction):
        vx = vy = vz = 0.0
        if direction == 'w': vy = self.params["TILT_SPEED"]
        elif direction == 's': vy = -self.params["TILT_SPEED"]
        elif direction == 'a': vx = self.params["PAN_SPEED"]
        elif direction == 'd': vx = -self.params["PAN_SPEED"]
        elif direction == 'i': vz = self.params["ZOOM_SPEED"]
        elif direction == 'o': vz = -self.params["ZOOM_SPEED"]

        if self.ptz and (vx or vy or vz):
            self.ptz.move(vx, vy, vz)
            self._last_move_ts = time.time()
            print(f"[PTZ] Moviendo: vx={vx}, vy={vy}, vz={vz}")
            return True
        return False

    def stop_ptz(self):
        if self.ptz:
            self.ptz.stop()
            self._last_move_ts = 0 # Resetear el timestamp para detener el movimiento continuo
            print("[PTZ] Detenido.")
            return True
        return False

    def goto_home_ptz(self):
        if self.ptz:
            self.ptz.goto_home()
            print("[PTZ] Ir a Home.")
            return True
        return False

    def toggle_mic_stream(self):
        if self.audio_streamer:
            self.audio_streamer.toggle_mic_stream()
            return self.audio_streamer.mic_active
        return False

    def toggle_camera_audio(self):
        if self.audio_streamer:
            self.audio_streamer.toggle_cam_audio()
            return self.audio_streamer.cam_audio_active
        return False

    def get_status(self):
        status = {
            "do_detect": self.do_detect,
            "do_face": self.do_face,
            "do_body": self.do_body,
            "mic_active": self.audio_streamer.mic_active if self.audio_streamer else False,
            "cam_audio_active": self.audio_streamer.cam_audio_active if self.audio_streamer else False,
            "ptz_available": self.ptz is not None,
            "yolo_available": self.model is not None,
            "rtsp_open": self.ffmpeg_process is not None and self.ffmpeg_process.poll() is None
        }
        status.update(self.params)
        return status

    def release_resources(self):
        self._running = False
        if self.ffmpeg_process:
            print("[INFO] Deteniendo proceso FFMPEG.")
            self.ffmpeg_process.kill()
        if self.face_mesh:
            self.face_mesh.close()
        if self.pose:
            self.pose.close()
        if self.ptz:
            self.ptz.stop()
        print("[INFO] Recursos de PTZCameraService liberados.")

# Para pruebas directas del servicio (no se usará en el servidor Flask principal)
if __name__ == "__main__":
    # Puedes cargar la configuración desde un archivo JSON si lo deseas
    # with open("config.json", "r") as f:
    #     user_config = json.load(f)
    # service = PTZCameraService(config=user_config)

    service = PTZCameraService() # Usará la configuración por defecto

    print("Servicio PTZ inicializado. Presiona Ctrl+C para salir.")
    try:
        # Mantener el script corriendo para que el hilo de procesamiento de frames funcione
        while True:
            time.sleep(1)
            # Puedes imprimir el estado actual para depuración
            # print(service.get_status())
    except KeyboardInterrupt:
        print("Deteniendo servicio...")
    finally:
        service.release_resources()
        print("Servicio PTZ detenido.")