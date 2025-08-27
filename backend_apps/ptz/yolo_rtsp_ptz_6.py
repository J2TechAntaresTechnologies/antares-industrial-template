# yolo_rtsp_ptz_v7.py
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

# --------------------- CONFIG ---------------------
IP = "10.42.0.179"
USER = "admin"
PASS = "uijgbv88"
RTSP_PORT = 554
RTSP_PATH = "/12"
ONVIF_PORT = 8080

USE_CUSTOM_WEIGHTS = False
WEIGHTS = "/path/a/tu/best.pt"
MODEL_NAME = "yolov5s"

RTSP_URL = f"rtsp://{USER}:{PASS}@{IP}:{RTSP_PORT}{RTSP_PATH}"

# --------------------- LOG FILTERS -----------------
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore", category=FutureWarning, message=r".*torch\.cuda\.amp\.autocast.*is deprecated.*")

# --------------------- Mediapipe -------------------
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# --------------------- UTIL -----------------------
def clamp(val, lo=-1.0, hi=1.0):
    return max(lo, min(hi, val))

# --------------------- PTZ ------------------------
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

# --------------------- YOLOv5 ---------------------
def load_yolov5():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        if USE_CUSTOM_WEIGHTS:
            model = torch.hub.load("ultralytics/yolov5", "custom", path=WEIGHTS, verbose=False)
        else:
            model = torch.hub.load("ultralytics/yolov5", MODEL_NAME, pretrained=True, verbose=False)
    except Exception as e:
        Y5_DIR = str(__import__("pathlib").Path.home() / "yolov5")
        sys.path.insert(0, Y5_DIR)
        raise RuntimeError("No se pudo cargar YOLOv5 con Torch Hub.")
    model.to(device)
    model.conf = 0.35
    model.iou = 0.45
    model.max_det = 300
    model.classes = None
    model.amp = False
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
        cv2.putText(frame, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    return frame

# --------------------- Mediapipe Draw ----------------
COLOR_PUNTOS = (0, 255, 0)
COLOR_LINEAS = (255, 0, 0)
GROSOR_PUNTOS = 1
GROSOR_LINEAS = 1

def draw_custom_landmarks(image, landmarks, connections):
    mp_drawing.draw_landmarks(
        image=image,
        landmark_list=landmarks,
        connections=connections,
        landmark_drawing_spec=mp_drawing.DrawingSpec(
            color=COLOR_PUNTOS,
            thickness=GROSOR_PUNTOS,
            circle_radius=1
        ),
        connection_drawing_spec=mp_drawing.DrawingSpec(
            color=COLOR_LINEAS,
            thickness=GROSOR_LINEAS
        )
    )
    return image

# --------------------- AUDIO ------------------------
AUDIO_CHUNK = 1024
mic_active = False
mic_buffer = []

def stream_mic_to_buffer():
    global mic_active, mic_buffer
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=AUDIO_CHUNK)
    mic_buffer = []
    try:
        while mic_active:
            data = stream.read(AUDIO_CHUNK)
            mic_buffer.append(data)
    except Exception as e:
        print(f"[MIC->BUFFER] Error: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def send_buffer_to_camera():
    global mic_buffer
    if not mic_buffer:
        print("[MIC->RTSP] No hay audio para enviar.")
        return
    # Guardamos en WAV temporal
    filename = "mic_buffer.wav"
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)
    wf.writeframes(b''.join(mic_buffer))
    wf.close()
    print(f"[MIC->RTSP] Enviando audio a cámara ({filename})...")
    # Aquí podrías integrar ONVIF SendAudio si tu cámara lo soporta
    mic_buffer = []

def toggle_cam_audio():
    global cam_audio_on
    cam_audio_on = not getattr(toggle_cam_audio, "cam_audio_on", False)
    setattr(toggle_cam_audio, "cam_audio_on", cam_audio_on)
    print(f"[AUDIO] Escuchar cámara {'ON' if cam_audio_on else 'OFF'}")

