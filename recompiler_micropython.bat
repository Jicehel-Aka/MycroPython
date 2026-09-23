@echo off
REM Ouvre MSYS2 MINGW64 dans le dossier du projet ET relance la generation
REM du coeur MicroPython (clean + build). La fenetre reste ouverte a la fin.
cd /d "%~dp0"
C:\msys64\msys2_shell.cmd -mingw64 -here -c "./build_micropython_embed.sh clean && ./build_micropython_embed.sh; echo; echo '--- Termine. Ferme la fenetre ou tape idf.py build cote ESP-IDF. ---'; exec bash"
