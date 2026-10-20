# Control de solicitudes y trámites del CICA

## Instalación
```
pip install -r requirements.txt
cp .env.example .env        # y completa los datos
python main.py init
python main.py demo         # datos de ejemplo (opcional)
```

## Comandos
| Comando | Qué hace |
|---|---|
| `python main.py nueva --solicitante "Ana" --tipo Certificados --correo ana@x.com` | Registra una solicitud |
| `python main.py listar [--estado "En proceso"] [--todas]` | Lista solicitudes (! = con alerta) |
| `python main.py ver CICA-2026-0001` | Detalle + historial |
| `python main.py estado CICA-2026-0001 "En revisión"` | Cambia de estado (asigna responsable por tipo) |
| `python main.py estado CICA-2026-0001 Finalizada --respuesta "..."` | Cierra la solicitud |
| `python main.py espera CICA-2026-0001 "Falta el documento"` | Queda esperando al solicitante |
| `python main.py reanudar CICA-2026-0001` | Quita la espera y extiende los plazos |
| `python main.py alertas [--enviar]` | Muestra / envía las alertas |
| `python main.py importar` | Trae respuestas nuevas del formulario de Google |
| `python main.py exportar` | Escribe el seguimiento en la pestaña "Seguimiento" |

## Conexión con Google Sheets
1. En Google Cloud crea un proyecto, activa **Google Sheets API** y **Google Drive API**.
2. Crea una **cuenta de servicio** y descarga su clave JSON como `credenciales.json`.
3. Comparte tu hoja de respuestas con el correo de la cuenta de servicio (permiso de editor).
4. Copia el ID de la hoja (está en la URL) a `GOOGLE_SHEET_ID` en `.env`.
5. Ajusta `COLUMNAS_FORM` en `config.py` con los nombres exactos de las preguntas de tu formulario.

## Automatizar (Linux/macOS, cron, cada día laborable a las 8:00)
```
0 8 * * 1-5  cd /ruta/cica_solicitudes && python main.py importar && python main.py alertas --enviar && python main.py exportar
```
En Windows usa el Programador de tareas con el mismo comando.
