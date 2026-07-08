@echo off
set /p id="Enter group/user id: "
python roarchive.py %id%
pause