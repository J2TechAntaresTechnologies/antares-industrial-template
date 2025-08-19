import React, { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000';

export default function ArnegApp() {
  const [output, setOutput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleExecute = async () => {
    setIsLoading(true);
    setOutput('');
    try {
      const response = await fetch(`${API_BASE}/api/run/argneg_contornos`, {
        method: 'POST',
      });
      const data = await response.json();
      if (response.ok) {
        setOutput(data.output);
      } else {
        setOutput(`Error: ${data.error}`);
      }
    } catch (error) {
      setOutput(`Error de conexión: ${error.message}`);
    }
    setIsLoading(false);
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Aplicación Arneg - Perfil de Bordes</h1>
      <p className="mb-4">Haz clic en el botón para ejecutar el script de perfiles de contorno en el backend.</p>
      <button
        onClick={handleExecute}
        disabled={isLoading}
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:bg-gray-400"
      >
        {isLoading ? 'Ejecutando...' : 'Ejecutar Script'}
      </button>
      <div className="mt-4 p-2 bg-gray-900 text-white font-mono rounded">
        <h2 className="font-bold">Resultado:</h2>
        <pre>{output}</pre>
      </div>
    </div>
  );
}
