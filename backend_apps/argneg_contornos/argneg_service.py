import cv2
import numpy as np
import time
import threading

class ArgnegService:
    def __init__(self, camera_index=1):
        print(f"[INFO] Inicializando ArgnegService para la cámara {camera_index}...")
        self.camera_index = camera_index
        # Forzar el uso del backend V4L2, que es más robusto en Linux
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 460)

        self.params = {
            "Canny Th1": 50,
            "Canny Th2": 150,
            "Blur": 5,
            "Brillo": 50,
            "Contraste": 50
        }

        self._running = False
        self._frame_lock = threading.Lock()
        self._current_frame = None

        if not self.cap.isOpened():
            print(f"Error al abrir la cámara {self.camera_index}")
        else:
            self._running = True
            self.thread = threading.Thread(target=self._process_frames, daemon=True)
            self.thread.start()

    def _process_frames(self):
        prev_time = time.time()
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                print("No se pudo leer el frame")
                time.sleep(0.1)
                continue

            # Aplicar transformaciones
            alpha = self.params["Contraste"] / 50.0
            beta = (self.params["Brillo"] - 50) * 2
            adjusted = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
            
            gray = cv2.cvtColor(adjusted, cv2.COLOR_BGR2GRAY)
            
            blur_val = self.params["Blur"]
            blur_val = max(1, blur_val if blur_val % 2 == 1 else blur_val + 1)
            blur = cv2.GaussianBlur(gray, (blur_val, blur_val), 0)
            
            edges = cv2.Canny(blur, self.params["Canny Th1"], self.params["Canny Th2"])

            # Combinar frame original con los bordes
            output_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            final_frame = cv2.addWeighted(output_frame, 0.5, adjusted, 0.5, 0)

            # FPS
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time)
            prev_time = curr_time

            # Overlay
            text = f"FPS: {fps:.2f} | Th1:{self.params['Canny Th1']} Th2:{self.params['Canny Th2']} Blur:{self.params['Blur']} B:{self.params['Brillo']} C:{self.params['Contraste']}"
            cv2.putText(final_frame, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1, cv2.LINE_AA)

            with self._frame_lock:
                self._current_frame = final_frame.copy()

            time.sleep(0.01)

    def generate_frames(self):
        while self._running:
            try:
                with self._frame_lock:
                    if self._current_frame is None:
                        time.sleep(0.01)
                        continue
                    ret, buffer = cv2.imencode('.jpg', self._current_frame)
                    if not ret:
                        continue
                    frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.03)
            except (GeneratorExit, BrokenPipeError):
                print("[INFO] Cliente de streaming de Argneg desconectado.")
                break

    def get_status(self):
        return self.params

    def set_param(self, param_name, value):
        if param_name in self.params:
            self.params[param_name] = value
            return {"status": "ok", "param_name": param_name, "value": value}
        return {"error": "Parámetro no válido"}

    def release_resources(self):
        self._running = False
        if self.thread.is_alive():
            self.thread.join()
        self.cap.release()
