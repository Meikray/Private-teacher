@echo off
REM ==========================================================
REM  Lanceur Windows de l'Assistant Professeur Personnel.
REM  Double-clique sur ce fichier : il installe ce qu'il faut
REM  (la premiere fois), puis demarre le serveur et ouvre le
REM  navigateur. Pour arreter : ferme cette fenetre (ou Ctrl+C).
REM ==========================================================
chcp 65001 >nul
cd /d "%~dp0"

REM --- 1. Trouver Python ---
set PYTHON=
where py >nul 2>nul && set PYTHON=py
if not defined PYTHON (where python >nul 2>nul && set PYTHON=python)
if not defined PYTHON (
  echo Python est introuvable. Installe-le depuis https://www.python.org/downloads/
  echo en cochant "Add Python to PATH", puis relance ce fichier.
  pause
  exit /b 1
)

REM --- 2. Environnement virtuel (seulement la premiere fois) ---
if not exist ".venv\Scripts\activate.bat" (
  echo Creation de l'environnement virtuel...
  %PYTHON% -m venv .venv || (echo Echec de la creation de .venv & pause & exit /b 1)
)
call ".venv\Scripts\activate.bat"

REM --- 3. Bibliotheques (rapide si elles sont deja installees) ---
echo Verification des bibliotheques...
python -m pip install -q -r requirements.txt || (echo Echec de l'installation & pause & exit /b 1)

REM --- 4. Configuration (.env) ---
if not exist ".env" copy ".env.example" ".env" >nul
set FOURNISSEUR=ollama
set MODELE=qwen2.5:7b
for /f "tokens=1,* delims==" %%a in ('findstr /b "FOURNISSEUR= MODELE_OLLAMA=" ".env"') do (
  if "%%a"=="FOURNISSEUR" set FOURNISSEUR=%%b
  if "%%a"=="MODELE_OLLAMA" set MODELE=%%b
)

if /i "%FOURNISSEUR%"=="ollama" goto ollama
goto claude

:ollama
REM --- 4a. IA locale gratuite (Ollama) ---
where ollama >nul 2>nul || (
  echo.
  echo Ollama ^(l'IA gratuite qui tourne sur ton ordinateur^) n'est pas installe.
  echo Telecharge-le sur https://ollama.com/download , installe-le, puis relance ce fichier.
  pause
  exit /b 1
)
curl -s http://127.0.0.1:11434/api/tags >nul 2>nul || (
  echo Demarrage d'Ollama...
  start "" /b ollama serve >nul 2>nul
  timeout /t 5 >nul
)
ollama list | findstr /b /c:"%MODELE%" >nul || (
  echo Telechargement du modele %MODELE% ^(une seule fois, plusieurs Go^)...
  ollama pull %MODELE%
)
echo Professeur : IA locale gratuite ^(%MODELE%^).
goto lancer

:claude
REM --- 4b. Claude (payant) : cle API ---
findstr /c:"mets-ta-cle-ici" ".env" >nul && (
  echo.
  echo Il faut mettre ta cle API dans le fichier .env.
  echo Le Bloc-notes va s'ouvrir : remplace "mets-ta-cle-ici" par ta cle,
  echo enregistre, ferme le Bloc-notes, et le lancement continuera.
  notepad ".env"
)

:lancer
REM --- 5. Ouvrir le navigateur dans 3 secondes, puis demarrer le serveur ---
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"
echo.
echo Serveur demarre sur http://127.0.0.1:8000  (ferme cette fenetre pour l'arreter)
python -m uvicorn app.main:app
pause
