# Documentación Técnica — UI/UX y Operación del Frontend Antares Industrial App

## 1. Mantenimiento de Servidor Local

### 1.1 Requisitos del entorno

- **Node.js 18+** obligatorio (Node < 18 rompe Vite).
- npm o yarn para manejo de dependencias.
- Backend Flask v0.3 corriendo localmente en `http://localhost:5000`.

### 1.2 Instalación y actualización

1. Clonar el repositorio frontend.
2. Copiar `.env.sample` a `.env` y configurar `VITE_API_BASE`.
3. Instalar dependencias:

```bash
npm install
```

4. Para actualizar dependencias:

```bash
npm update
```

5. Limpiar cache si hay problemas:

```bash
rm -rf node_modules package-lock.json
npm install
```

### 1.3 Ejecución local

```bash
npm run dev    # Abre en http://localhost:5173
npm run build  # Genera versión de producción
npm run preview
```

---

## 2. Seguridad

### 2.1 Comunicación segura

- Usar HTTPS en producción.
- Configurar CORS en backend para restringir orígenes.

### 2.2 Gestión de credenciales

- Variables sensibles en `.env`, no versionar este archivo.
- API keys y tokens solo en backend, nunca en frontend.

### 2.3 Autenticación y roles

- Implementar JWT o cookies seguras.
- Restringir rutas y componentes según rol (Operador, Supervisor, Ingeniería, Admin).

### 2.4 Protección contra ataques comunes

- Validar todos los datos que vengan de formularios antes de enviarlos al backend.
- Evitar inyección en parámetros de PLC.
- Rate limit y auditoría para operaciones críticas.

---

## 3. Edición y mantenimiento de la interfaz gráfica

### 3.1 Estructura de carpetas recomendada

```
src/
  components/
  hooks/
  pages/
  styles/
```

### 3.2 Modificación de estilos

- Los estilos globales se encuentran en `src/index.css`.
- Tailwind config (`tailwind.config.js`) contiene colores, tipografías y espaciados según Antares Theme.

### 3.3 Creación y edición de componentes

- Reutilizar componentes base (Card, Table, StatusBadge).
- Mantener consistencia de clases Tailwind para no romper estilo corporativo.

### 3.4 Pruebas de cambios

- Correr `npm run dev` y validar en múltiples resoluciones.
- Revisar que el polling y las llamadas API funcionen tras cambios.

### 3.5 Deploy de cambios

- Compilar con `npm run build`.
- Subir la carpeta `dist/` al servidor web o integrarla con el backend.

---

## 4. Checklist previo a producción

- Node actualizado.
- `.env` configurado para entorno productivo.
- Certificados SSL configurados si aplica.
- Validación de todas las rutas y roles.
- Pruebas de lectura/escritura PLC en entorno de staging.

