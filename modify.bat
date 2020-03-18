@echo off
set pythonPath="F:\envs\py37\Scripts\python.exe">nul
set mainPath="F:\py\todo\main.py">nul
set param0=%0>nul
set id=%1>nul
set content=%2>nul
cls
%pythonPath% %mainPath% %param0% %id% %content%
echo on