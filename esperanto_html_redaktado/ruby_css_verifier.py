#!/usr/bin/env python3
"""
ruby_css_verifier.py — エスペラントHTML ルビCSSクラス一括検証・修正スクリプト

使い方:
  検証のみ（ドライラン）:
    python3 ruby_css_verifier.py rondolegado/2026-03/rondolegada_materialoj_202603_enhavoj_JA.html

  全件修正（バックアップ自動作成）:
    python3 ruby_css_verifier.py rondolegado/2026-03/rondolegada_materialoj_202603_enhavoj_JA.html --fix

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

  --margin M を指定すると、ratio が閾値から M 以内のケースのうち、
  現在クラスと期待クラスが隣接しているものだけを「境界ケース」として
  修正スキップする。2段階以上ずれている粗い誤割当ては修正対象に残す。
"""

import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime


def filesystem_path(path):
    """Return a Windows extended-length path for long corpus filenames."""
    if os.name != "nt":
        return path
    absolute = os.path.abspath(path)
    if absolute.startswith("\\\\?\\"):
        return absolute
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute

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
CSS_CLASS_ORDER = [cls for _, cls in THRESHOLDS] + ["XXL_L"]
CSS_CLASS_INDEX = {cls: i for i, cls in enumerate(CSS_CLASS_ORDER)}


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


def css_class_distance(actual_css, expected_css):
    """CSSクラスの段差を返す。未知クラスは無限大扱い。"""
    actual_idx = CSS_CLASS_INDEX.get(actual_css)
    expected_idx = CSS_CLASS_INDEX.get(expected_css)
    if actual_idx is None or expected_idx is None:
        return float("inf")
    return abs(actual_idx - expected_idx)


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
RAW_RUBY_OPEN_RE = re.compile(r'<ruby\b', re.IGNORECASE)
RUBY_RE = re.compile(
    r'<ruby\b[^>]*>\s*(?P<rb>[^<]+?)\s*'
    r'<rt\b(?P<attrs>[^>]*)>(?P<rt>.*?)</rt\s*>\s*</ruby\s*>',
    re.IGNORECASE | re.DOTALL,
)
CLASS_ATTR_RE = re.compile(
    r'''(?<![\w:-])class\s*=\s*(?:
        "(?P<double>[^"]*)"
        |'(?P<single>[^']*)'
        |\u201c(?P<smart>[^\u201d]*)\u201d
    )''',
    re.IGNORECASE | re.VERBOSE,
)
BR_RE = re.compile(r'<br\s*/?\s*>', re.IGNORECASE)
RT_OPEN_RE = re.compile(r'<rt\b(?P<attrs>[^>]*)>', re.IGNORECASE)
RT_CLOSE_RE = re.compile(r'</rt\s*>', re.IGNORECASE)


def count_raw_ruby_opens(content):
    """Return the number of opening ``<ruby`` tags, independent of case."""
    return len(RAW_RUBY_OPEN_RE.findall(content))


def parse_rubies(content):
    """Parse supported ruby tags.

    Each result is ``(match, rb, css, rt_raw, rt_clean,
    needs_class_normalization)``.  ASCII single and double quotes are valid;
    U+201C/U+201D smart quotes are accepted so ``--fix`` can normalize the
    invalid HTML attribute quoting.
    """
    results = []
    for m in RUBY_RE.finditer(content):
        class_match = CLASS_ATTR_RE.search(m.group("attrs"))
        if class_match is None:
            # Keep this out of the parsed count so the raw/parsed gap exposes
            # unsupported or malformed ruby markup.
            continue

        quote_kind = class_match.lastgroup
        css = class_match.group(quote_kind)
        rb = m.group("rb").strip()
        rt_raw = m.group("rt").strip()
        rt_clean = BR_RE.sub('', rt_raw)
        if '<' in rt_clean or '>' in rt_clean:
            # Only plain annotation text plus <br>/<BR/> is supported.  Other
            # nested markup must be reviewed rather than silently measured.
            continue
        results.append((m, rb, css, rt_raw, rt_clean, quote_kind == "smart"))
    return results


