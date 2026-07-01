#!/usr/bin/env python3
"""문항 크롭 + 자동 모자이크.

시험지 페이지 이미지에서 한 문항 영역을 잘라내고, 민감 영역(정답 표기·정답이
노출되는 선지)을 모자이크(픽셀화)한다.

핵심 정책 — "문제 캡처 후 일부를 모자이크로 가린다":
  학교 시험지를 통째로 그대로 게시하는 것은 안 되지만, 문항을 캡처한 뒤 문항의
  일부를 모자이크로 가리면 활용할 수 있다(교육청 답변 근거). 따라서 deep_dive 에
  넣는 모든 크롭은 정답/핵심 노출부를 반드시 한 군데 이상 모자이크해야 한다.

좌표는 0~1 비율(기본) 또는 픽셀(--px). 좌상단(0,0)~우하단(1,1).

사용 예:
  # 1) 좌표 잡기용 격자 미리보기(10% 격자 + 좌표 라벨)부터 본다
  python3 crop_question.py page2.png --grid -o crops/_grid_page2.png

  # 2) 문항 박스를 잘라내고, 정답 영역 2곳을 모자이크
  python3 crop_question.py page2.png \
      --box 0.08,0.42,0.94,0.66 \
      --mask 0.70,0.44,0.92,0.50 \
      --mask 0.10,0.60,0.40,0.66 \
      -o crops/q14.png

출력:
  crops/q14.png       잘리고 모자이크된 PNG
  crops/q14.json      재현/검수용 메타(원본·box·mask 좌표). 마스크가 0개면 경고.
"""
import argparse
import json
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow 가 필요합니다:  pip install pillow --break-system-packages")


def parse_box(spec):
    parts = [float(x) for x in spec.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"좌표는 x0,y0,x1,y1 4개여야 합니다: {spec!r}")
    return parts


def to_px(box, w, h, is_px):
    if is_px:
        x0, y0, x1, y1 = box
    else:
        x0, y0, x1, y1 = box[0] * w, box[1] * h, box[2] * w, box[3] * h
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    # 클램프
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    return int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))


def remove_marks(img):
    """색으로 손글씨 채점 표기를 지운다 — 빨강(빨간펜 동그라미/체크)과
    중간톤 회색(연필 ○·체크)을 흰색으로. 검정 인쇄 글자는 남는다.

    좌표 기반 모자이크가 사진 원근 왜곡 때문에 빗나갈 때 훨씬 안정적이다.
    pencil/pen 으로 채점된 시험지(○·✓·빨간 동그라미)에 권장.
    needs numpy.
    """
    try:
        import numpy as np
    except ImportError:
        sys.exit("--remove-marks 에는 numpy 가 필요합니다:  pip install numpy --break-system-packages")
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299 * R + 0.587 * G + 0.114 * B
    red = (R - G > 22) & (R - B > 22)          # 빨간펜
    gray = (lum > 108) & (lum < 230)           # 연필 중간톤(검정 인쇄<108, 배경>230 제외)
    out = a.copy()
    out[red | gray] = [255, 255, 255]
    return Image.fromarray(out.astype("uint8"))


def pixelate(region, block=14):
    """영역을 잘게 줄였다 키워 픽셀화(모자이크)."""
    w, h = region.size
    small = region.resize(
        (max(1, w // block), max(1, h // block)), Image.NEAREST
    )
    return small.resize((w, h), Image.NEAREST)


def draw_grid(img):
    """10% 격자 + 비율 좌표 라벨을 그린 미리보기."""
    g = img.convert("RGB").copy()
    d = ImageDraw.Draw(g)
    w, h = g.size
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", max(12, w // 70))
    except Exception:
        font = ImageFont.load_default()
    for i in range(1, 10):
        x = int(w * i / 10)
        y = int(h * i / 10)
        d.line([(x, 0), (x, h)], fill=(255, 0, 0), width=1)
        d.line([(0, y), (w, y)], fill=(255, 0, 0), width=1)
        d.text((x + 2, 2), f"{i/10:.1f}", fill=(255, 0, 0), font=font)
        d.text((2, y + 2), f"{i/10:.1f}", fill=(255, 0, 0), font=font)
    return g


def main():
    ap = argparse.ArgumentParser(description="문항 크롭 + 자동 모자이크")
    ap.add_argument("page", help="시험지 페이지 이미지 경로")
    ap.add_argument("-o", "--out", help="출력 PNG 경로")
    ap.add_argument("--box", type=parse_box, help="잘라낼 문항 영역 x0,y0,x1,y1")
    ap.add_argument("--mask", type=parse_box, action="append", default=[],
                    help="모자이크할 영역(반복 가능) x0,y0,x1,y1. box 기준이 아니라 page 기준 좌표.")
    ap.add_argument("--px", action="store_true", help="좌표를 비율(0~1) 대신 픽셀로 해석")
    ap.add_argument("--block", type=int, default=14, help="모자이크 블록 크기(클수록 더 거침)")
    ap.add_argument("--grid", action="store_true", help="격자 미리보기만 출력하고 종료")
    ap.add_argument("--remove-marks", action="store_true",
                    help="빨간펜/연필 채점 표기를 색으로 제거(원근 왜곡에 강함). --mask 와 함께 쓸 수 있음")
    args = ap.parse_args()

    if not os.path.exists(args.page):
        sys.exit(f"페이지 이미지를 찾을 수 없음: {args.page}")
    img = Image.open(args.page).convert("RGB")
    W, H = img.size

    # 격자 미리보기 모드
    if args.grid:
        out = args.out or f"_grid_{os.path.basename(args.page)}"
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        draw_grid(img).save(out)
        print(f"격자 미리보기 저장: {out}  (페이지 {W}x{H}px)")
        return

    if not args.box:
        sys.exit("--box 가 필요합니다. 먼저 --grid 로 좌표를 잡으세요.")
    if not args.out:
        sys.exit("-o/--out 출력 경로가 필요합니다.")

    bx = to_px(args.box, W, H, args.px)

    # page 좌표계의 mask 를 적용한 뒤 box 로 자른다(마스크가 box 경계를 걸쳐도 안전).
    work = img.copy()
    applied = []
    for m in args.mask:
        mx = to_px(m, W, H, args.px)
        if mx[2] <= mx[0] or mx[3] <= mx[1]:
            continue
        region = work.crop(mx)
        work.paste(pixelate(region, args.block), mx)
        applied.append(mx)

    crop = work.crop(bx)
    if args.remove_marks:
        crop = remove_marks(crop)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    crop.save(args.out)

    meta = {
        "source_page": os.path.abspath(args.page),
        "page_size_px": [W, H],
        "box_px": bx,
        "mask_px": applied,
        "remove_marks": bool(args.remove_marks),
        "block": args.block,
        "coord_mode": "px" if args.px else "ratio",
    }
    meta_path = os.path.splitext(args.out)[0] + ".json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    rm = " +채점표기제거" if args.remove_marks else ""
    print(f"크롭 저장: {args.out}  ({crop.size[0]}x{crop.size[1]}px), 마스크 {len(applied)}개{rm}")
    print(f"메타 저장: {meta_path}")
    if not applied and not args.remove_marks:
        print("⚠️  모자이크가 0개입니다. deep_dive 크롭은 정답/핵심 노출부를 반드시 가려야 합니다.")
    print("→ 이제 잘린 PNG 를 view 로 열어 정답이 노출됐는지 직접 확인하세요(누락 시 --mask 추가).")


if __name__ == "__main__":
    main()
