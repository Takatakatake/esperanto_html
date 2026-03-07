#!/usr/bin/env python3
"""
ruby_css_verifier.py — エスペラントHTML ルビCSSクラス一括検証・修正スクリプト

使い方:
  検証のみ（ドライラン）:
    python3 ruby_css_verifier.py rondolegada_materialoj_202603_enhavoj_JA.html

  全件修正（バックアップ自動作成）:
    python3 ruby_css_verifier.py rondolegada_materialoj_202603_enhavoj_JA.html --fix

  境界ケースをスキップして修正（安全モード、推奨）:
    python3 ruby_css_verifier.py *.html --fix --margin 0.05

  詳細表示:
    python3 ruby_css_verifier.py *.html --verbose

  境界ケースのみ表示:
    python3 ruby_css_verifier.py *.html --boundary-only

アルゴリズム:
  §2.3 に準拠。ratio = pixel_width(rt) / pixel_width(rb) を計算し、
  閾値テーブルでCSSクラスを決定。XXXS_S/XXS_S の場合は <br> を
  ピクセル幅ベースで挿入する。

  --margin M を指定すると、ratio が閾値から M 以内のケースは
  「境界ケース」として修正をスキップする（安全措置）。
"""

import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime

# ─────────────────────────────────────────────────────
# パス設定
# ─────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WIDTH_JSON = os.path.join(SCRIPT_DIR, "Unicode_BMP全范围文字幅(宽)_Arial16.json")

# ─────────────────────────────────────────────────────
# ピクセル幅計算
# ─────────────────────────────────────────────────────
_width_data = None


def _load_width_data():
    global _width_data
    if _width_data is None:
        with open(WIDTH_JSON, "r", encoding="utf-8") as f:
            _width_data = json.load(f)
    return _width_data


def measure_text_width(text, width_data=None):
    """文字列のピクセル幅合計を返す（Arial 16px 基準）"""
    if width_data is None:
        width_data = _load_width_data()
    total = 0.0
    for ch in text:
        total += width_data.get(ch, 8)
    return total


# ─────────────────────────────────────────────────────
# <br> 挿入（ピクセル幅ベース）
# ─────────────────────────────────────────────────────
def insert_br_at_half_width(text, width_data=None):
    """ピクセル幅の1/2地点で <br> を挿入（XXS_S 用）"""
    if width_data is None:
        width_data = _load_width_data()
    total_w = measure_text_width(text, width_data)
    half = total_w / 2.0
    cumul = 0.0
    for i, ch in enumerate(text):
        cumul += width_data.get(ch, 8)
        if cumul >= half and i < len(text) - 1:
            return text[: i + 1] + "<br>" + text[i + 1 :]
    return text


def insert_br_at_third_width(text, width_data=None):
    """ピクセル幅の1/3・2/3地点で <br> を挿入（XXXS_S 用）"""
    if width_data is None:
        width_data = _load_width_data()
    total_w = measure_text_width(text, width_data)
    third1 = total_w / 3.0
    third2 = total_w * 2.0 / 3.0
    cumul = 0.0
    parts = []
    current = []
    br_count = 0
    for ch in text:
        cumul += width_data.get(ch, 8)
        current.append(ch)
        if br_count == 0 and cumul >= third1:
            parts.append("".join(current))
            current = []
            br_count += 1
        elif br_count == 1 and cumul >= third2:
            parts.append("".join(current))
            current = []
            br_count += 1
    if current:
        parts.append("".join(current))
    return "<br>".join(parts)


# ─────────────────────────────────────────────────────
# CSSクラス決定
# ─────────────────────────────────────────────────────
THRESHOLDS = [
    (6.0, "XXXS_S"),
    (3.0, "XXS_S"),
    (9 / 4, "XS_S"),
    (9 / 5, "S_S"),
    (9 / 6, "M_M"),
    (9 / 7, "L_L"),
    (9 / 8, "XL_L"),
]

ALL_THRESHOLD_VALUES = [t[0] for t in THRESHOLDS]


