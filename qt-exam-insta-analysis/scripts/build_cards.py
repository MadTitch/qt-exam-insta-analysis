#!/usr/bin/env python3
"""deck.json → 1080×1080 캐러셀 카드 PNG.

사용:
  PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    python3 build_cards.py deck.json /mnt/user-data/outputs/<게시물명>/

카드 타입: cover, scope, score_table, feature_list, deep_dive, strategy, outro.
디자인은 assets/card.css, 색은 brand.color 에서 derive_palette() 로 파생한다.
스키마는 references/deck-schema.md.
"""
import base64
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
STYLES = ("A", "B", "C", "D", "E", "F", "G", "H", "I")


def load_css(style):
    """base.css + theme_<style>.css 를 합쳐 반환. style 은 A/B/C."""
    style = (style or "A").upper()
    if style not in STYLES:
        sys.exit(f"style 은 {STYLES} 중 하나여야 합니다: {style!r}")
    with open(os.path.join(ASSETS, "base.css"), encoding="utf-8") as f:
        css = f.read()
    theme = os.path.join(ASSETS, f"theme_{style.lower()}.css")
    if os.path.exists(theme):
        with open(theme, encoding="utf-8") as f:
            css += "\n/* theme " + style + " */\n" + f.read()
    return css

# 책더미 일러스트(하단 우측 공용)
BOOKS_SVG = """<svg class="books" viewBox="0 0 150 110" xmlns="http://www.w3.org/2000/svg">
  <rect x="6" y="74" width="120" height="26" rx="4" fill="#ffffff" stroke="#111" stroke-width="4"/>
  <rect x="18" y="50" width="110" height="26" rx="4" fill="var(--brand-tint)" stroke="#111" stroke-width="4"/>
  <rect x="10" y="26" width="100" height="26" rx="4" fill="#ffffff" stroke="#111" stroke-width="4"/>
  <line x1="40" y1="26" x2="40" y2="52" stroke="#111" stroke-width="3"/>
  <line x1="52" y1="50" x2="52" y2="76" stroke="#111" stroke-width="3"/>
</svg>"""


