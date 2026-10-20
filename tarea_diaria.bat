@echo off
REM Ejecuta el ciclo diario del sistema CICA: importar respuestas nuevas,
REM revisar y enviar alertas, y actualizar la hoja de seguimiento.
REM Este archivo se guarda un registro en tarea.log para poder revisar
REM despues si algo fallo.

cd /d "%~dp0"

echo ==================================================== >> tarea.log
echo %date% %time% - Iniciando tarea diaria CICA >> tarea.log

python main.py importar >> tarea.log 2>&1
python main.py alertas --enviar >> tarea.log 2>&1
python main.py exportar >> tarea.log 2>&1

echo %date% %time% - Tarea finalizada >> tarea.log
