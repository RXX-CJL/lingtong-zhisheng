@echo off
chcp 65001 >nul
echo ============================================
echo  DSH Desktop 重启脚本（会中断所有会话）
echo ============================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restart-desktop.ps1"
