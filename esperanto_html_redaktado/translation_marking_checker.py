#!/usr/bin/env python3
"""日本語訳の有無と表記の整合を検査する。

検査項目
  A. <title> の表記が実際の本文と合っているか
       和訳あり → title に「日本語訳」等の語がある
       和訳なし → title に「日本語訳なし」等の語がある
  B. 一覧ページ(index.html)のバッジが実際の本文と合っているか
  C. 「3文以上の塊」(原文が1つの表示行にまとまっていて読みにくいもの)が残っていないか
       ただし1文が短いもの(平均50字未満)は対象外。
       例:「Paŝoj. Oni paŝas sur la strato.（足音。通りを誰かが歩いている。）」

使い方
    python3 esperanto_html_redaktado/translation_marking_checker.py [--require-zero]

--require-zero を付けると、違反が1件でもあれば終了コード1で終わる(CI用)。
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

RT_RE = re.compile(r'<rt\b[^>]*>.*?</rt>', re.I | re.S)
RUBY_RE = re.compile(r'<ruby[^>]*>.*?</ruby>', re.I | re.S)
BR_RE = re.compile(r'<br\s*/?>', re.I)
TAG_RE = re.compile(r'<[^>]+>')
KANA = re.compile(r'[ぁ-んァ-ヶ]')
HANGUL = re.compile(r'[가-힣]')

MARK_NO = re.compile(r'日本語訳なし|和訳なし|ルビのみ')
MARK_YES = re.compile(r'日本語訳|和訳|japanaj?\s+traduk|kun\s+japana|対訳|全訳|日本語注釈')


def title_says(title):
    """titleが主張している状態を返す: 'no' / 'yes' / None

    「日本語訳なし」は「日本語訳」を含むため、必ず MARK_NO を先に判定する。
    逆順にすると、訳ありの文書に誤って「訳なし」と書いても検出できない。
    """
    if MARK_NO.search(title):
        return 'no'
    if MARK_YES.search(title):
        return 'yes'
    return None

ABBREV = re.compile(r'''(?xi)
      \.\.\. | … | \d\s*[.,]\s*\d
    | \b(?:t|a|p|n|k|i)\s*\.\s*[a-zĉĝĥĵŝŭ]\s*\.
    | \bk\s*\.\s*t\s*\.\s*p\s*\.
    | \b(?:ekz|prof|d-ro|s-ro|s-ino|f-ino|resp|vd|ktp|p|n-ro|nro|sam|k-do)\s*\.
''')
INITIAL = re.compile(r'(?:^|[\s(\[*"“』」>])[A-ZĈĜĤĴŜŬ]\s*\.')
LISTNUM = re.compile(r'(?:^|[\s*>])\d{1,2}\s*\.\s')

# 「3文以上 かつ (1文が長い または ブロック全体が長い)」を塊とみなす。
#  ・1文が長いものは3文でも追いにくい。
#  ・1文が短くてもブロック全体が長いと、原文の塊と訳の塊を突き合わせるのが難しい
#    (例: 24文759字の「Paŝoj. Oni paŝas sur la strato. …」)。
#  ・3〜5文で全体も短い短文の連続は、分割しても細切れになるだけなので対象外。
MIN_SENT = 3
MIN_AVG_LEN = 50
MIN_TOTAL_LEN = 250


def segments(body):
    masked = RT_RE.sub(lambda m: '\x00' * len(m.group(0)), body)
    out, pos = [], 0
    for m in BR_RE.finditer(masked):
        out.append(body[pos:m.start()])
        pos = m.end()
    out.append(body[pos:])
    return out


def text_of(seg):
    return re.sub(r'\s+', ' ', TAG_RE.sub('', RT_RE.sub('', seg))).strip()


def kind_of(seg):
    t = text_of(seg)
    if len(t) < 25 or t.startswith(('#', '=', '**Audio', '**URL', '**Categ', '**Publ', 'Hejmo')):
        return None
    n = len(t)
    if len(HANGUL.findall(t)) > n * 0.15:
        return 'KO'
    if len(KANA.findall(t)) > n * 0.15:
        return 'JA'
    return 'EO' if '<ruby' in seg.lower() else None


CLOSERS = '"”»)’\'』」）'
HAS_WORD = re.compile(r'[0-9A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ぀-ヿ一-鿿가-힣]')
# 写真キャプション末尾の頁参照。例: (p.19) （p.8-9） (p. 21)
PAGEREF = re.compile(r'[(（]\s*[a-zA-Z]?\s*\.?\s*\d+(?:\s*[-–]\s*\d+)?\s*[)）]')


def _rendered(s):
    """表示される平文と、各文字の (元位置, ruby内か) を返す。

    略語(Prof. / L. Couturat)は語幹がruby内・ピリオドがruby外に分かれることがあるため、
    判定は ruby の base を含む平文で行い、切断は ruby 外の位置に限る。
    """
    txt, idx, inruby, pos = [], [], [], 0
    for m in RUBY_RE.finditer(s):
        seg = TAG_RE.sub(lambda t: '\x01' * len(t.group(0)), s[pos:m.start()])
        for k, ch in enumerate(seg):
            if ch != '\x01':
                txt.append(ch); idx.append(pos + k); inruby.append(False)
        base = TAG_RE.sub(lambda t: '\x01' * len(t.group(0)), RT_RE.sub('', m.group(0)))
        for k, ch in enumerate(base):
            if ch != '\x01':
                txt.append(ch); idx.append(m.start() + k); inruby.append(True)
        pos = m.end()
    tail = TAG_RE.sub(lambda t: '\x01' * len(t.group(0)), s[pos:])
    for k, ch in enumerate(tail):
        if ch != '\x01':
            txt.append(ch); idx.append(pos + k); inruby.append(False)
    return ''.join(txt), idx, inruby


def eo_sentences(seg):
    """エスペラント本文の文を返す。分割適用側と同じ判定を用いる。"""
    txt, idx, inr = _rendered(seg)
    prot = [(m.start(), m.end()) for m in ABBREV.finditer(txt)]
    prot += [(m.start(), m.end()) for m in INITIAL.finditer(txt)]
    prot += [(m.start(), m.end()) for m in LISTNUM.finditer(txt)]
    cuts, depth, i = [], 0, 0
    while i < len(txt):
        ch = txt[i]
        if ch in '(（':
            depth += 1
        elif ch in ')）':
            depth = max(0, depth - 1)
        elif (ch in '.!?' and depth == 0 and not inr[i]
              and not any(a <= i < b for a, b in prot)):
            j = i + 1
            while j < len(txt) and txt[j] in '.!?':
                j += 1
            while j < len(txt) and txt[j] in CLOSERS:
                j += 1
            if j >= len(txt):
                break
            if not inr[j] and txt[j] in ' \t\n':
                last = j
                j += 1
                while (j < len(txt) and txt[j] in ' \t\n'
                       and idx[j] == idx[j - 1] + 1):
                    last = j
                    j += 1
                if j < len(txt):
                    cuts.append(last + 1)
                i = j
                continue
        i += 1
    parts, prev = [], 0
    for c in cuts:
        parts.append(txt[prev:c]); prev = c
    parts.append(txt[prev:])
    # タグ間の改行・字下げは表示されないので、長さを測る前に畳む
    parts = [re.sub(r'\s+', ' ', p).strip() for p in parts if p.strip()]
    # 文字を含まない断片(閉じ引用符だけ 等)は独立した「文」と数えない。
    # 例: '… bushaltejo. "' はピリオドと閉じ引用符の間に空白があるため、
    #     素朴に切ると '"' だけが1文と数えられてしまう。
    #     分割を適用する側と同じ規則にしないと、検査だけが違反を報告する。
    merged = []
    for p in parts:
        if merged and not HAS_WORD.search(p):
            merged[-1] += p
        else:
            merged.append(p)
    # 末尾の頁参照 '(p.19)' も1文と数えない。
    # 写真キャプションは原文・訳文とも末尾に同じ頁参照を持つため、
    # 切り出すと「(p.19)」だけの行が2行続けて表示されてしまう。
    # 分割を適用する側と同じ規則にしないと、検査だけが違反を報告する。
    if len(merged) >= 2 and PAGEREF.fullmatch(merged[-1].strip()):
        last = merged.pop()
        merged[-1] += last
    return merged


def _inr_helper(inr):
    return lambda p: inr[p]


def analyze(path):
    """(状態, 塊のリスト, html) を返す。対象外なら None。

    状態: 'yes' ルビ+和訳 / 'no' ルビのみ / 'ko' 韓国語訳版
          'plain' ルビ無しだが和訳あり（Gerda txt元版・対訳版など）
    判定は必ず本文の実データで行う。title を信用してはならない。
    """
    if path.name.lower().startswith('index'):
        return None
    html = path.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'<body\b[^>]*>(.*)</body>', html, re.I | re.S)
    if not m:
        return None
    body = re.sub(r'<style\b.*?</style>', '', m.group(1), flags=re.I | re.S)

    if len(re.findall(r'<ruby\b', html, re.I)) < 50:
        # ルビ注釈の無い原文版。日本語が十分あれば「和訳あり（ルビなし）」
        txt = TAG_RE.sub('', body)
        nk, nh = len(KANA.findall(txt)), len(HANGUL.findall(txt))
        if nh > 50 and nh > nk:
            return 'ko', [], html
        return ('plain', [], html) if nk > 50 else None

    segs = segments(body)
    kinds = [kind_of(s) for s in segs]
    ja = sum(1 for k in kinds if k == 'JA')
    ko = sum(1 for k in kinds if k == 'KO')
    clumps = []
    for i, (k, s) in enumerate(zip(kinds, segs)):
        if k != 'EO':
            continue
        if i + 1 >= len(kinds) or kinds[i + 1] not in ('JA', 'KO'):
            continue
        sents = eo_sentences(s)
        if len(sents) < MIN_SENT:
            continue
        # 段落全体が ** … ** や * … * で囲まれているブロックは分割対象外。
        # このコーパスでは ** / * は <strong>/<em> に変換されずリテラル文字として
        # 表示されるため、文で割ると開始の印と終了の印が別の表示行に分かれ、
        # 間の行には印が無いという崩れた見た目になる。
        # ただし行頭の箇条書き「* 」や脚注番号「*³」は元から1個で完結しているので、
        # 「ブロック全体では対なのに割ると片方だけになる」場合に限って対象外とする。
        whole = text_of(s)
        if any(f(whole) % 2 == 0 and any(f(x) % 2 for x in sents)
               for f in (lambda t: t.count('**'),
                         lambda t: t.replace('**', '').count('*'))):
            continue
        total = sum(len(x) for x in sents)
        avg = total // len(sents)
        if avg < MIN_AVG_LEN and total < MIN_TOTAL_LEN:
            continue
        clumps.append((len(sents), avg, text_of(s)[:60]))
    st = 'ko' if ko > ja else ('yes' if ja else 'no')
    return st, clumps, html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--require-zero', action='store_true')
    args = ap.parse_args()

    bad_title, bad_badge, bad_clump = [], [], []
    state = {}

    for f in sorted(ROOT.rglob('*.html')):
        r = analyze(f)
        if r is None:
            continue
        st, clumps, html = r
        rel = f.relative_to(ROOT)
        state[f.resolve()] = st

        t = re.search(r'<title>(.*?)</title>', html, re.S)
        title = t.group(1).strip() if t else ''
        says = title_says(title)
        want = {'yes': 'yes', 'plain': 'yes', 'no': 'no', 'ko': None}[st]
        if want is None:
            # 韓国語訳版には和訳有無の定型表記が無いので want を決められない。
            # ただし「日本語訳付き」「日本語訳なし」等が付いていたら読者を誤らせるので弾く。
            # (want=None を素通りさせていた旧版は、KO版のtitleを一切検査していなかった)
            if says is not None:
                bad_title.append((rel, f'韓国語訳版なのに title が和訳有無({says})を主張', title))
        elif says != want:
            bad_title.append((rel, f'実際は{st}だが title の表記は{says or "無し"}', title))
        for ns, avg, head in clumps:
            bad_clump.append((rel, ns, avg, head))

    # <li> と <a> の隣接を前提にせず、複数行にまたがる項目も拾う。
    # (re.S 無し・隣接必須の旧版は96件を取りこぼし、Bを常に0件と誤報していた)
    li_re = re.compile(r'<li\b[^>]*>\s*<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</li>',
                       re.S | re.I)
    # 一覧ページは index.html だけではない。index_txt.html / index_txt_files.html も
    # link-list を持つ一覧なので、index.html 限定にすると無検査領域ができる。
    for idx in sorted(ROOT.rglob('index*.html')):
        html = idx.read_text(encoding='utf-8', errors='replace')
        if 'link-list' not in html:
            continue
        for m in li_re.finditer(html):
            target = (idx.parent / m.group(1)).resolve()
            st = state.get(target)
            if st is None:
                continue
            want = {'yes': 'tr-yes', 'no': 'tr-no',
                    'ko': 'tr-ko', 'plain': 'tr-plain'}[st]
            if want not in m.group(2):
                bad_badge.append((idx.relative_to(ROOT), m.group(1), st))

    # D. バッジのCSSが実際に届いているか
    # 付与したclassがどのCSSにも定義されていないと、バッジは無装飾の素のテキストとして
    # 表示される。HTMLだけ見ても気づけないので、リンク先のCSSまで辿って確認する。
    bad_css = []
    for idx in sorted(ROOT.rglob('index*.html')):
        html = idx.read_text(encoding='utf-8', errors='replace')
        used = set(re.findall(r'class="([^"]*\btr-[\w-]+[^"]*)"', html))
        if not used:
            continue
        names = {c for u in used for c in u.split() if c.startswith('tr-')}
        css = '\n'.join(re.findall(r'<style\b[^>]*>(.*?)</style>', html, re.S | re.I))
        for href in re.findall(r'<link[^>]+href="([^"]+\.css)"', html):
            p = (idx.parent / href).resolve()
            if p.exists():
                css += p.read_text(encoding='utf-8', errors='replace')
        # ★ 素の部分文字列検索 (f'.{n}' not in css) にしてはならない。
        #   CSSの説明コメントに「.tr-yes ルビ注釈＋和訳」のようにクラス名を書くと、
        #   実際の色定義を全部消してもコメントだけで検査が通ってしまう
        #   (この検査を追加した 880bb28 のコメントが、まさに検査自身を無効化していた)。
        #   コメントを除去したうえで、クラス名の後に { か , が続くことまで確認する。
        css = re.sub(r'/\*.*?\*/', ' ', css, flags=re.S)
        missing = sorted(n for n in names
                         if not re.search(r'\.' + re.escape(n) + r'\s*[,{]', css))
        if missing:
            bad_css.append((idx.relative_to(ROOT), missing))

    print(f"検査対象: 本文HTML {len(state)} 件")
    print(f"  ルビ+和訳 {sum(1 for v in state.values() if v == 'yes')} / "
          f"ルビのみ {sum(1 for v in state.values() if v == 'no')} / "
          f"韓国語版 {sum(1 for v in state.values() if v == 'ko')} / "
          f"ルビ無し+和訳 {sum(1 for v in state.values() if v == 'plain')}")
    print()
    print(f"A. title の表記ずれ : {len(bad_title)} 件")
    for rel, why, title in bad_title[:20]:
        print(f"     {why}: {rel}\n        title: {title[:70]}")
    print(f"B. 一覧バッジのずれ : {len(bad_badge)} 件")
    for rel, href, st in bad_badge[:20]:
        print(f"     {rel} → {href} (実際は {st})")
    print(f"C. 3文以上の塊     : {len(bad_clump)} 件")
    for rel, ns, avg, head in bad_clump[:20]:
        print(f"     {rel}  {ns}文/平均{avg}字  {head}")
    print(f"D. バッジCSSの欠落 : {len(bad_css)} 件")
    for rel, miss in bad_css[:20]:
        print(f"     {rel}: {', '.join(miss)} がどのCSSにも無い")

    total = len(bad_title) + len(bad_badge) + len(bad_clump) + len(bad_css)
    print()
    print(f"違反合計: {total} 件")
    if args.require_zero and total:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
