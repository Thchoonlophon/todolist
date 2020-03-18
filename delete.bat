@echo off
set pythonPath="F:\envs\py37\Scripts\python.exe">nul
set mainPath="F:\py\todo\main.py">nul
set param0=%0
set id=%1
cls
%pythonPath% %mainPath% %param0% %id%
echo on