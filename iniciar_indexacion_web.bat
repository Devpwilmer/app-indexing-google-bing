@echo off
cd /d "%~dp0indexing_web"
echo.
echo  Indexacion masiva - Google y Bing
echo  Abriendo http://127.0.0.1:5055 en el navegador...
echo  Deja esta ventana abierta. Para cerrar el servidor: Ctrl+C
echo.
start "" "http://127.0.0.1:5055"
python app.py
pause
