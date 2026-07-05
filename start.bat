@echo off
title SAD OFFICINE - Demarrage

echo.
echo  ============================================
echo   SAD OFFICINE - Demarrage de l'application
echo  ============================================
echo.

:: Verifier que la venv Python existe
if not exist "%~dp0backend\venv\Scripts\python.exe" (
    echo  [ERREUR] Environnement Python introuvable.
    echo.
    echo  Lancez d'abord ces commandes dans le dossier backend :
    echo    cd backend
    echo    python -m venv venv
    echo    venv\Scripts\pip install -r requirement.txt
    echo.
    pause
    exit /b 1
)

:: Verifier si le port 8000 est deja utilise
netstat -ano | findstr "127.0.0.1:8000" >nul 2>&1
if not errorlevel 1 (
    echo  [AVERTISSEMENT] Le port 8000 est deja utilise.
    echo  Un serveur backend tourne peut-etre deja.
    echo  Fermez la fenetre "SAD OFFICINE - Backend" precedente, puis relancez.
    echo.
    pause
    exit /b 1
)

:: Installer les dependances frontend si absentes
if not exist "%~dp0frontend\node_modules" (
    echo  [INFO] Installation des dependances frontend...
    pushd "%~dp0frontend"
    npm install
    if errorlevel 1 (
        echo  [ERREUR] npm install a echoue.
        popd
        pause
        exit /b 1
    )
    popd
)

:: Creer le .env frontend si absent
if not exist "%~dp0frontend\.env" (
    echo VITE_API_URL=http://localhost:8000>"%~dp0frontend\.env"
)

echo  [1/2] Demarrage du backend  (http://localhost:8000) ...
start "SAD OFFICINE - Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo  [2/2] Demarrage du frontend (http://localhost:5173) ...
start "SAD OFFICINE - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 4 /nobreak >nul

echo.
echo  Application prete. Ouverture du navigateur...
echo.
start "" http://localhost:5173

echo.
echo  Appuyez sur une touche pour fermer cette fenetre.
echo  Les serveurs restent actifs dans leurs fenetres.
pause >nul
