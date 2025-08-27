import React, { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = 'http://localhost:5000/api/ptz';
const VIDEO_FEED_URL = 'http://localhost:5000/ptz_feed';

function PTZApp() {
  const [status, setStatus] = useState(null);
  const [isServiceRunning, setIsServiceRunning] = useState(false);
  const [loading, setLoading] = useState(false); // Para acciones de Iniciar/Detener
  const [error, setError] = useState(null);

  // Función para detener el servicio
  const stopService = useCallback(async () => {
    try {
      await fetch(`${API_BASE_URL}/stop_service`, { method: 'POST' });
      setIsServiceRunning(false);
      setStatus(null); // Limpiar el estado anterior
      console.log("PTZ service stopped");
    } catch (e) {
      console.error("Error stopping PTZ service:", e);
      setError("Error al detener el servicio PTZ.");
    }
  }, []);

  // Iniciar el servicio
  const handleStartService = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/start`, { method: 'POST' });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      setIsServiceRunning(true);
      // Dar un pequeño margen para que el servicio inicialice antes de pedir el estado
      setTimeout(() => fetchStatus(), 1000);
    } catch (e) {
      console.error("Error starting PTZ service:", e);
      setError("No se pudo iniciar el servicio PTZ. Verifica la consola del backend.");
    } finally {
      setLoading(false);
    }
  };

  // Detener el servicio
  const handleStopService = async () => {
    setLoading(true);
    await stopService();
    setLoading(false);
  };

  // Obtener el estado de los parámetros
  const fetchStatus = useCallback(async () => {
    if (!isServiceRunning) return;
    try {
      const response = await fetch(`${API_BASE_URL}/status`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      if (data.status !== 'stopped') {
        setStatus(data);
      }
    } catch (e) {
      console.error("Error fetching PTZ status:", e);
    }
  }, [isServiceRunning]);

  // Efecto para obtener el estado periódicamente
  useEffect(() => {
    if (isServiceRunning) {
      const interval = setInterval(fetchStatus, 3000);
      return () => clearInterval(interval);
    }
  }, [isServiceRunning, fetchStatus]);

  // Efecto para detener el servicio al desmontar
  useEffect(() => {
    return () => {
      if (isServiceRunning) {
        stopService();
      }
    };
  }, [isServiceRunning, stopService]);

  const handleToggleFeature = async (featureName) => {
    if (!isServiceRunning) return;
    try {
      const response = await fetch(`${API_BASE_URL}/toggle_feature`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feature_name: featureName }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      setStatus(prev => ({ ...prev, [featureName === 'yolo' ? 'do_detect' : `do_${featureName}`]: data.new_state }));
    } catch (e) {
      console.error(`Error toggling ${featureName}:`, e);
    }
  };
  
  const handleSetParam = async (paramName, value) => {
    if (!isServiceRunning) return;
    try {
      // Convertir valores flotantes de vuelta a su rango original si es necesario
      let finalValue = value;
      if (['YOLO_CONF_THRESHOLD', 'YOLO_IOU_THRESHOLD', 'PAN_SPEED', 'TILT_SPEED', 'ZOOM_SPEED'].includes(paramName)) {
        finalValue = value / 100;
      }

      await fetch(`${API_BASE_URL}/set_param`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ param_name: paramName, value: finalValue }),
      });
      // Actualizar el estado local inmediatamente para una UI más reactiva
      setStatus(prev => ({
        ...prev,
        params: {
          ...prev.params,
          [paramName]: finalValue // Guardar el valor final que se envió al backend
        }
      }));
    } catch (e) {
      console.error(`Error setting ${paramName}:`, e);
    }
  };
  
  const handlePtzMove = async (direction) => {
    if (!isServiceRunning || !status?.ptz_available) return;
    try {
      await fetch(`${API_BASE_URL}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction: direction }),
      });
    } catch (e) {
      console.error(`Error moving PTZ ${direction}:`, e);
    }
  };
  
  const handlePtzStop = async () => {
    if (!isServiceRunning || !status?.ptz_available) return;
    try {
      await fetch(`${API_BASE_URL}/stop`, { method: 'POST' });
    } catch (e) {
      console.error(`Error stopping PTZ:`, e);
    }
  };
  
  const handlePtzHome = async () => {
    if (!isServiceRunning || !status?.ptz_available) return;
    try {
      await fetch(`${API_BASE_URL}/home`, { method: 'POST' });
    } catch (e) {
      console.error(`Error going to PTZ home:`, e);
    }
  };

  const getParamProps = (paramName) => {
    let min, max, step;
    switch (paramName) {
      case 'YOLO_CONF_THRESHOLD':
      case 'YOLO_IOU_THRESHOLD':
      case 'PAN_SPEED':
      case 'TILT_SPEED':
      case 'ZOOM_SPEED':
        min = 0;
        max = 100; // Representa 0.0 a 1.0
        step = 1;
        break;
      case 'YOLO_STRIDE_N':
      case 'GROSOR_PUNTOS':
      case 'GROSOR_LINEAS':
        min = 1;
        max = 10; // O un valor máximo adecuado
        step = 1;
        break;
      default:
        min = 0;
        max = 100;
        step = 1;
    }
    return { min, max, step };
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Control de Cámara PTZ</h1>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">{error}</div>}
      
      {isServiceRunning && status && !status.rtsp_open && (
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4" role="alert">
          <p className="font-bold">Advertencia:</p>
          <p>El stream RTSP no está abierto. Asegúrate de que la cámara está conectada y la configuración es correcta en el backend.</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg overflow-hidden shadow-lg flex flex-col">
          <h2 className="text-xl text-white p-4 border-b border-gray-700">Visualización de Cámara</h2>
          <div className="relative w-full flex-grow" style={{ minHeight: '360px' }}>
            {isServiceRunning ? (
              <img
                src={`${VIDEO_FEED_URL}?t=${new Date().getTime()}`}
                alt="Video Stream"
                className="absolute top-0 left-0 w-full h-full object-contain"
                onError={(e) => {
                  e.target.onerror = null;
                  setError('El stream de video no está disponible. Verifica la conexión RTSP.');
                  setIsServiceRunning(false);
                }}
              />
            ) : (
              <div className="absolute top-0 left-0 w-full h-full bg-black flex items-center justify-center">
                <span className="text-gray-400">Servicio detenido</span>
              </div>
            )}
          </div>
          <div className="p-4 bg-gray-900">
            {!isServiceRunning ? (
              <button onClick={handleStartService} disabled={loading} className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded transition duration-300 disabled:opacity-50">
                {loading ? 'Iniciando...' : 'Iniciar Servicio'}
              </button>
            ) : (
              <button onClick={handleStopService} disabled={loading} className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded transition duration-300 disabled:opacity-50">
                {loading ? 'Deteniendo...' : 'Detener Servicio'}
              </button>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Controles y Parámetros</h2>
          {isServiceRunning && status ? (
            <>
              <div className="mb-6">
                <h3 className="text-lg font-medium mb-2">Detección de Características</h3>
                <div className="flex flex-wrap gap-4">
                  <label className="inline-flex items-center">
                    <input type="checkbox" className="form-checkbox h-5 w-5 text-blue-600" checked={status.do_detect} onChange={() => handleToggleFeature('yolo')} disabled={!status.yolo_available} />
                    <span className="ml-2 text-gray-700">YOLO ({status.yolo_available ? 'Disponible' : 'No Disp.'})</span>
                  </label>
                  <label className="inline-flex items-center">
                    <input type="checkbox" className="form-checkbox h-5 w-5 text-blue-600" checked={status.do_face} onChange={() => handleToggleFeature('face')} />
                    <span className="ml-2 text-gray-700">Facial</span>
                  </label>
                  <label className="inline-flex items-center">
                    <input type="checkbox" className="form-checkbox h-5 w-5 text-blue-600" checked={status.do_body} onChange={() => handleToggleFeature('body')} />
                    <span className="ml-2 text-gray-700">Corporal</span>
                  </label>
                </div>
              </div>

              {status.ptz_available && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium mb-2">Control PTZ</h3>
                  <div className="grid grid-cols-3 gap-2 mb-4 max-w-xs mx-auto">
                    <div></div>
                    <button onMouseDown={() => handlePtzMove('w')} onMouseUp={handlePtzStop} onMouseLeave={handlePtzStop} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">▲</button>
                    <div></div>
                    <button onMouseDown={() => handlePtzMove('a')} onMouseUp={handlePtzStop} onMouseLeave={handlePtzStop} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">◀</button>
                    <button onClick={handlePtzStop} className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">■</button>
                    <button onMouseDown={() => handlePtzMove('d')} onMouseUp={handlePtzStop} onMouseLeave={handlePtzStop} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">▶</button>
                    <div></div>
                    <button onMouseDown={() => handlePtzMove('s')} onMouseUp={handlePtzStop} onMouseLeave={handlePtzStop} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">▼</button>
                    <div></div>
                  </div>
                  <div className="flex justify-center">
                     <button onClick={handlePtzHome} className="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded">Ir a Home</button>
                  </div>
                </div>
              )}

              {/* Sección de Trackbars para Parámetros */}
              <div className="mb-6">
                <h3 className="text-lg font-medium mb-2">Ajuste de Parámetros</h3>
                {status.params && Object.keys(status.params).map(paramName => {
                  const { min, max, step } = getParamProps(paramName);
                  // Para mostrar el valor correcto en el UI, especialmente para flotantes
                  const displayValue = ['YOLO_CONF_THRESHOLD', 'YOLO_IOU_THRESHOLD', 'PAN_SPEED', 'TILT_SPEED', 'ZOOM_SPEED'].includes(paramName)
                    ? (status.params[paramName] * 100).toFixed(0) // Multiplicar por 100 para el slider
                    : status.params[paramName];

                  return (
                    <div className="mb-4" key={paramName}>
                      <label htmlFor={paramName} className="block text-sm font-medium text-gray-700">
                        {paramName.replace(/_/g, ' ')}: {displayValue}
                      </label>
                      <input
                        type="range"
                        id={paramName}
                        min={min}
                        max={max}
                        step={step}
                        value={displayValue} // Usar el valor ajustado para el slider
                        onChange={(e) => {
                          const newValue = parseFloat(e.target.value);
                          setStatus(prev => ({
                            ...prev,
                            params: {
                              ...prev.params,
                              [paramName]: ['YOLO_CONF_THRESHOLD', 'YOLO_IOU_THRESHOLD', 'PAN_SPEED', 'TILT_SPEED', 'ZOOM_SPEED'].includes(paramName)
                                ? newValue / 100 // Dividir por 100 para el valor real
                                : newValue
                            }
                          }));
                        }}
                        onMouseUp={(e) => handleSetParam(paramName, parseFloat(e.target.value))}
                        onTouchEnd={(e) => handleSetParam(paramName, parseFloat(e.target.value))}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                      />
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="text-gray-500">Inicia el servicio para ver y ajustar los parámetros.</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PTZApp;