def calc_css_class(rb_text, rt_text_clean, width_data=None):
    """(rb, rt) からCSSクラスと ratio を返す。"""
    if width_data is None:
        width_data = _load_width_data()
    rb_w = measure_text_width(rb_text, width_data)
    rt_w = measure_text_width(rt_text_clean, width_data)
    if rb_w == 0:
        return "XXL_L", 0.0
    ratio = rt_w / rb_w
    for threshold, cls in THRESHOLDS:
        if ratio > threshold:
            return cls, ratio
    return "XXL_L", ratio


def nearest_threshold_distance(ratio):
    """ratio から最寄りの閾値までの絶対距離を返す。"""
    if not ALL_THRESHOLD_VALUES:
        return float("inf")
    return min(abs(ratio - th) for th in ALL_THRESHOLD_VALUES)


def build_correct_rt(rt_text_clean, css_class, width_data=None):
    """CSSクラスに基づき <br> を挿入した rt テキストを返す。"""
    if css_class == "XXXS_S":
        return insert_br_at_third_width(rt_text_clean, width_data)
    elif css_class == "XXS_S":
        return insert_br_at_half_width(rt_text_clean, width_data)
    else:
        return rt_text_clean


# ─────────────────────────────────────────────────────
# Ruby パース
# ─────────────────────────────────────────────────────
RUBY_RE = re.compile(
    r'<ruby>([^<]+)<rt\s+class="([^"]+)">([^<]*(?:<br>[^<]*)*)</rt></ruby>'
)


def parse_rubies(content):
    """全 ruby タグを解析し、(match, rb, css, rt_raw, rt_clean) のリストを返す。"""
    results = []
    for m in RUBY_RE.finditer(content):
        rb = m.group(1)
        css = m.group(2)
        rt_raw = m.group(3)
        rt_clean = rt_raw.replace("<br>", "")
        results.append((m, rb, css, rt_raw, rt_clean))
    return results


# ─────────────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────────────
def verify_file(filepath, fix=False, verbose=False, margin=0.0, boundary_only=False):
    width_data = _load_width_data()

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    rubies = parse_rubies(content)
    total = len(rubies)
    all_mismatches = []
    fixable = []
    skipped_boundary = []

    for m, rb, actual_css, rt_raw, rt_clean in rubies:
        expected_css, ratio = calc_css_class(rb, rt_clean, width_data)
        if actual_css != expected_css:
            dist = nearest_threshold_distance(ratio)
            correct_rt = build_correct_rt(rt_clean, expected_css, width_data)
            entry = {
                "match": m,
                "rb": rb,
                "rt_clean": rt_clean,
                "rt_raw": rt_raw,
                "actual_css": actual_css,
                "expected_css": expected_css,
                "correct_rt": correct_rt,
                "ratio": ratio,
                "threshold_dist": dist,
            }
            all_mismatches.append(entry)
            if margin > 0 and dist < margin:
                skipped_boundary.append(entry)
            else:
                fixable.append(entry)

    # ─── レポート出力 ───
    fname = os.path.basename(filepath)
    print(f"\n{'='*70}")
    print(f"  {fname}")
    print(f"  Total ruby: {total}   Mismatched: {len(all_mismatches)} ({len(all_mismatches)/total*100:.1f}%)")
    if margin > 0:
        print(f"  Margin: {margin}  Fixable: {len(fixable)}  Boundary(skip): {len(skipped_boundary)}")
    print(f"{'='*70}")

    if not all_mismatches:
        print("  No CSS mismatches found.")
        return 0

    # 表示対象を選択
    if boundary_only:
        display_list = skipped_boundary if margin > 0 else [
            e for e in all_mismatches if e["threshold_dist"] < 0.05
        ]
        label = "Boundary cases"
    else:
        display_list = fixable if margin > 0 else all_mismatches
        label = "Fixable mismatches" if margin > 0 else "All mismatches"

    # ユニークペア集計
    pair_counts = Counter()
    for mm in display_list:
        key = (mm["rb"], mm["rt_clean"], mm["actual_css"], mm["expected_css"])
        pair_counts[key] += 1

    limit = 80 if verbose else 25
    print(f"\n  {label}: {len(display_list)} instances, {len(pair_counts)} unique pairs")
    print(f"  {'rb':<20} {'rt':<16} {'actual':>8} {'expected':>8} {'count':>5} {'ratio':>8} {'dist':>7}")
    print(f"  {'-'*20} {'-'*16} {'-'*8} {'-'*8} {'-'*5} {'-'*8} {'-'*7}")

    for (rb, rt, actual, expected), cnt in pair_counts.most_common(limit):
        rt_disp = rt[:14] + ".." if len(rt) > 16 else rt
        _, ratio = calc_css_class(rb, rt, width_data)
        dist = nearest_threshold_distance(ratio)
        print(f"  {rb:<20} {rt_disp:<16} {actual:>8} {expected:>8} {cnt:>5} {ratio:>8.4f} {dist:>7.4f}")

    if len(pair_counts) > limit:
        print(f"  ... and {len(pair_counts) - limit} more (use --verbose)")

    # ─── 修正実行 ───
    if fix and fixable:
        print(f"\n  Applying {len(fixable)} fixes (skipping {len(skipped_boundary)} boundary cases)...")

        # バックアップ作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath + f".bak_{timestamp}"
        shutil.copy2(filepath, backup_path)
        print(f"  Backup: {backup_path}")

        # 後ろから置換（位置がずれないように）
        new_content = content
        for mm in sorted(fixable, key=lambda x: x["match"].start(), reverse=True):
            m = mm["match"]
            new_tag = (
                f'<ruby>{mm["rb"]}'
                f'<rt class="{mm["expected_css"]}">'
                f'{mm["correct_rt"]}</rt></ruby>'
            )
            start, end = m.start(), m.end()
            new_content = new_content[:start] + new_tag + new_content[end:]

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        # 修正後の再検証
        with open(filepath, "r", encoding="utf-8") as f:
            verify_content = f.read()
        post_rubies = parse_rubies(verify_content)
        post_all = 0
        post_within_margin = 0
        for pm, rb, actual_css, rt_raw, rt_clean in post_rubies:
            expected_css, ratio = calc_css_class(rb, rt_clean, width_data)
            if actual_css != expected_css:
                post_all += 1
                dist = nearest_threshold_distance(ratio)
                if margin > 0 and dist < margin:
                    post_within_margin += 1

        post_real = post_all - post_within_margin
        print(f"  Post-fix: {post_all} total mismatches ({post_within_margin} boundary, {post_real} real)")
        if post_real == 0:
            print("  ALL NON-BOUNDARY CSS CLASSES NOW CORRECT!")
        print(f"  Fixed: {filepath}")
    elif fix and not fixable:
        if skipped_boundary:
            print(f"\n  All {len(skipped_boundary)} mismatches are boundary cases (within margin {margin}). Nothing to fix.")
        else:
            print("\n  No mismatches to fix.")

    return len(all_mismatches)


