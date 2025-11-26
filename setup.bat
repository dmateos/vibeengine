@echo off
REM VibeEngine Setup Script for Windows

echo.
echo ======================================
echo   VibeEngine Setup
echo ======================================
echo.

REM Check Python version
echo Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Please install Python 3.11+
    pause
    exit /b 1
)
echo.

REM Check Node.js version
echo Checking Node.js version...
node --version
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)
echo.

REM Create virtual environment
echo Creating Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated
echo.

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt
echo Python dependencies installed
echo.

REM Copy .env.example if .env doesn't exist
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo .env file created
    echo WARNING: Please edit .env and add your API keys!
    echo.
) else (
    echo .env file already exists
    echo.
)

REM Run migrations
echo Running database migrations...
python manage.py migrate
echo Migrations completed
echo.

REM Create superuser
echo.
echo Do you want to create a Django superuser? (Y/N)
set /p create_superuser=
if /i "%create_superuser%"=="Y" (
    python manage.py createsuperuser
    echo.
)

REM Install frontend dependencies
echo Installing frontend dependencies...
cd frontend
call npm install
echo Frontend dependencies installed
cd ..
echo.

REM Done
echo.
echo ======================================
echo   Setup Complete!
echo ======================================
echo.
echo Next steps:
echo 1. Edit .env and add your API keys
echo 2. Start backend:  python manage.py runserver
echo 3. Start frontend: cd frontend ^&^& npm run dev
echo 4. Open http://localhost:5173 in your browser
echo.
echo Happy building!
echo.
pause
