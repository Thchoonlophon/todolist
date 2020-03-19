@echo off
set pythonPath="F:\envs\py37\Scripts\python.exe">nul
set mainPath="F:\py\todo\main.py">nul
set param0=%0>nul
set opera=%1>nul
set id=%2>nul
set content=%3>nul
cls
%pythonPath% %mainPath% %param0% %opera% %id% %content%
echo on