@echo off
chcp 65001 > nul
cd /d "%~dp0"
python src\main.py && python src\check_report.py
echo.
echo 完了しました。output\report.csv を確認してください。
pause
