@echo off
REM install.bat - 시험지 분석 인스타 카드뉴스 스킬 설치 (더블클릭)
set "DEST=%USERPROFILE%\.claude\skills"
if not exist "%DEST%" mkdir "%DEST%"
xcopy /E /I /Y "%~dp0qt-exam-insta-analysis" "%DEST%\qt-exam-insta-analysis" >nul
echo.
echo [OK] 스킬 설치 완료: %DEST%\qt-exam-insta-analysis
echo.
echo 쓰는 법: Claude Code에서 시험지 사진(또는 PDF) + 시험범위를 올리고
echo         "시험 분석 카드뉴스 만들어줘" 또는 "상세 분석지 만들어줘" 라고 하세요.
echo.
pause
