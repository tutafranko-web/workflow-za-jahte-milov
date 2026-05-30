@echo off
REM Daily charter outreach SMTP send — auto-triggered by Windows Task Scheduler at 09:00
REM Logs to job-outreach/logs/daily-YYYY-MM-DD.log

cd /d "c:\Users\WWW\Desktop\ai\claude code\job-outreach"

if not exist "logs" mkdir logs

set LOGFILE=logs\daily-%date:~-4,4%-%date:~-7,2%-%date:~-10,2%.log

echo === Daily run started at %date% %time% === >> %LOGFILE%
py src\smtp_sender.py --batch 20 >> %LOGFILE% 2>&1
echo === Daily run finished at %date% %time% === >> %LOGFILE%
echo. >> %LOGFILE%
