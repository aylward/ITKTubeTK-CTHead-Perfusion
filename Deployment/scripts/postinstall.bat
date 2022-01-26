@"%~dp0\nssm.exe" install ARGUS "%~dp0\..\argus\argus-server.exe"
@"%~dp0\nssm.exe" set ARGUS Start SERVICE_AUTO_START
@"%~dp0\nssm.exe" start ARGUS