@echo off
REM install.bat - 시험 분석 스킬(카드뉴스+A4 분석지) 설치/업데이트 (더블클릭)
set "DEST=%USERPROFILE%\.claude\skills"
if not exist "%DEST%" mkdir "%DEST%"
REM 기존 버전이 있으면 깨끗이 교체(구버전 잔여 파일 방지) - 설치가 곧 업데이트
if exist "%DEST%\qt-exam-insta-analysis" rmdir /S /Q "%DEST%\qt-exam-insta-analysis"
xcopy /E /I /Y "%~dp0qt-exam-insta-analysis" "%DEST%\qt-exam-insta-analysis" >nul
echo.
echo [OK] 스킬 설치/업데이트 완료: %DEST%\qt-exam-insta-analysis
echo.
echo 쓰는 법: Claude Code에서 시험지 사진(또는 PDF) + 시험범위를 올리고
echo         "시험 분석 카드뉴스 만들어줘" 또는 "상세 분석지 만들어줘" 라고 하세요.
echo.
pause
