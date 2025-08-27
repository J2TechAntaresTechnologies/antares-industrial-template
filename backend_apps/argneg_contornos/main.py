import cv2
import time
from argneg_service import ArgnegService

if __name__ == "__main__":
    service = ArgnegService(camera_index=1)

    if not service._running:
        print("No se pudo iniciar el servicio. Saliendo.")
        exit()

    print("Servicio Arneg inicializado. Presiona 'q' para salir.")

    while True:
        with service._frame_lock:
            if service._current_frame is not None:
                cv2.imshow("Arneg Contornos", service._current_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

        time.sleep(0.03)

    service.release_resources()
    cv2.destroyAllWindows()
    print("Servicio Arneg detenido.")
