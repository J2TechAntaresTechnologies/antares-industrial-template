
# Antares Industrial Template

## Descripción General

Antares Industrial Template es una plantilla base profesional para el desarrollo de aplicaciones orientadas a la automatización industrial. Este proyecto ofrece una estructura modular y escalable pensada para facilitar la integración entre interfaces gráficas, conexiones con dispositivos industriales (como PLCs), bases de datos y ejecución de scripts personalizados (visión artificial, OCR, IA, entre otros).

Este template permite un desarrollo ágil, colaborativo y robusto, integrando tecnologías modernas como Flask, Snap7, SQLite/PostgreSQL y soporte directo para trabajo con GitHub y asistentes de inteligencia artificial.

---

## Estructura del Proyecto

```
antares-industrial-template/
│
├── app/                    # Módulo principal de la aplicación
│   ├── routes/             # Rutas web (Flask): landing, login, dashboard, parámetros
│   ├── static/             # Archivos estáticos (CSS, JS, logos)
│   ├── templates/          # HTMLs renderizados con Jinja2
│   ├── db/                 # Conector de base de datos
│   ├── plc/                # Módulo de conexión a PLCs (Snap7, etc.)
│   ├── utils/              # Funciones auxiliares compartidas
│   └── services/           # Lógica de ejecución de scripts externos
│
├── config/                 # Configuración por entorno
├── tests/                  # Pruebas unitarias
├── docs/                   # Documentación técnica interna
│
├── .gitignore              # Exclusiones para el control de versiones
├── README.md               # Este archivo
├── requirements.txt        # Dependencias del entorno Python
└── run.py                  # Punto de entrada para levantar la app
```

---

## Detalle por Módulo

### app/routes/
Contiene las rutas y vistas de la aplicación. Cada archivo representa una sección de la interfaz web, como landing page, login, pantalla principal o parámetros configurables.

### app/static/
Archivos estáticos como hojas de estilo (CSS), scripts JS y recursos visuales (logos, íconos).

### app/templates/
HTMLs renderizados dinámicamente con Jinja2. Se vinculan a las rutas definidas en `app/routes`.

### app/db/
Módulo encargado de conectar con bases de datos. El archivo `connector.py` es adaptable a múltiples motores como SQLite, PostgreSQL o MySQL.

### app/plc/
Conectores para comunicación industrial. Actualmente incluye `siemens_snap7.py` pero es escalable a otros protocolos como Modbus o OPC UA.

### app/utils/
Funciones compartidas como sanitización de datos, validaciones, transformaciones, etc.

### app/services/
Contiene scripts de ejecución independiente o lógica pesada, como procesamiento de visión artificial, inferencia de modelos, etc. `runner.py` permite invocar y gestionar estos scripts.

### config/
Archivos de configuración general y específica por entorno (desarrollo, producción, pruebas).

### tests/
Contiene pruebas unitarias del sistema. Estructura compatible con pytest.

### docs/
Espacio reservado para documentación técnica extendida, como arquitectura, decisiones de diseño, bitácoras.

---

## Requisitos

- Python 3.8+
- Flask
- Snap7 (python-snap7)
- Motor de base de datos (SQLite/PostgreSQL/MySQL)
- Git
- Visual Studio Code (recomendado)

---

## Cómo iniciar el proyecto

```bash
pip install -r requirements.txt
python run.py
```

---

## Trabajo colaborativo recomendado

Este proyecto está preparado para trabajo en equipo con Git y GitHub, incluyendo:
- Ramas por feature (`feature/xxx`)
- Rama `dev` para integración
- Rama `main` para versiones estables
- Pull Requests obligatorios
- Convención de commits (feat, fix, refactor, chore)

---

## Asistente Inteligente

Se recomienda el uso de GitHub Copilot y su nuevo **Chat IA integrado en Visual Studio Code**, lo que permite colaborar en vivo, generar código contextual, obtener ayuda técnica y mejorar la calidad del desarrollo sin salir del entorno de trabajo.

---

## Autoría

Antares Technologies SRL
Proyecto iniciado por Juan Martinez (@jmartinez)