# --------------------- MAIN ------------------------
def main():
    global mic_active

    # --- PTZ ---
    try:
        ptz = PTZ(IP, ONVIF_PORT, USER, PASS)
        print("[OK] ONVIF listo.")
    except Exception as e:
        print(f"[WARN] ONVIF no disponible: {e}")
        ptz = None

    # --- Video ---
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("[ERR] No se pudo abrir el RTSP.")
        sys.exit(1)

    # --- YOLOv5 ---
    model, device = load_yolov5()
    names = model.names if hasattr(model, "names") else {i: f"id{i}" for i in range(1000)}

    # --- Mediapipe ---
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=2, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5)
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    win = "IPCam + PTZ + YOLOv5 + Face+Body"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    def nothing(_): pass
    cv2.createTrackbar("Pan Speed",  win, 50, 100, nothing)
    cv2.createTrackbar("Tilt Speed", win, 50, 100, nothing)
    cv2.createTrackbar("Zoom Speed", win, 50, 100, nothing)
    cv2.createTrackbar("Conf x100",  win, int(model.conf*100), 100, nothing)
    cv2.createTrackbar("IoU x100",   win, int(model.iou*100),  100, nothing)
    cv2.createTrackbar("Stride N",   win, 2, 8, nothing)

    last_move_ts, move_timeout = 0.0, 0.25
    do_detect, do_face, do_body = True, False, False
    fcount, t0, fps = 0, time.time(), 0.0

    print("[INFO] Controles: WASD mueve | I/O zoom | SPACE Stop | H Home | T toggle YOLO | F toggle Face | B toggle Body | U toggle audio cámara | J presionar/suelta mic | ESC salir")

    prev_j_state = False
    mic_thread = None

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        key = cv2.waitKey(1) & 0xFF
        pan_speed = cv2.getTrackbarPos("Pan Speed", win)/100.0
        tilt_speed = cv2.getTrackbarPos("Tilt Speed", win)/100.0
        zoom_speed = cv2.getTrackbarPos("Zoom Speed", win)/100.0
        model.conf = cv2.getTrackbarPos("Conf x100", win)/100.0
        model.iou  = max(0.05, cv2.getTrackbarPos("IoU x100", win)/100.0)
        strideN    = max(1, cv2.getTrackbarPos("Stride N", win))

        # --- PTZ ---
        vx = vy = vz = 0.0
        if key == ord('w'): vy = tilt_speed
        elif key == ord('s'): vy = -tilt_speed
        if key == ord('a'): vx = pan_speed
        elif key == ord('d'): vx = -pan_speed
        if key == ord('i'): vz = zoom_speed
        elif key == ord('o'): vz = -zoom_speed
        if key == 32:  # SPACE
            if ptz: ptz.stop()
        elif key in (ord('h'), ord('H')):
            if ptz: ptz.goto_home()
        elif key in (ord('t'), ord('T')): do_detect = not do_detect
        elif key in (ord('f'), ord('F')): do_face = not do_face
        elif key in (ord('b'), ord('B')): do_body = not do_body
        elif key in (ord('u'), ord('U')): toggle_cam_audio()

        if ptz and (time.time() - last_move_ts) > move_timeout and (vx or vy or vz):
            ptz.move(vx, vy, vz)
            last_move_ts = time.time()

        # --- J mic ---
        j_pressed = key in (ord('j'), ord('J'))
        if j_pressed and not prev_j_state:
            # Inicia mic
            print("[AUDIO] Micrófono ON")
            mic_active = True
            mic_thread = threading.Thread(target=stream_mic_to_buffer, daemon=True)
            mic_thread.start()
        elif not j_pressed and prev_j_state:
            # Se soltó J
            mic_active = False
            if mic_thread:
                mic_thread.join()
            print("[AUDIO] Micrófono OFF / enviando buffer...")
            send_buffer_to_camera()
        prev_j_state = j_pressed

        # --- Detección ---
        if do_detect:
            results = model(frame)
            frame = draw_detections(frame, results, names)

        # --- Face ---
        if do_face:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)
            if res.multi_face_landmarks:
                for lm in res.multi_face_landmarks:
                    frame = draw_custom_landmarks(frame, lm, mp_face_mesh.FACEMESH_TESSELATION)

        cv2.imshow(win, frame)

        if key == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

