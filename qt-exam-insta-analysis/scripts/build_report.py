#!/usr/bin/env python3
"""report.json → A4 상세 분석지 PDF (playwright).

사용:
  PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    python3 build_report.py report.json /mnt/user-data/outputs/<이름>/report.pdf

- 스키마: references/report-schema.md (단일 데이터 원천)
- 디자인: assets/report.css. 색은 meta.accent 한 색에서 파생(인쇄 친화 흑백+악센트 1색).
- PDF 옆에 report.html 도 남겨 디버깅/수정에 쓴다.
"""
import base64
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSS_PATH = os.path.join(HERE, "..", "assets", "report.css")


# ── 색 파생 (악센트 1색) ─────────────────────────────────
def _hex(c):
    c = str(c).strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", c):
        raise ValueError(f"잘못된 색상값: #{c}")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _css(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def accent_vars(color):
    base = _hex(color or "#1E2A78")
    soft = tuple(v * 0.10 + 255 * 0.90 for v in base)  # 흰색 90% 혼합
    return f"--accent:{_css(base)};--accent-soft:{_css(soft)}"


# ── 텍스트 헬퍼 ─────────────────────────────────────────
def e(s):
    return html.escape(str(s if s is not None else ""))


def ebr(s):
    """이스케이프 + 수동 줄바꿈(\\n)→<br>."""
    return e(s).replace("\n", "<br>")


def emph(s):
    """ebr + [[바뀐 부분]] → 강조 span (변형 분석용)."""
    return ebr(s).replace("[[", '<span class="chg">').replace("]]", "</span>")


def stars(n):
    try:
        n = max(0, min(3, int(n)))
    except (TypeError, ValueError):
        n = 0
    return "★" * n + "☆" * (3 - n)


# ── 섹션 렌더러 ─────────────────────────────────────────
def sec_h2(idx, title):
    return f'<h2 class="sec"><span class="no">{idx}.</span>{e(title)}</h2>'


def render_overview(idx, sec, base_dir):
    return sec_h2(idx, sec.get("title", "총평")) + f'<div class="overview">{ebr(sec.get("body", ""))}</div>'


def render_score_table(idx, sec, base_dir):
    body = ""
    for r in sec.get("rows", []):
        body += (f'<tr><td>{e(r.get("label",""))}</td>'
                 f'<td class="num">{e(r.get("nums",""))}</td>'
                 f'<td class="num">{e(r.get("count",""))}</td>'
                 f'<td class="score">{e(r.get("score",""))}</td></tr>')
    foot = ""
    f = sec.get("footer")
    if f:
        foot = (f'<tfoot><tr><td>{e(f.get("label",""))}</td>'
                f'<td class="num">{e(f.get("nums",""))}</td>'
                f'<td class="num">{e(f.get("count",""))}</td>'
                f'<td class="score">{e(f.get("score",""))}</td></tr></tfoot>')
    return (sec_h2(idx, sec.get("title", "유형별 배점 분석")) +
            '<table><thead><tr><th>유형</th><th class="num">문항 번호</th>'
            '<th class="num">문항수</th><th class="num">배점</th></tr></thead>'
            f'<tbody>{body}</tbody>{foot}</table>')


def render_question_table(idx, sec, base_dir):
    body = ""
    for r in sec.get("rows", []):
        body += (f'<tr><td class="num">{e(r.get("no",""))}</td>'
                 f'<td class="num">{e(r.get("score",""))}</td>'
                 f'<td>{e(r.get("qtype",""))}</td>'
                 f'<td>{e(r.get("source",""))}</td>'
                 f'<td class="num"><span class="diff">{stars(r.get("diff"))}</span></td>'
                 f'<td class="note">{ebr(r.get("note",""))}</td></tr>')
    return (sec_h2(idx, sec.get("title", "문항 전수 분석표")) +
            '<table class="qtable"><thead><tr><th class="num">번호</th><th class="num">배점</th>'
            '<th>유형</th><th>출제 근거</th><th class="num">난이도</th><th>한 줄 분석</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def render_transform_table(idx, sec, base_dir):
    body = ""
    for r in sec.get("rows", []):
        body += (f'<tr><td class="num">{e(r.get("no",""))}</td>'
                 f'<td class="sent"><div class="tf-before">원문: {emph(r.get("before",""))}</div>'
                 f'<div class="tf-after">시험: {emph(r.get("after",""))}</div></td>'
                 f'<td class="tf-point">{ebr(r.get("point",""))}</td></tr>')
    return (sec_h2(idx, sec.get("title", "교과서 원문 대비 변형 분석")) +
            '<table class="tf"><thead><tr><th class="num">문항</th><th>원문 → 시험 (바뀐 부분 표시)</th>'
            '<th>변형 포인트</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def render_deep(idx, sec, base_dir):
    out = sec_h2(idx, sec.get("title", "문항별 상세 해설"))
    for it in sec.get("items", []):
        img = ""
        crop = it.get("crop")
        if crop:
            path = crop if os.path.isabs(crop) else os.path.join(base_dir, crop)
            if not os.path.exists(path):
                raise FileNotFoundError(f"deep 해설 crop 파일 없음: {path}")
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            img = f'<img class="crop" src="data:image/png;base64,{b64}"/>'
        rows = ""
        for lbl, key in (("핵심 분석", "analysis"), ("함정", "trap"), ("처방", "tip")):
            if it.get(key):
                rows += f'<div class="row"><span class="lbl">{lbl}</span>{ebr(it[key])}</div>'
        out += (f'<div class="deep-item"><h3><span class="badge">{e(it.get("no",""))}번'
                f'{("·" + e(it["score"]) + "점") if it.get("score") else ""}</span>'
                f'{e(it.get("title",""))}</h3>{img}{rows}</div>')
    return out


def render_mapping(idx, sec, base_dir):
    body = ""
    for r in sec.get("rows", []):
        body += (f'<tr><td>{e(r.get("topic",""))}</td>'
                 f'<td class="num">{e(r.get("questions",""))}</td>'
                 f'<td>{ebr(r.get("note",""))}</td></tr>')
    return (sec_h2(idx, sec.get("title", "시험범위 → 출제 매핑")) +
            '<table><thead><tr><th>범위 항목</th><th class="num">출제 문항</th><th>비고</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def render_strategy(idx, sec, base_dir):
    out = sec_h2(idx, sec.get("title", "다음 시험 대비 전략"))
    for it in sec.get("items", []):
        out += (f'<div class="strategy-item"><div class="st-title">{e(it.get("title",""))}</div>'
                f'<div class="st-body">{ebr(it.get("body",""))}</div></div>')
    return out


RENDERERS = {
    "overview": render_overview,
    "score_table": render_score_table,
    "question_table": render_question_table,
    "transform_table": render_transform_table,
    "deep": render_deep,
    "mapping": render_mapping,
    "strategy": render_strategy,
}


def build_html(report, base_dir):
    meta = report.get("meta", {})
    with open(CSS_PATH, encoding="utf-8") as f:
        css = f.read()
    root = accent_vars(meta.get("accent"))

    parts = []
    kicker = " · ".join(x for x in (meta.get("academy"), meta.get("teacher")) if x)
    metas = []
    for label, key in (("시험일", "date"), ("총 문항", "total_questions"), ("총점", "total_score")):
        if meta.get(key) is not None:
            metas.append(f'{label} <b>{e(meta[key])}</b>')
    parts.append(
        f'<div class="report-head"><div class="kicker">{e(kicker)}</div>'
        f'<h1>{e(meta.get("title", "시험 상세 분석지"))}</h1>'
        f'<div class="meta">{" &nbsp;|&nbsp; ".join(metas)}</div></div>')

    for i, sec in enumerate(report.get("sections", []), 1):
        typ = sec.get("type")
        if typ not in RENDERERS:
            raise ValueError(f"알 수 없는 섹션 타입: {typ!r}")
        if sec.get("page_break"):
            parts.append('<div class="page-break"></div>')
        parts.append(RENDERERS[typ](i, sec, base_dir))

    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}\n'
            f':root{{{root}}}</style></head><body>{"".join(parts)}</body></html>')


def main():
    if len(sys.argv) != 3:
        sys.exit("사용: build_report.py <report.json> <출력.pdf>")
    src, out_pdf = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        report = json.load(f)
    meta = report.get("meta", {})
    accent_vars(meta.get("accent"))  # 색 조기 검증
    if not report.get("sections"):
        sys.exit("sections 가 비어 있습니다.")

    out_dir = os.path.dirname(os.path.abspath(out_pdf)) or "."
    os.makedirs(out_dir, exist_ok=True)
    html_doc = build_html(report, out_dir)
    html_path = os.path.splitext(out_pdf)[0] + ".html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright 가 필요합니다:  pip install playwright --break-system-packages")

    footer = (
        '<div style="width:100%;font-size:8px;color:#888;'
        'font-family:sans-serif;display:flex;justify-content:space-between;padding:0 12mm;">'
        f'<span>{html.escape(str(meta.get("academy", "")))}</span>'
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_doc, wait_until="networkidle")
        page.pdf(path=out_pdf, format="A4", print_background=True,
                 display_header_footer=True,
                 header_template='<div></div>', footer_template=footer,
                 margin={"top": "13mm", "bottom": "16mm", "left": "12mm", "right": "12mm"})
        browser.close()

    print(f"완료: {out_pdf}  (HTML: {html_path})")


if __name__ == "__main__":
    main()