def rebuild_fixed_ruby(match, expected_css, correct_rt):
    """Rebuild only the rt class/content while preserving all other markup.

    In particular, attributes on ``ruby`` and non-class attributes on ``rt``
    must survive ``--fix``.  Reconstructing a minimal tag would silently drop
    data-*, lang, ARIA, or other future metadata.
    """
    original = match.group(0)
    rt_open = RT_OPEN_RE.search(original)
    if rt_open is None:
        raise ValueError("parsed ruby unexpectedly lacks an rt opening tag")
    attrs = rt_open.group("attrs")
    class_match = CLASS_ATTR_RE.search(attrs)
    if class_match is None:
        raise ValueError("parsed ruby unexpectedly lacks a supported class attribute")
    fixed_attrs = (
        attrs[:class_match.start()]
        + f'class="{expected_css}"'
        + attrs[class_match.end():]
    )
    fixed_open = "<rt" + fixed_attrs + ">"
    rt_close = RT_CLOSE_RE.search(original, rt_open.end())
    if rt_close is None:
        raise ValueError("parsed ruby unexpectedly lacks an rt closing tag")
    return (
        original[:rt_open.start()]
        + fixed_open
        + correct_rt
        + original[rt_close.start():]
    )


# ─────────────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────────────
def verify_file(filepath, fix=False, verbose=False, margin=0.0, boundary_only=False):
    width_data = _load_width_data()

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    raw_total = count_raw_ruby_opens(content)
    rubies = parse_rubies(content)
    total = len(rubies)
    unparsed = raw_total - total
    all_mismatches = []
    fixable = []
    skipped_boundary = []

    for m, rb, actual_css, rt_raw, rt_clean, needs_normalization in rubies:
        expected_css, ratio = calc_css_class(rb, rt_clean, width_data)
        expected_rt = build_correct_rt(rt_clean, expected_css, width_data)
        actual_class_rt = build_correct_rt(
            rt_clean, actual_css, width_data
        )
        class_mismatch = actual_css != expected_css
        # Break placement belongs to the class currently carried by the tag.
        # Even when --margin retains an adjacent boundary class, that retained
        # class must still have its own exact half/third-width break.
        break_mismatch = rt_raw != actual_class_rt
        break_only_mismatch = not class_mismatch and break_mismatch
        if class_mismatch or needs_normalization or break_mismatch:
            dist = nearest_threshold_distance(ratio)
            gap = css_class_distance(actual_css, expected_css)
            boundary_class = (
                class_mismatch
                and not needs_normalization
                and margin > 0
                and dist < margin
                and gap <= 1
            )
            entry = {
                "match": m,
                "rb": rb,
                "rt_clean": rt_clean,
                "rt_raw": rt_raw,
                "actual_css": actual_css,
                "expected_css": expected_css,
                "expected_rt": expected_rt,
                "actual_class_rt": actual_class_rt,
                "ratio": ratio,
                "threshold_dist": dist,
                "class_gap": gap,
                "needs_normalization": needs_normalization,
                "class_mismatch": class_mismatch,
                "break_mismatch": break_mismatch,
                "break_only_mismatch": break_only_mismatch,
                "boundary_class": boundary_class,
                # Default repair target.  A retained boundary class overrides
                # these below so only its break is normalized.
                "fix_css": expected_css,
                "fix_rt": expected_rt,
            }
            all_mismatches.append(entry)
            if boundary_class:
                skipped_boundary.append(entry)
                if break_mismatch:
                    entry["fix_css"] = actual_css
                    entry["fix_rt"] = actual_class_rt
                    fixable.append(entry)
            # Smart quotes are invalid HTML attribute delimiters.  Preserve
            # the established behavior: normalization is fixable even at a
            # width-ratio boundary and uses the computed class.
            elif needs_normalization:
                fixable.append(entry)
            else:
                fixable.append(entry)

    # ─── レポート出力 ───
    fname = os.path.basename(filepath)
    mismatch_ratio = (len(all_mismatches) / total * 100) if total else 0.0
    print(f"\n{'='*70}")
    print(f"  {fname}")
    print(f"  Raw ruby opens: {raw_total}   Parsed ruby: {total}   Unparsed: {unparsed}")
    print(f"  Total ruby: {total}   Mismatched: {len(all_mismatches)} ({mismatch_ratio:.1f}%)")
    print(
        "  Categories: "
        f"class={sum(e['class_mismatch'] for e in all_mismatches)}  "
        f"break={sum(e['break_mismatch'] for e in all_mismatches)}  "
        f"break-only={sum(e['break_only_mismatch'] for e in all_mismatches)}  "
        f"smart-quote={sum(e['needs_normalization'] for e in all_mismatches)}"
    )
    if unparsed:
        print(f"  WARNING: {unparsed} ruby tag(s) could not be parsed; review their markup.")
    if margin > 0:
        print(f"  Margin: {margin}  Fixable: {len(fixable)}  Boundary(skip): {len(skipped_boundary)}")
    print(f"{'='*70}")

    if total == 0:
        print("  No parseable ruby tags found.")
        return unparsed

    if not all_mismatches:
        print("  No CSS/rt-break mismatches found.")
        return unparsed

    # 表示対象を選択
    if boundary_only:
        display_list = skipped_boundary if margin > 0 else [
            e for e in all_mismatches
            if (
                e["class_mismatch"]
                and not e["needs_normalization"]
                and e["threshold_dist"] < 0.05
            )
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

    if not boundary_only:
        break_counts = Counter(
            (
                mm["rb"], mm["rt_raw"], mm["actual_class_rt"],
                mm["actual_css"],
            )
            for mm in display_list
            if mm["break_mismatch"]
        )
        if break_counts:
            print(
                f"\n  Break-placement mismatches: "
                f"{sum(break_counts.values())} instances, "
                f"{len(break_counts)} unique pairs"
            )
            for (rb, actual_rt, correct_rt, css), cnt in break_counts.most_common(limit):
                print(
                    f"    {cnt:5d}  {rb!r} [{css}]  "
                    f"{actual_rt!r} -> {correct_rt!r}"
                )
            if len(break_counts) > limit:
                print(
                    f"    ... and {len(break_counts) - limit} more "
                    "(use --verbose)"
                )

    # ─── 修正実行 ───
    if fix and fixable:
        print(
            f"\n  Applying {len(fixable)} fixes "
            f"(retaining {len(skipped_boundary)} boundary class decisions)..."
        )

        # バックアップ作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath + f".bak_{timestamp}"
        shutil.copy2(filesystem_path(filepath), filesystem_path(backup_path))
        print(f"  Backup: {backup_path}")

        # 後ろから置換（位置がずれないように）
        new_content = content
        for mm in sorted(fixable, key=lambda x: x["match"].start(), reverse=True):
            m = mm["match"]
            new_tag = rebuild_fixed_ruby(
                m, mm["fix_css"], mm["fix_rt"]
            )
            start, end = m.start(), m.end()
            new_content = new_content[:start] + new_tag + new_content[end:]

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        # 修正後の再検証
        with open(filepath, "r", encoding="utf-8") as f:
            verify_content = f.read()
        post_raw_total = count_raw_ruby_opens(verify_content)
        post_rubies = parse_rubies(verify_content)
        post_unparsed = post_raw_total - len(post_rubies)
        post_all = 0
        post_within_margin = 0
        post_break = 0
        post_break_only = 0
        for pm, rb, actual_css, rt_raw, rt_clean, needs_normalization in post_rubies:
            expected_css, ratio = calc_css_class(rb, rt_clean, width_data)
            class_mismatch = actual_css != expected_css
            actual_class_rt = build_correct_rt(
                rt_clean, actual_css, width_data
            )
            break_mismatch = rt_raw != actual_class_rt
            break_only_mismatch = not class_mismatch and break_mismatch
            if class_mismatch or needs_normalization or break_mismatch:
                post_all += 1
                if break_mismatch:
                    post_break += 1
                if break_only_mismatch:
                    post_break_only += 1
                dist = nearest_threshold_distance(ratio)
                gap = css_class_distance(actual_css, expected_css)
                if (
                    margin > 0
                    and dist < margin
                    and gap <= 1
                    and not needs_normalization
                    and not break_mismatch
                ):
                    post_within_margin += 1

        post_real = post_all - post_within_margin
        print(
            f"  Post-fix ruby coverage: {len(post_rubies)}/{post_raw_total} parsed "
            f"({post_unparsed} unparsed)"
        )
        print(
            f"  Post-fix: {post_all} total mismatches "
            f"({post_within_margin} boundary, {post_break} break, "
            f"{post_break_only} break-only, "
            f"{post_real} real)"
        )
        if post_real == 0 and post_unparsed == 0:
            print("  ALL NON-BOUNDARY CSS CLASSES AND RT BREAKS NOW CORRECT!")
        elif post_unparsed:
            print(f"  WARNING: {post_unparsed} ruby tag(s) remain unparsed after fixing.")
        print(f"  Fixed: {filepath}")
    elif fix and not fixable:
        if skipped_boundary:
            print(f"\n  All {len(skipped_boundary)} mismatches are boundary cases (within margin {margin}). Nothing to fix.")
        else:
            print("\n  No mismatches to fix.")

    # A raw/parsed gap is a structural verification failure, not merely a
    # warning.  It must contribute to both the per-file and CLI exit status.
    return len(all_mismatches) + unparsed


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
    return 1 if total_mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
