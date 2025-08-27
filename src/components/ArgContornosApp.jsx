import React, { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = 'http://localhost:5000/api/arg_contornos';
const VIDEO_FEED_URL = 'http://localhost:5000/arg_contornos_feed';

function ArgContornosApp() {
  const [params, setParams] = useState({
    "Canny Th1": 50,
    "Canny Th2": 150,
    "Blur": 5,
    "Brillo": 50,
    "Contraste": 50
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/status`);
      if (!response.ok) {
        if (response.status === 503) {
          setError("Servicio no disponible. Intentando iniciar...");
          return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      if (data.status === 'stopped') {
        setError("El servicio de Arg Contornos está detenido.");
        return;
      }
      setParams(data);
      setError(null); // Limpiar errores si el estado se obtiene correctamente
    } catch (e) {
      console.error("Error fetching Arg Contornos status:", e);
      setError("No se pudo conectar con el servicio Arg Contornos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const startService = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/start`, { method: 'POST' });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        await response.json();
        fetchStatus(); // Obtener el estado inicial después de iniciar
      } catch (e) {
        console.error("Error starting Arg Contornos service:", e);
        setError("No se pudo iniciar el servicio Arg Contornos.");
      }
    };

    startService();

    const interval = setInterval(fetchStatus, 5000);

    return () => {
      clearInterval(interval);
      const stopService = async () => {
        try {
          await fetch(`${API_BASE_URL}/stop_service`, { method: 'POST' });
        } catch (e) {
          console.error("Error stopping Arg Contornos service:", e);
        }
      };
      stopService();
    };
  }, [fetchStatus]);

  const handleSetParam = async (paramName, value) => {
    try {
      const response = await fetch(`${API_BASE_URL}/set_param`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ param_name: paramName, value: value }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (e) {
      console.error(`Error setting ${paramName}:`, e);
      setError(`Error al establecer ${paramName}.`);
    }
  };

  if (loading) {
    return <div className="p-4">Cargando aplicación Arg Contornos...</div>;
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Aplicación Arg Contornos</h1>

      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
          <p className="font-bold">Error:</p>
          <p>{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Video Feed */}
        <div className="bg-gray-800 rounded-lg overflow-hidden shadow-lg">
          <h2 className="text-xl text-white p-4 border-b border-gray-700">Visualización de Cámara (Cámara 1)</h2>
          <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
            <img
              src={VIDEO_FEED_URL}
              alt="Video Stream"
              className="absolute top-0 left-0 w-full h-full object-contain"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = 'https://via.placeholder.com/640x360?text=Video+No+Disponible';
              }}
            />
          </div>
        </div>

        {/* Controls */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Controles y Parámetros</h2>

          {Object.keys(params).map(paramName => (
            <div className="mb-4" key={paramName}>
              <label htmlFor={paramName} className="block text-sm font-medium text-gray-700">{paramName}: {params[paramName]}</label>
              <input
                type="range"
                id={paramName}
                min={paramName.includes('Canny') ? 0 : (paramName === 'Blur' ? 1 : 0)}
                max={paramName.includes('Canny') ? 500 : 100}
                step="1"
                value={params[paramName] || 0}
                onChange={(e) => setParams(prev => ({ ...prev, [paramName]: parseInt(e.target.value) }))}
                onMouseUp={(e) => handleSetParam(paramName, parseInt(e.target.value))}
                onTouchEnd={(e) => handleSetParam(paramName, parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ArgContornosApp;
