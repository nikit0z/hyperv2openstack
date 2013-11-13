C:\Windows\System32\certutil.exe -f -addstore "TrustedPublisher" C:\VirtIO\redhat.cer

ping -n 180 127.0.0.1 > nul

REG DELETE HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\firstboot /f

shutdown -t 0 -r -f

