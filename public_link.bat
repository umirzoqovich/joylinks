@echo off
title Joylinks Target CRM - Internetga Chiqarish (Public HTTPS)
echo ======================================================================
echo       JOYLINKS TARGET CRM - REKLAMA UCHUN OCHIQ INTERNET HAVOLASI
echo ======================================================================
echo.
echo 1. Oldin 'run.bat' orqali CRM ni ishga tushirganingizga ishonch hosil qiling!
echo 2. Quyida beriladigan https://... havolani nusxalang.
echo 3. Shu havolaning orqasiga '/form' qo'shib, Instagram reklamaga qo'ying!
echo.
echo Masalan: https://a.pinggy.link/form
echo ======================================================================
echo.
ssh -p 443 -R0:localhost:8000 a.pinggy.io
pause
