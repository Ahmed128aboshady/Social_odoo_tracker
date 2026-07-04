@echo off
echo ==========================================
echo Starting Odoo Leads Dashboard Local Server
echo ==========================================
echo.
echo 1. Opening Dashboard in your browser...
start "" "http://localhost:8085"
echo 2. Running python server on http://localhost:8085
echo.
echo Press Ctrl+C in this window to stop the server.
echo.
python server.py
