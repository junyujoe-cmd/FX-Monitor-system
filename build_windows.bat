@echo off
REM Windows exe 构建脚本
REM 运行前确保已安装: pip install PyQt6 requests pyqtgraph akshare beautifulsoup4 pandas lxml pyinstaller

echo === 构建实时外汇监控系统 Windows 版本 ===

pyinstaller --noconfirm --onefile --windowed ^
  --name "实时外汇监控系统" ^
  --add-data "ui;ui" ^
  --add-data "config.py;." ^
  --add-data "database.py;." ^
  --add-data "calculator.py;." ^
  --add-data "fetcher.py;." ^
  --add-data "bank_fetcher.py;." ^
  --hidden-import PyQt6 ^
  --hidden-import pyqtgraph ^
  --hidden-import akshare ^
  --hidden-import bs4 ^
  --hidden-import lxml ^
  --hidden-import pandas ^
  main.py

echo.
echo ✅ 构建完成! exe 文件在 dist\ 目录
echo.
echo 安装包位于 dist\实时外汇监控系统.exe
pause
