import React, { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = 'http://localhost:5000/api/arneg';
const VIDEO_FEED_URL = 'http://localhost:5000/arneg_feed';

function ArnegApp() {
  const [params, setParams] = useState(null);
  const [isServiceRunning, setIsServiceRunning] = useState(false);
  const [loading, setLoading] = useState(false); // Para acciones específicas
  const [error, setError] = useState(null);

  // Función para detener el servicio
  const stopService = useCallback(async () => {
    try {
      await fetch(`${API_BASE_URL}/stop`, { method: 'POST' });
      setIsServiceRunning(false);
      console.log("Arneg service stopped");
    } catch (e) {
      console.error("Error stopping Arneg service:", e);
      setError("Error al detener el servicio Arneg.");
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
      // Una vez iniciado, obtenemos el estado inicial de los parámetros
      fetchStatus(); 
    } catch (e) {
      console.error("Error starting Arneg service:", e);
      setError("No se pudo iniciar el servicio Arneg. Verifica la consola del backend.");
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

  // Obtener el estado de los parámetros (solo si el servicio está corriendo)
  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/status`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      if (data.status !== 'stopped') {
        setParams(data);
      }
    } catch (e) {
      console.error("Error fetching Arneg status:", e);
      // No mostramos error aquí para no ser intrusivos, el estado se reintentará
    }
  };

  // Efecto para detener el servicio cuando el componente se desmonta
  useEffect(() => {
    // La función de limpieza se ejecutará cuando el usuario navegue fuera de esta página
    return () => {
      if (isServiceRunning) {
        stopService();
      }
    };
  }, [isServiceRunning, stopService]);

  const handleSetParam = async (paramName, value) => {
    if (!isServiceRunning) return;
    try {
      const response = await fetch(`${API_BASE_URL}/set_param`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ param_name: paramName, value: value }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      // Actualizar el estado local inmediatamente para una UI más reactiva
      setParams(prev => ({ ...prev, [paramName]: value }));
    } catch (e) {
      console.error(`Error setting ${paramName}:`, e);
      setError(`Error al establecer ${paramName}.`);
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Aplicación Arneg - Perfil de Bordes</h1>
      
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Columna de Video y Controles de Servicio */}
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
                  setError('El stream de video no está disponible. Verifica la cámara y el backend.');
                  setIsServiceRunning(false); // Detiene el intento de carga
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

        {/* Columna de Controles y Parámetros */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Controles y Parámetros</h2>
          {isServiceRunning && params ? (
            Object.keys(params).map(paramName => (
              <div className="mb-4" key={paramName}>
                <label htmlFor={paramName} className="block text-sm font-medium text-gray-700">{paramName}: {params[paramName]}</label>
                <input
                  type="range"
                  id={paramName}
                  min={paramName.includes('Canny') ? 0 : 1}
                  max={paramName.includes('Canny') ? 500 : 100}
                  step="1"
                  value={params[paramName] || 0}
                  onChange={(e) => setParams(prev => ({ ...prev, [paramName]: parseInt(e.target.value) }))}
                  onMouseUp={(e) => handleSetParam(paramName, parseInt(e.target.value))}
                  onTouchEnd={(e) => handleSetParam(paramName, parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
              </div>
            ))
          ) : (
            <div className="text-gray-500">Inicia el servicio para ver y ajustar los parámetros.</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ArnegApp;
