# yolo_rtsp_ptz_v6.py
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
from pynput import keyboard

# ===================== CONFIG USUARIO =====================
#IP = "10.42.0.179"
IP = "192.168.1.19"
USER = "admin"
PASS = "uijgbv88"
RTSP_PORT = 554
RTSP_PATH = "/2"
ONVIF_PORT = 8080

# YOLOv5
USE_CUSTOM_WEIGHTS = False
WEIGHTS = "/path/a/tu/best.pt"
MODEL_NAME = "yolov5s"

RTSP_URL = f"rtsp://{USER}:{PASS}@{IP}:{RTSP_PORT}{RTSP_PATH}"

# ===================== LOG FILTERS =====================
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore", category=FutureWarning,
                        message=r".*torch\.cuda\.amp\.autocast.*is deprecated.*")

# ===================== Mediapipe =====================
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

COLOR_PUNTOS = (0, 255, 0)
COLOR_LINEAS = (255, 0, 0)
GROSOR_PUNTOS = 1
GROSOR_LINEAS = 1

def draw_custom_landmarks(image, landmarks, connections):
    mp_drawing.draw_landmarks(
        image=image,
        landmark_list=landmarks,
        connections=connections,
        landmark_drawing_spec=mp_drawing.DrawingSpec(color=COLOR_PUNTOS,
                                                      thickness=GROSOR_PUNTOS,
                                                      circle_radius=1),
        connection_drawing_spec=mp_drawing.DrawingSpec(color=COLOR_LINEAS,
                                                       thickness=GROSOR_LINEAS)
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
def load_yolov5():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        if USE_CUSTOM_WEIGHTS:
            model = torch.hub.load("ultralytics/yolov5", "custom", path=WEIGHTS, verbose=False)
        else:
            model = torch.hub.load("ultralytics/yolov5", MODEL_NAME, pretrained=True, verbose=False)
    except Exception:
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
        cv2.putText(frame, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    return frame

# ===================== AUDIO =====================
AUDIO_CHUNK = 1024
mic_active = False
mic_thread = None
cam_audio_active = False

def stream_mic_to_rtsp(rtsp_url):
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True,
                        frames_per_buffer=AUDIO_CHUNK)
        import subprocess
        cmd = [
            "ffmpeg", "-f", "s16le", "-ar", "16000", "-ac", "1", "-i", "-",
            "-f", "rtsp", rtsp_url
        ]
        p_ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while mic_active:
            data = stream.read(AUDIO_CHUNK, exception_on_overflow=False)
            p_ff.stdin.write(data)
        p_ff.stdin.close()
        p_ff.wait()
        stream.stop_stream()
        stream.close()
        p.terminate()
    except Exception as e:
        print(f"[MIC->RTSP] Error: {e}")

def toggle_cam_audio():
    global cam_audio_active
    cam_audio_active = not cam_audio_active
    print(f"[AUDIO] Escuchar cámara {'ON' if cam_audio_active else 'OFF'}")
    if cam_audio_active:
        t = threading.Thread(target=listen_camera_audio, args=(RTSP_URL,))
        t.daemon = True
        t.start()

def listen_camera_audio(rtsp_url):
    try:
        import subprocess
        cmd = [
            "ffmpeg", "-i", rtsp_url, "-f", "wav", "-acodec", "pcm_s16le",
            "-ac", "1", "-ar", "16000", "-"
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        pya = pyaudio.PyAudio()
        stream = pya.open(format=pya.get_format_from_width(2), channels=1, rate=16000, output=True)
        while cam_audio_active:
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

# ===================== MAIN =====================
def main():
    print("[INFO] Conectando ONVIF...")
    try:
        ptz = PTZ(IP, ONVIF_PORT, USER, PASS)
        print("[OK] ONVIF listo.")
    except Exception as e:
        print(f"[WARN] ONVIF no disponible: {e}")
        ptz = None

    print(f"[INFO] Abriendo RTSP: {RTSP_URL}")
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("[ERR] No se pudo abrir el RTSP.")
        sys.exit(1)

    print("[INFO] Cargando YOLOv5...")
    model, device = load_yolov5()
    names = model.names if hasattr(model, "names") else {i: f"id{i}" for i in range(1000)}

    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=2, refine_landmarks=True,
                                      min_detection_confidence=0.5, min_tracking_confidence=0.5)
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

    def tb_speed(name): return max(0.05, cv2.getTrackbarPos(name, win) / 100.0)

    last_move_ts, move_timeout = 0.0, 0.25
    do_detect, do_face, do_body = True, False, False
    fcount, t0, fps = 0, time.time(), 0.0

    print("[INFO] Controles: WASD mueve | I/O zoom | SPACE Stop | H Home | T toggle YOLO | F toggle Face | B toggle Body | U toggle audio cámara | J presionar/suelta enviar mic | ESC salir")

    # ===================== Keyboard Listener =====================
    def on_press(key):
        try:
            if key.char.lower() == "u":
                toggle_cam_audio()
        except AttributeError:
            pass

    def on_release(key):
        try:
            if key.char.lower() == "j":
                global mic_active, mic_thread
                mic_active = False
        except AttributeError:
            pass

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    # ===================== Loop principal =====================
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        key = cv2.waitKey(1) & 0xFFFF
        pan_speed, tilt_speed, zoom_speed = tb_speed("Pan Speed"), tb_speed("Tilt Speed"), tb_speed("Zoom Speed")
        model.conf = cv2.getTrackbarPos("Conf x100", win) / 100.0
        model.iou  = max(0.05, cv2.getTrackbarPos("IoU x100", win) / 100.0)
        strideN    = max(1, cv2.getTrackbarPos("Stride N", win))

        # --- PTZ manual ---
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
        if (vx or vy or vz) and ptz:
            ptz.move(vx, vy, vz)
            last_move_ts = time.time()
        if ptz and (time.time() - last_move_ts) > move_timeout and last_move_ts > 0:
            ptz.stop()
            last_move_ts = 0

        # --- Toggles ---
        if key in (ord('t'), ord('T')):
            do_detect = not do_detect
            print(f"[YOLO] {'ON' if do_detect else 'OFF'}")
        if key in (ord('f'), ord('F')):
            do_face = not do_face
            print(f"[Face] {'ON' if do_face else 'OFF'}")
        if key in (ord('b'), ord('B')):
            do_body = not do_body
            print(f"[Body] {'ON' if do_body else 'OFF'}")

        # --- YOLO ---
        fcount += 1
        if do_detect and (fcount % strideN == 0):
            results = model(frame, size=640)
            frame = draw_detections(frame, results, names)

        # --- Mediapipe FaceMesh ---
        if do_face:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results_face = face_mesh.process(rgb)
            if results_face.multi_face_landmarks:
                for fl in results_face.multi_face_landmarks:
                    draw_custom_landmarks(frame, fl, mp_face_mesh.FACEMESH_TESSELATION)
                    draw_custom_landmarks(frame, fl, mp_face_mesh.FACEMESH_CONTOURS)
                    draw_custom_landmarks(frame, fl, mp_face_mesh.FACEMESH_IRISES)

        # --- Mediapipe Pose ---
        if do_body:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results_body = pose.process(rgb)
            if results_body.pose_landmarks:
                draw_custom_landmarks(frame, results_body.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # --- FPS ---
        dt = time.time() - t0
        if dt >= 0.5:
            fps, fcount, t0 = fcount / dt, 0, time.time()
        hud = f"FPS: {fps:.1f} | YOLO:{'ON' if do_detect else 'OFF'} | FACE:{'ON' if do_face else 'OFF'} | BODY:{'ON' if do_body else 'OFF'}"
        cv2.putText(frame, hud, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2, cv2.LINE_AA)

        cv2.imshow(win, frame)
        if key == 27:  # ESC
            break

    if ptz: ptz.stop()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