# ── 색 파생 ─────────────────────────────────────────────
def _hex(c):
    c = c.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", c):
        raise ValueError(f"잘못된 색상값: #{c}")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _css(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def _mul(rgb, f):
    return tuple(v * f for v in rgb)


def _mix_white(rgb, w):  # w=흰색 비율
    return tuple(v * (1 - w) + 255 * w for v in rgb)


def derive_palette(color):
    base = _hex(color)
    return {
        "--brand": _css(base),
        "--brand-dark": _css(_mul(base, 0.70)),
        "--brand-ink": _css(_mul(base, 0.35)),
        "--brand-tint": _css(_mix_white(base, 0.82)),
        "--brand-tint2": _css(_mix_white(base, 0.92)),
    }


# 큐레이션 색 팔레트 프리셋 (primary + 조화로운 dark). 라이트 톤은 primary에서 파생.
# brand.palette 로 이름을 지정하면 이 조합을 쓴다. (coolors 류 조합에서 고른 값)
PALETTES = {
    "sunset":  {"brand": "#E8590C", "dark": "#A6410A"},  # 주황·머스타드(현재)
    "navy":    {"brand": "#3B4FD8", "dark": "#1E2A78"},  # 인디고 네이비
    "ocean":   {"brand": "#1C7ED6", "dark": "#0B4A8F"},  # 오션 블루
    "teal":    {"brand": "#0CA6A0", "dark": "#0A5854"},  # 청록
    "forest":  {"brand": "#2F9E44", "dark": "#14532D"},  # 포레스트 그린
    "plum":    {"brand": "#8B3FA6", "dark": "#4A1D5E"},  # 플럼 퍼플
    "berry":   {"brand": "#C2255C", "dark": "#6D1235"},  # 베리 핑크
    "rose":    {"brand": "#E64980", "dark": "#8A2350"},  # 로즈
    "gold":    {"brand": "#C7911F", "dark": "#6E4E10"},  # 머스터드 골드
    "slate":   {"brand": "#495779", "dark": "#252D45"},  # 슬레이트(차분)
}


def resolve_palette(brand):
    """brand.palette(프리셋 이름) 우선, 없으면 brand.color 단색 파생."""
    name = brand.get("palette")
    if name:
        if name not in PALETTES:
            sys.exit(f"palette 는 {tuple(PALETTES)} 중 하나여야 합니다: {name!r}")
        p = PALETTES[name]
        b, dk = _hex(p["brand"]), _hex(p["dark"])
    elif brand.get("color"):
        b, dk = _hex(brand["color"]), _mul(_hex(brand["color"]), 0.70)
    else:
        sys.exit("brand.palette 또는 brand.color 중 하나가 필요합니다.")
    return {
        "--brand": _css(b),
        "--brand-dark": _css(dk),
        "--brand-ink": _css(_mul(dk, 0.55)),
        "--brand-tint": _css(_mix_white(b, 0.83)),
        "--brand-tint2": _css(_mix_white(b, 0.93)),
    }


def e(s):
    return html.escape(str(s if s is not None else ""))


def ebr(s):
    """이스케이프 후 수동 줄바꿈(\\n)을 <br>로. 본문에서 애매한 구절을 미리 끊을 때 쓴다."""
    return e(s).replace("\n", "<br>")


def emph(s):
    """ebr + [[바뀐 부분]] → 강조 span. transform 카드에서 변형 지점을 표시할 때."""
    return ebr(s).replace("[[", '<span class="chg">').replace("]]", "</span>")


# ── 카드 공용 조각 ──────────────────────────────────────
def watermark(brand):
    return f'<div class="watermark">{e(brand.get("academy",""))}</div>{BOOKS_SVG}'


def tab(card):
    t = card.get("tab")
    return f'<div class="tab">{e(t)}</div>' if t else ""


def heading(card):
    h = card.get("heading")
    return f'<h1>{e(h)}</h1>' if h else ""


# ── 카드 타입별 본문 ────────────────────────────────────
def card_cover(card, brand):
    teacher = brand.get("teacher")
    tea = f'<div class="c-teacher">{e(teacher)}</div>' if teacher else ""
    return f"""<div class="cover">
      <div class="c-title">{e(brand.get('title',''))}</div>
      <div class="c-sub">{e(brand.get('subtitle',''))}</div>
      {tea}
    </div>{watermark(brand)}"""


def card_outro(card, brand):
    tags = "  ".join(brand.get("hashtags", []))
    return f"""<div class="outro">
      <div class="o-slogan">{e(brand.get('slogan',''))}</div>
      <div class="o-tags">{e(tags)}</div>
      <div class="o-academy">{e(brand.get('academy',''))}{(' · ' + e(brand['teacher'])) if brand.get('teacher') else ''}</div>
    </div>{watermark(brand)}"""


def card_scope(card, brand):
    chips = "".join(f'<div class="chip">{e(x)}</div>' for x in card.get("items", []))
    return f"""{tab(card)}<div class="card">{heading(card)}
      <div class="chips">{chips}</div>
    </div>{watermark(brand)}"""


def card_score_table(card, brand):
    body = ""
    for r in card.get("rows", []):
        body += (f'<tr><td>{e(r.get("label",""))}</td>'
                 f'<td class="num">{e(r.get("nums",""))}</td>'
                 f'<td class="score">{e(r.get("score",""))}</td></tr>')
    foot = ""
    f = card.get("footer")
    if f:
        foot = (f'<tfoot><tr><td>{e(f.get("label",""))}</td>'
                f'<td class="num">{e(f.get("nums",""))}</td>'
                f'<td class="score">{e(f.get("score",""))}</td></tr></tfoot>')
    return f"""{tab(card)}<div class="card">{heading(card)}
      <table class="score">
        <thead><tr><th>유형</th><th class="num">문항</th><th class="score">배점</th></tr></thead>
        <tbody>{body}</tbody>{foot}
      </table>
    </div>{watermark(brand)}"""


def _item_blocks(card):
    out = ""
    for it in card.get("items", []):
        out += (f'<div class="item"><div class="it-title">{ebr(it.get("title",""))}</div>'
                f'<div class="it-body">{ebr(it.get("body",""))}</div></div>')
    return f'<div class="items">{out}</div>'


def card_feature_list(card, brand):
    return f"""{tab(card)}<div class="card">{heading(card)}{_item_blocks(card)}</div>{watermark(brand)}"""


def card_strategy(card, brand):
    return f"""{tab(card)}<div class="card">{heading(card)}{_item_blocks(card)}</div>{watermark(brand)}"""


def card_deep_dive(card, brand, base_dir):
    img_html = ""
    crop = card.get("crop")
    if crop:
        path = crop if os.path.isabs(crop) else os.path.join(base_dir, crop)
        if not os.path.exists(path):
            raise FileNotFoundError(f"deep_dive crop 파일 없음: {path}")
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        img_html = f'<img src="data:image/png;base64,{b64}"/>'
    title = card.get("title", "")
    return f"""{tab(card)}<div class="card">
      <h1 class="dd-title">{e(title)}</h1>
      <div class="dd-crop">{img_html}</div>
      <div class="dd-body">{ebr(card.get('body',''))}</div>
    </div>{watermark(brand)}"""


def card_transform(card, brand):
    rows = ""
    for r in card.get("rows", []):
        point = f'<div class="tf-point">→ {e(r.get("point",""))}</div>' if r.get("point") else ""
        rows += (
            '<div class="tf-row">'
            f'<div class="tf-line tf-before"><span class="lbl">원문</span>{emph(r.get("before",""))}</div>'
            f'<div class="tf-line tf-after"><span class="lbl">시험</span>{emph(r.get("after",""))}</div>'
            f'{point}</div>'
        )
    return f"""{tab(card)}<div class="card">{heading(card)}<div class="transform">{rows}</div></div>{watermark(brand)}"""


RENDERERS = {
    "cover": card_cover,
    "outro": card_outro,
    "scope": card_scope,
    "score_table": card_score_table,
    "feature_list": card_feature_list,
    "strategy": card_strategy,
    "transform": card_transform,
}


def page_html(card, brand, css, base_dir, idx=None, total=None):
    typ = card.get("type")
    if typ == "deep_dive":
        body = card_deep_dive(card, brand, base_dir)
    elif typ in RENDERERS:
        body = RENDERERS[typ](card, brand)
    else:
        raise ValueError(f"알 수 없는 카드 타입: {typ!r}")
    root_vars = ";".join(f"{k}:{v}" for k, v in resolve_palette(brand).items())
    # NOTE: inject palette vars AFTER the stylesheet so they override base.css :root defaults.
    pageno = f'<div class="pageno">{idx} / {total}</div>' if idx else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>
{css}
:root{{{root_vars}}}</style></head>
<body><div class="canvas">{body}{pageno}</div></body></html>"""


def representative_card(cards):
    """디자인 샘플로 보여줄 대표 카드 1장 — 시각적으로 풍부하고 외부 파일이 필요 없는 것 우선."""
    order = ["score_table", "feature_list", "strategy", "scope", "deep_dive", "cover", "outro"]
    by = {}
    for c in cards:
        by.setdefault(c.get("type"), c)
    for t in order:
        if t in by:
            return by[t]
    return cards[0]


def main():
    argv = sys.argv[1:]
    samples = "--samples" in argv
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) != 2:
        sys.exit("사용: build_cards.py <deck.json> <출력폴더>/ [--samples]")
    deck_path, out_dir = pos

    with open(deck_path, encoding="utf-8") as f:
        deck = json.load(f)
    brand = deck["brand"]
    resolve_palette(brand)  # 팔레트/색 유효성 조기 검증 (palette 또는 color 필요)
    cards = deck.get("cards", [])
    if not cards:
        sys.exit("cards 가 비어 있습니다.")

    os.makedirs(out_dir, exist_ok=True)
    base_dir = os.path.abspath(out_dir)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright 가 필요합니다:  pip install playwright --break-system-packages")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080},
                                device_scale_factor=2)

        if samples:  # 디자인 샘플 A/B/C — 대표 카드 1장을 세 테마로
            rep = representative_card(cards)
            for st in STYLES:
                css = load_css(st)
                out = os.path.join(out_dir, f"sample_{st}.png")
                page.set_content(page_html(rep, brand, css, base_dir), wait_until="networkidle")
                page.locator(".canvas").screenshot(path=out)
                print(f"  sample_{st}.png  (테마 {st}, '{rep.get('type')}' 카드)")
            browser.close()
            print(f"디자인 샘플 3장 → {out_dir}  (A/B/C 중 선택)")
            return

        style = brand.get("style", "A")
        css = load_css(style)
        if len(cards) > 20:
            print(f"⚠️  카드 {len(cards)}장 — 인스타 캐러셀은 최대 20장입니다. 줄이세요.")
        for i, card in enumerate(cards, 1):
            page.set_content(page_html(card, brand, css, base_dir, i, len(cards)), wait_until="networkidle")
            out = os.path.join(out_dir, f"card_{i:02d}.png")
            page.locator(".canvas").screenshot(path=out)
            print(f"  card_{i:02d}.png  ({card.get('type')})")
        browser.close()

    print(f"완료: {len(cards)}장 (테마 {brand.get('style','A')}) → {out_dir}")


if __name__ == "__main__":
    main()