def main():
    parser = argparse.ArgumentParser(
        description="エスペラントHTML ルビCSSクラス一括検証・修正"
    )
    parser.add_argument("files", nargs="+", help="対象HTMLファイル")
    parser.add_argument(
        "--fix", action="store_true",
        help="不一致を自動修正する（バックアップ自動作成）",
    )
    parser.add_argument(
        "--margin", type=float, default=0.0,
        help="境界スキップ幅: ratio が閾値から M 以内のケースをスキップ (推奨: 0.05)",
    )
    parser.add_argument(
        "--boundary-only", action="store_true",
        help="境界ケースのみを表示 (--margin 未指定時は dist<0.05 を表示)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="詳細表示（最大80件）",
    )
    args = parser.parse_args()

    if not os.path.exists(WIDTH_JSON):
        print(f"ERROR: Width data not found: {WIDTH_JSON}", file=sys.stderr)
        sys.exit(1)

    total_mismatches = 0
    for filepath in args.files:
        if not os.path.exists(filepath):
            print(f"WARNING: File not found: {filepath}", file=sys.stderr)
            continue
        total_mismatches += verify_file(
            filepath,
            fix=args.fix,
            verbose=args.verbose,
            margin=args.margin,
            boundary_only=args.boundary_only,
        )

    print(f"\n{'='*70}")
    print(f"  Total mismatches across all files: {total_mismatches}")
    if args.fix:
        if args.margin > 0:
            print(f"  Fixed (with margin={args.margin}, boundary cases skipped).")
        else:
            print("  All files have been fixed (backups created).")
    else:
        print("  Run with --fix to apply corrections.")
        if args.margin == 0:
            print("  Recommended: --fix --margin 0.05 (skip boundary cases)")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
