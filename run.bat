@echo off
echo Starting Steel Parser Application...
echo.
echo Checking database...
if not exist "database\steel_database.db" (
    echo Database not found. Creating database...
    python database_schema.py
    echo.
    echo Database created. You may want to run the parser first:
    echo   python parser.py
    echo.
    pause
)
echo.
echo Starting web application...
echo Open http://localhost:5001 in your browser
echo.
echo Press Ctrl+C to stop the server
echo.
python app.py
pause

