import cv2
import numpy as np
import json
import os
import time

# --- CONFIG ---
preset_folder = "presets"
os.makedirs(preset_folder, exist_ok=True)

preset_files = {
    "1": os.path.join(preset_folder, "preset1.txt"),
    "2": os.path.join(preset_folder, "preset2.txt"),
    "3": os.path.join(preset_folder, "preset3.txt")
}

# --- CONFIG por defecto ---
def default_config():
    return {
        "Canny Th1": 50,
        "Canny Th2": 150,
        "Blur": 5,
        "Brillo": 50,
        "Contraste": 50
    }

# --- FUNCIONES ---
def nothing(x):
    pass

def save_preset(preset_id):
    config = {
        "Canny Th1": cv2.getTrackbarPos("Canny Th1", "Controles"),
        "Canny Th2": cv2.getTrackbarPos("Canny Th2", "Controles"),
        "Blur": cv2.getTrackbarPos("Blur", "Controles"),
        "Brillo": cv2.getTrackbarPos("Brillo", "Controles"),
        "Contraste": cv2.getTrackbarPos("Contraste", "Controles")
    }
    with open(preset_files[preset_id], 'w') as f:
        json.dump(config, f, indent=4)
    print(f"✅ Preset {preset_id} guardado.")

def load_preset(preset_id):
    if os.path.exists(preset_files[preset_id]):
        with open(preset_files[preset_id], 'r') as f:
            config = json.load(f)
        for key, val in config.items():
            cv2.setTrackbarPos(key, "Controles", val)
        print(f"✅ Preset {preset_id} cargado.")
    else:
        print(f"⚠️ No se encontró preset {preset_id}. Se usarán defaults.")
        for key, val in default_config().items():
            cv2.setTrackbarPos(key, "Controles", val)

def draw_overlay(img, fps, config):
    text = f"FPS: {fps:.2f} | Th1:{config['Canny Th1']} Th2:{config['Canny Th2']} Blur:{config['Blur']} B:{config['Brillo']} C:{config['Contraste']}"
    cv2.putText(img, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1, cv2.LINE_AA)

def draw_help_overlay(img):
    help_text = [
        "Teclas disponibles:",
        "  q - Salir",
        "  g - Guardar preset 1",
        "  b - Guardar preset 2",
        "  n - Guardar preset 3",
        "  1/2/3 - Cargar presets 1-3",
        "  s - Guardar captura",
        "  h - Mostrar/Ocultar ayuda"
    ]
    y0 = 50
    for i, line in enumerate(help_text):
        y = y0 + i * 20
        cv2.putText(img, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

def compute_histogram_and_adjust(gray):
    hist = cv2.calcHist([gray], [0], None, [256], [0,256])
    min_val, max_val = np.min(hist), np.max(hist)
    if max_val - min_val < 500:
        print("⚠️ Imagen oscura/pobre contraste, sugerencia: subí Brillo/Contraste.")

# --- INICIALIZACIÓN ---
cv2.namedWindow("Controles")
for key, val in default_config().items():
    cv2.createTrackbar(key, "Controles", val, 500 if 'Canny' in key else 100, nothing)

load_preset("1")

cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 460)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 440)

if not cap.isOpened():
    print("❌ No se pudo abrir la cámara")
    exit()

prev_time = time.time()
show_help = False  # Estado del overlay de ayuda

# --- LOOP PRINCIPAL ---
while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ No se pudo leer el frame")
        break

    # Leer parámetros
    th1 = cv2.getTrackbarPos("Canny Th1", "Controles")
    th2 = cv2.getTrackbarPos("Canny Th2", "Controles")
    blur_val = cv2.getTrackbarPos("Blur", "Controles")
    brillo_raw = cv2.getTrackbarPos("Brillo", "Controles")
    contraste_raw = cv2.getTrackbarPos("Contraste", "Controles")

    blur_val = max(1, blur_val if blur_val % 2 == 1 else blur_val + 1)
    alpha = contraste_raw / 50.0
    beta = (brillo_raw - 50) * 2

    adjusted = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
    gray = cv2.cvtColor(adjusted, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (blur_val, blur_val), 0)
    edges = cv2.Canny(blur, th1, th2)

    # FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time

    # Overlay
    draw_overlay(adjusted, fps, {
        "Canny Th1": th1, "Canny Th2": th2, "Blur": blur_val,
        "Brillo": brillo_raw, "Contraste": contraste_raw
    })
    if show_help:
        draw_help_overlay(adjusted)

    compute_histogram_and_adjust(gray)

    # Mostrar
    cv2.imshow("Original + Ajustes", adjusted)
    cv2.imshow("Gris + Blur", blur)
    cv2.imshow("Bordes Canny", edges)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        print("👋 Cerrando...")
        break
    elif key == ord('g'):
        save_preset("1")
    elif key == ord('l'):
        load_preset("1")

#juan agrego nuevo save de preset 2
    elif key == ord('b'):
        save_preset("2")
#ciero presets 2       

#juan abro preset 3

    elif key == ord('n'):
        save_preset("3") 
        
#
    elif key in [ord('1'), ord('2'), ord('3')]:
        load_preset(chr(key))
    elif key == ord('s'):
        filename = f"captura_{int(time.time())}.jpg"
        cv2.imwrite(filename, adjusted)
        print(f"📸 Imagen guardada como {filename}")
    elif key == ord('h'):
        show_help = not show_help

cap.release()
cv2.destroyAllWindows()
