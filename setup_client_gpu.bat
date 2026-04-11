@echo off
title Cai dat Moi Truong GPU Chuyen Dung (CUDA 11.1)
color 0B

echo ========================================================
echo   CAI DAT MOI TRUONG GPU CHUYEN DUNG (CU111) CHO ARGO
echo   Ho tro dac biet cho cac may dung Driver tu nam 2021
echo ========================================================
echo.
echo [CANH BAO QUAN TRONG]: 
echo Thuoc dac tri nay CHI DUOC DUNG cho nhung may co Card roi NVIDIA
echo ma khong the cap nhat Driver (Bi ket o CUDA 11.1).
echo Cac may khac (chay CPU hoac GPU doi moi) vui long DONG CUA SO nay lai!
echo.
echo Ban chac chan day la may can ha cap Python khong? 
pause
echo.
echo.

echo [1] Dang tai Python 3.9.13 xuong thu muc hien tai...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe' -OutFile 'python-3.9.13-amd64.exe' -UseBasicParsing"

echo [2] Dang cai dat Python 3.9.13 tang ngam (Silent Install)...
echo Vui long doi khoang 1-2 phut. Khong tat cua so nay!
start /wait python-3.9.13-amd64.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

set PY39_PATH=%LocalAppData%\Programs\Python\Python39\python.exe

if not exist "%PY39_PATH%" (
    echo [LOI] Khong tim thay ban cai Python 3.9 tai %PY39_PATH%.
    echo He thong yeu cau khoi dong lai CMD hoac chay bang quyen Admin.
    pause
    exit /b
)

echo.
echo [3] Dang xoa moi truong venv hien tai (Neu co)...
if exist "venv" (
    rmdir /s /q venv
)

echo [4] Tao moi truong ao venv dua tren Python 3.9...
"%PY39_PATH%" -m venv venv

echo [5] Dang cap nhat pip cua venv...
venv\Scripts\python.exe -m pip install --upgrade pip

echo [6] Dang cai dat PyTorch 1.10.1 (CUDA 11.1) - Ban dac biet...
venv\Scripts\python.exe -m pip install torch==1.10.1+cu111 -f https://download.pytorch.org/whl/cu111/torch_stable.html

echo [7] Cai dat cac thu vien lien quan cua du an (pandas, numpy, v.v.)...
venv\Scripts\python.exe -m pip install pandas numpy paho-mqtt requests pyarrow fastparquet matplotlib huggingface_hub

echo.
echo [8] Dang don dep rac...
del python-3.9.13-amd64.exe

echo.
echo ========================================================
echo CAI DAT HOAN TAT THANG LOI!
echo Bay gio dung venv nay se kich hoat duoc card man hinh cu!
echo.
echo Luu y: Ban Python 3.14 cu tren may se hoat dong doc lap,
echo KHONG gay xung dot gi voi du an Argo cua chung ta nua.
echo De tiet kiem dung luong, ban co the vao "Add or Remove Programs" 
echo cua Windows va go bo bieu tuong "Python 3.14.x" neu muon.
echo.
echo Bay gio hay tat cua so nay, roi chay CHAY_AGENT.bat de vao viec!
echo.
echo Nhan phim bat ky de thoat...
echo ========================================================
pause
