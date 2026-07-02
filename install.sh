#!/usr/bin/env bash
# install.sh — 시험지 분석 인스타 카드뉴스 스킬을 Claude Code에 설치한다.
# 사용: 이 파일이 있는 폴더에서  bash install.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude/skills"
mkdir -p "$DEST"
cp -R "$DIR/qt-exam-insta-analysis" "$DEST/"
echo "✅ 스킬 설치 완료 → $DEST/qt-exam-insta-analysis"
echo ""
echo "쓰는 법: Claude Code에서 시험지 사진(또는 PDF) + 시험범위를 올리고"
echo "        \"시험 분석 카드뉴스 만들어줘\" 또는 \"상세 분석지 만들어줘\" 라고 하세요."
echo ""
echo "* 첫 실행 시 렌더링 엔진(playwright chromium)·Pillow·numpy를 자동 설치합니다."
