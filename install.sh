#!/usr/bin/env bash
# install.sh — 시험 분석 스킬(카드뉴스+A4 분석지)을 Claude Code에 설치/업데이트한다.
# 사용: 이 파일이 있는 폴더에서  bash install.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude/skills"
mkdir -p "$DEST"
# 기존 버전이 있으면 깨끗이 교체(구버전 잔여 파일 방지) — 설치가 곧 업데이트
rm -rf "$DEST/qt-exam-insta-analysis"
cp -R "$DIR/qt-exam-insta-analysis" "$DEST/"
echo "✅ 스킬 설치/업데이트 완료 → $DEST/qt-exam-insta-analysis"
echo ""
echo "쓰는 법: Claude Code에서 시험지 사진(또는 PDF) + 시험범위를 올리고"
echo "        \"시험 분석 카드뉴스 만들어줘\" 또는 \"상세 분석지 만들어줘\" 라고 하세요."
echo ""
echo "* 첫 실행 시 렌더링 엔진(playwright chromium)·Pillow·numpy를 자동 설치합니다."
