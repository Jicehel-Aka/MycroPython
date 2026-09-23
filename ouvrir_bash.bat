@echo off
REM Ouvre un shell MSYS2 MINGW64 directement dans le dossier du projet.
REM Double-clique ce fichier, puis tape :  ./build_micropython_embed.sh
cd /d "%~dp0"
C:\msys64\msys2_shell.cmd -mingw64 -here
