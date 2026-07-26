"""
esp_text_replacement_module.py

このモジュールは「エスペラント文章の文字列(漢字)置換」を包括的に扱うツール集です。
主な機能：
1. エスペラント独自の文字形式（ĉ, ĝなど）への変換 → convert_to_circumflex
2. 特殊な半角スペースの統一（ASCIIスペースに） → unify_halfwidth_spaces
3. ✕不要に　HTMLルビ（<ruby>タグ）付与 → wrap_text_with_ruby (HTML形式のブラッシュアップにより必要なくなった。202502)
4. %や@で囲まれたテキストのスキップ・局所変換 → (create_replacements_list_for_...)
5. 大域的なプレースホルダー置換 → safe_replace
6. それらをまとめて実行する複合置換関数 → orchestrate_comprehensive_esperanto_text_replacement
7. multiprocessing を用いた行単位の並列実行 → parallel_process / process_segment
"""
# Pythonファイル単独でモジュールとして扱う想定。トップレベルに各関数を定義しておく。

import re
import json
from typing import List, Tuple, Dict
import multiprocessing

# ================================
# 1) エスペラント文字変換用の辞書
# ================================
# 字上符付き文字の表記形式変換用の辞書型配列
x_to_circumflex = {'cx': 'ĉ', 'gx': 'ĝ', 'hx': 'ĥ', 'jx': 'ĵ', 'sx': 'ŝ', 'ux': 'ŭ','Cx': 'Ĉ', 'Gx': 'Ĝ', 'Hx': 'Ĥ', 'Jx': 'Ĵ', 'Sx': 'Ŝ', 'Ux': 'Ŭ'}
circumflex_to_x = {'ĉ': 'cx', 'ĝ': 'gx', 'ĥ': 'hx', 'ĵ': 'jx', 'ŝ': 'sx', 'ŭ': 'ux','Ĉ': 'Cx', 'Ĝ': 'Gx', 'Ĥ': 'Hx', 'Ĵ': 'Jx', 'Ŝ': 'Sx', 'Ŭ': 'Ux'}
x_to_hat = {'cx': 'c^', 'gx': 'g^', 'hx': 'h^', 'jx': 'j^', 'sx': 's^', 'ux': 'u^','Cx': 'C^', 'Gx': 'G^', 'Hx': 'H^', 'Jx': 'J^', 'Sx': 'S^', 'Ux': 'U^'}
hat_to_x = {'c^': 'cx', 'g^': 'gx', 'h^': 'hx', 'j^': 'jx', 's^': 'sx', 'u^': 'ux','C^': 'Cx', 'G^': 'Gx', 'H^': 'Hx', 'J^': 'Jx', 'S^': 'Sx', 'U^': 'Ux'}
hat_to_circumflex = {'c^': 'ĉ', 'g^': 'ĝ', 'h^': 'ĥ', 'j^': 'ĵ', 's^': 'ŝ', 'u^': 'ŭ','C^': 'Ĉ', 'G^': 'Ĝ', 'H^': 'Ĥ', 'J^': 'Ĵ', 'S^': 'Ŝ', 'U^': 'Ŭ'}
circumflex_to_hat = {'ĉ': 'c^', 'ĝ': 'g^', 'ĥ': 'h^', 'ĵ': 'j^', 'ŝ': 's^', 'ŭ': 'u^','Ĉ': 'C^', 'Ĝ': 'G^', 'Ĥ': 'H^', 'Ĵ': 'J^', 'Ŝ': 'S^', 'Ŭ': 'U^'}

# ================================
# 2) 基本の文字形式変換関数
# ================================

# 字上符付き文字の表記形式変換用の関数
def replace_esperanto_chars(text, char_dict: Dict[str, str]) -> str:
    for original_char, converted_char in char_dict.items():
        text = text.replace(original_char, converted_char)
    return text

def convert_to_circumflex(text: str) -> str:
    """テキストを字上符形式（ĉ, ĝ, ĥ, ĵ, ŝ, ŭなど）に統一します。"""
    text = replace_esperanto_chars(text, hat_to_circumflex)# 2. ^表記 (c^, g^...) → ĉ, ĝ... に変換
    text = replace_esperanto_chars(text, x_to_circumflex)# 3. x表記 (cx, gx...) → ĉ, ĝ... に変換
    return text

def unify_halfwidth_spaces(text: str) -> str:
    """全角スペース(U+3000)は変更せず、半角スペースと視覚的に区別がつきにくい空白文字を
        ASCII半角スペース(U+0020)に統一する。連続した空白は1文字ずつ置換する。"""
    pattern = r"[\u00A0\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A]"# 対象とする空白文字をまとめたパターン
    return re.sub(pattern, " ", text)# マッチした部分を標準的な半角スペースに置換

# ================================
# 3) HTMLルビタグの補助関数
# ================================
# ブラウザで表示した際の文字の高さを揃えるために、HTML形式の都合上、rubyタグがかかっていないメインテキストについても、<ruby>〜</ruby>で囲む必要が生じた。
# BeautifulSoup4を使用して実装することにした。streamlit cloud でもrequirements.txtに書き込んで、インストールすれば使用できることを確認。
# HTML形式のブラッシュアップにより必要なくなった。(202502)


# ================================
# 4) 占位符(placeholder)関連
# ================================

# 置換に用いる関数。正規表現、C++など様々な形式の置換を試したが、pythonでplaceholder(占位符)を用いる形式の置換が、最も処理が高速であった。(しかも大変シンプルでわかりやすい。)
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:# Tupleは狭義のList
    """(old, new, placeholder) のタプルを含むリストを受け取り、
        text中の old → placeholder → new の段階置換を行う。 """
    valid_replacements = {}
    # 置換対象(old)をplaceholderに一時的に置換
    for old, new, placeholder in replacements:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new# 後で置換後の文字列(new)に置換し直す必要があるplaceholderを辞書(valid_replacements)に記録しておく。
    # placeholderを置換後の文字列(new)に置換)
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    return text
def import_placeholders(filename: str) -> List[str]:# placeholder(占位符)をインポートするためだけの関数
    with open(filename, 'r') as file:
        placeholders = [line.strip() for line in file if line.strip()]
    return placeholders

# '%'で囲まれた50文字以内の部分を同定し、文字列(漢字)置換せずにそのまま保存しておくための関数群
# 関数外（モジュールのグローバルスコープ）でコンパイル
PERCENT_PATTERN = re.compile(r'(?<![0-9])%(.{1,50}?)%')  # 50% 等、数字直後の%は開きマーカーにしない
def find_percent_enclosed_strings_for_skipping_replacement(text: str) -> List[str]:
    """'%foo%' の形を全て抽出。50文字以内。"""
    matches = []
    used_indices = set()

    # 正規表現のマッチを見つける
    for match in PERCENT_PATTERN.finditer(text):
        start, end = match.span()
        # 重複する%を避けるためにインデックスをチェック
        if start not in used_indices and end-2 not in used_indices:  # end-2 because of double %
            matches.append(match.group(1))
            # インデックスを使用済みセットに追加
            used_indices.update(range(start, end))
    return matches

def create_replacements_list_for_intact_parts(text: str, placeholders: List[str]) -> List[Tuple[str, str]]:
    # テキストから%で囲まれた部分を抽出
    matches = find_percent_enclosed_strings_for_skipping_replacement(text)
    replacements_list_for_intact_parts = []
    # プレースホルダーとマッチを対応させる
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replacements_list_for_intact_parts.append([f"%{match}%", placeholders[i]])
        else:
            break  # プレースホルダーが足りなくなった場合は終了
    return replacements_list_for_intact_parts

# '@'で囲まれた18文字(PEJVOに収録されている最長語根の文字数)以内の部分を同定し、局所的な文字列(漢字)置換を実行するための関数群
# 関数外（モジュールのグローバルスコープ）でコンパイル
AT_PATTERN = re.compile(r'(?<![A-Za-z0-9])@(.{1,18}?)@(?![A-Za-z0-9])')  # 英数字密着の@(メールアドレス等)はマーカー不成立

# @...@ intentionally has its own, often broader, gloss semantics (for
# example @kaj@ means "と;そして" while the global word means "と").  Exact
# global reuse is therefore limited to this reviewed boundary-correction set;
# see _analysis_20260625/localized_global_exact_reviewed.json.
_LOCALIZED_GLOBAL_EXACT_ROOTS = (
    'ddt', 'fortran', 'golfo', 'hiv', 'khz', 'mhz', 'pat!',
    'racionalism', 'racionalist', 'spiritism', 'spiritist',
    'hokkajdon',
)
_LOCALIZED_GLOBAL_EXACT_REVIEWED = frozenset(
    form
    for root in _LOCALIZED_GLOBAL_EXACT_ROOTS
    for form in (root, root.capitalize(), root.upper())
)

def find_at_enclosed_strings_for_localized_replacement(text: str) -> List[str]:
    """'@foo@' の形を全て抽出。18文字以内。"""
    matches = []
    used_indices = set()

    # 正規表現のマッチを見つける
    for match in AT_PATTERN.finditer(text):
        start, end = match.span()
        # 重複する@を避けるためにインデックスをチェック
        if start not in used_indices and end-2 not in used_indices:  # end-2 because of double @
            matches.append(match.group(1))
            # インデックスを使用済みセットに追加
            used_indices.update(range(start, end))
    return matches

def _finalized_global_renderings_for_exact_matches(
    matches: List[str],
    replacements_final_list: List[Tuple[str, str, str]],
) -> Dict[str, str]:
    """Return each matched word's already-finalized global rendering.

    The global rule order is the boundary authority (first match wins).  Only a
    rule whose Esperanto source, apart from structural ASCII edge spaces, is
    exactly the @...@ payload is eligible.  Reusing its finalized ``new`` core
    also preserves the language's own gloss and the class/<br> layout computed
    from the final ruby text; the local atom list remains a compatibility
    fallback when no exact global rule exists.
    """
    wanted = set(matches) & _LOCALIZED_GLOBAL_EXACT_REVIEWED
    finalized = {}
    if not wanted or not replacements_final_list:
        return finalized
    for rule in replacements_final_list:
        if not isinstance(rule, (list, tuple)) or len(rule) < 2:
            continue
        old, new = rule[0], rule[1]
        if not isinstance(old, str) or not isinstance(new, str):
            continue
        left = len(old) - len(old.lstrip(' '))
        right = len(old) - len(old.rstrip(' '))
        end = len(old) - right if right else len(old)
        core = old[left:end]
        if not core or core not in wanted or core in finalized:
            continue
        new_left = len(new) - len(new.lstrip(' '))
        new_right = len(new) - len(new.rstrip(' '))
        if (new_left, new_right) != (left, right):
            raise ValueError(
                f"global exact rule has mismatched structural spaces: {old!r}"
            )
        new_end = len(new) - new_right if new_right else len(new)
        finalized[core] = new[new_left:new_end]
        if len(finalized) == len(wanted):
            break
    unresolved = sorted(wanted - set(finalized))
    if unresolved:
        raise ValueError(
            f"reviewed @local target lacks an exact global rule: {unresolved!r}"
        )
    return finalized

def create_replacements_list_for_localized_replacement(text, placeholders: List[str],
                                                       replacements_list_for_localized_string: List[Tuple[str, str, str]],
                                                       replacements_final_list: List[Tuple[str, str, str]] = None)-> List[List[str]]:
    # テキストから@で囲まれた部分を抽出
    matches = find_at_enclosed_strings_for_localized_replacement(text)
    finalized_global = _finalized_global_renderings_for_exact_matches(
        matches, replacements_final_list or []
    )
    tmp_replacements_list_for_localized_string = []
    # プレースホルダーとマッチを対応させる
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replaced_match = finalized_global.get(match)
            if replaced_match is None:
                replaced_match=safe_replace(match, replacements_list_for_localized_string)# ここで、まず１つplaceholdersが要る。
            # print(match,replaced_match)
            tmp_replacements_list_for_localized_string.append([f"@{match}@", placeholders[i],replaced_match])# ここに、置換後の
        else:
            break  # プレースホルダーが足りなくなった場合は終了
    return tmp_replacements_list_for_localized_string


# ================================
# 5) メインの複合文字列(漢字)置換関数
# ================================

def orchestrate_comprehensive_esperanto_text_replacement(
    text,
    placeholders_for_skipping_replacements: List[str],
    replacements_list_for_localized_string: List[Tuple[str, str, str]] ,
    placeholders_for_localized_replacement: List[str] ,
    replacements_final_list: List[Tuple[str, str, str]] ,
    replacements_list_for_2char: List[Tuple[str, str, str]] ,
    format_type: str
    )-> str:
    """
    複数の変換ルールに従ってエスペラント文を文字列(漢字)置換するメイン関数。

    ステップ:
      1) unify_halfwidth_spaces(text)     : 特殊な空白を半角スペースへ
      2) convert_to_circumflex(text)      : ĉ, ĝ, ĥ, ĵ, ŝ, ŭ への統一
      3) %...% で囲まれた部分を置換スキップ (placeholders_for_skipping_replacements で保護)
      4) @...@ で囲まれた部分を局所置換 (replacements_list_for_localized_string)
      5) 大域置換 (replacements_final_list)
      6) 二文字語根の置換を2回実施 (replacements_list_for_2char)
      7) プレースホルダーの復元
      8) もし format_type に "HTML" が含まれるなら、空白' 'や改行'\n'について、HTML形式用に変換

    Args:
        text: 変換対象のエスペラント文
        placeholders_for_skipping_replacements:  %...% 用のプレースホルダー一覧
        replacements_list_for_localized_string:  @...@ 用の置換ルール (old, new, placeholder)
        placeholders_for_localized_replacement:  @...@ 用のプレースホルダー一覧
        replacements_final_list:                 大域置換用の (old, new, placeholder) のリスト
        replacements_list_for_2char:             2文字語根用の (old, new, placeholder) リスト
        format_type:  "HTML" が含まれているとHTMLルビ化などの処理を行う

    Returns:
        置換後のテキスト（HTML形式の場合もある）
    """

    # 1, 2) 半角スペースを標準化し、エスペラント文字表現を字上符形式に統一
    text = unify_halfwidth_spaces(text)# 半角スペースと視覚的に区別がつきにくい特殊な空白文字を標準的なASCII半角スペース(U+0020)に置換する。 ただし、全角スペース(U+3000)は置換対象に含めていない。
    text = convert_to_circumflex(text)# テキストを字上符形式（ĉ, ĝ, ĥ, ĵ, ŝ, ŭなど）に統一。
    # 2.4) 異常入力耐性: 番兵文字chr(1)が入力に混入していた場合は除去(単語融合の防止)
    text = text.replace(chr(1), '')
    # 2.45) 改行正規化: CRLF/CR を LF へ(CR は _KEEP に含まれず、行末2字語根の発火を阻害するため)
    text = text.replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10))
    # 2.46) HTML出力時は入力由来の < > & をエスケープ(入力中の <b 等が実タグ化しプレビュー崩壊を防ぐ。
    #       置換で挿入する <ruby> 等はこの後段で入るため無傷。純粋置換(format_typeにHTML非含)は素通し)
    if "HTML" in format_type:
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # 3) '%'で囲まれた置換禁止部分を保護(placeholderに置換)。※パディング前(保護窓50字の仕様維持)
    replacements_list_for_intact_parts = create_replacements_list_for_intact_parts(text, placeholders_for_skipping_replacements)
    sorted_replacements_list_for_intact_parts = sorted(replacements_list_for_intact_parts, key=lambda x: len(x[0]), reverse=True)
    for original, place_holder_ in sorted_replacements_list_for_intact_parts:
        text = text.replace(original, place_holder_)# いいのか→多分大丈夫。
    # 4) '@'で囲まれた箇所を局所的に置換・保存(placeholderに置換)。※パディング前(窓18字+raw照合)
    tmp_replacements_list_for_localized_string_2 = create_replacements_list_for_localized_replacement(
        text,
        placeholders_for_localized_replacement,
        replacements_list_for_localized_string,
        replacements_final_list,
    )
    sorted_replacements_list_for_localized_string = sorted(tmp_replacements_list_for_localized_string_2, key=lambda x: len(x[0]), reverse=True)
    for original, place_holder_, replaced_original in sorted_replacements_list_for_localized_string:
        text = text.replace(original, place_holder_)
    # 4.5) 約物パディング(v2): 約物の両側に番兵付き仮想スペースを挿入し、2字語根standalone
    # (' x 'パターン)が「両隣が非文字」の境界でも発火するようにする(出力前に除去・表示不変)。
    # ※%...%保護と@...@局所置換より後に実行する(保護窓50/18字の仕様維持と、約物入り
    #   局所規則をrawテキストで照合するため。プレースホルダ %1854%/@5134@ は % @ 数字が
    #   下記_KEEPに含まれるためパディングで壊れない)。
    # _KEEP(パディング除外)の設計根拠:
    #   英字26+字上符12=語の構成文字 / ラテン拡張(À-Ö,Ø-ö,ø-ɏ)=外国固有名詞(ę,ś,ü等)の内部を
    #   境界化しない(Międzygórze等の偽ルビ防止。CJK/かなは境界のまま=中kaj国は発火) /
    #   数字+%+@=プレースホルダ整合に必須(序数3anの無害性は実測済みだが整合上も除外) /
    #   ASCII/U+2019アポストロフィ=詩的語尾省略と定冠詞l'/l’に使うため
    #   基本温存(右側と閉じ引用は下で個別処理) / 空白改行番兵=構造上必須
    _BOL = chr(1)
    import re as _re
    _HAT12 = chr(264) + chr(265) + chr(284) + chr(285) + chr(292) + chr(293) + chr(308) + chr(309) + chr(348) + chr(349) + chr(364) + chr(365)
    _LATEXT = chr(192) + '-' + chr(214) + chr(216) + '-' + chr(246) + chr(248) + '-' + chr(591)
    _APOSTROPHES = chr(39) + chr(8217)
    _KEEP = 'A-Za-z0-9' + _HAT12 + _LATEXT + chr(37) + chr(64) + _APOSTROPHES + ' ' + chr(10) + chr(13) + chr(1)
    _PAD = _re.compile('([^' + _KEEP + '])')
    text = _PAD.sub(lambda _mo: ' ' + _BOL + _mo.group(1) + _BOL + ' ', text)
    # アポストロフィの右側限定パディング(直後が文字): dank'al / dank’al
    # のal・'Mi / ’Mi 引用開きが発火。記号自体は原表記のまま保つ。
    # 左側温存により省略形(l'/kor'/dank')とアポストロフィ入り辞書エントリは無傷。
    _LTR = 'A-Za-z' + _HAT12 + _LATEXT
    _APOS_R = _re.compile('[' + _APOSTROPHES + '](?=[' + _LTR + '])')
    text = _APOS_R.sub(lambda _mo: _mo.group(0) + _BOL + ' ', text)
    # 閉じ引用 mi' 型: o省略形になり得ない2字語根に限り左側もパディング(du/en/ve は duo/eno/veo の
    # 省略があり得るため対象外)。
    _APOS_L = _re.compile('(?<![' + _LTR + '])((?:[Mm]i|[Vv]i|[Nn]i|[Ll]i|[' + chr(348) + chr(349) + ']i|[' + chr(284) + chr(285) + ']i|[Aa]l|[Dd]e|[Ee]l|[' + chr(264) + chr(265) + ']e|[' + chr(264) + chr(265) + ']u|[Ss]e|[Kk]e|[Jj]e|[Dd]a|[Nn]e|[Hh]o|[Oo]k))([' + _APOSTROPHES + '])(?![' + _LTR + '])')
    text = _APOS_L.sub(lambda _mo: _mo.group(1) + ' ' + _BOL + _mo.group(2), text)
    # 行頭(文頭・改行直後)の2字語根対応: 各行頭/行末に番兵付き仮想スペースを挿入
    text = _BOL + ' ' + text.replace(chr(10), ' ' + _BOL + chr(10) + _BOL + ' ') + ' ' + _BOL
    # 5) メインとなる置換対象文字列をplaceholderへ置換
    valid_replacements = {}
    # 約物入り見出し(bandar-seri-begavano等3,500件超)は、テキスト側がパディング済みのため
    # 生キーでは一致しない。見出し側にも同じパディングを適用した照合キーを【初回のみ前計算】し
    # (リストは起動時ロードで使い回されるためid基準キャッシュ)、ループ内はO(1)辞書引きで
    # フォールバック照合する。置換の優先順序(リスト順)は完全維持。
    # 値キー(old文字列→パディング済みold)のモジュール級キャッシュ。パディングは文字列の
    # 純関数なのでstaleし得ず、サイズは約物入り見出しの異なり数(~3.5K+補正数)で有界。
    # 旧実装は id(リスト) キーだったが、st.cache_data がStreamlit再実行毎に新コピーを返し
    # merge_overlay も新リストを返すため、再実行毎に~3.3MBずつ無制限成長していた。
    _pgc = globals().setdefault('_PUNCT_GG_CACHE', {})
    _pmap = {}
    _sub = lambda _mo: ' ' + _BOL + _mo.group(1) + _BOL + ' '
    for _o, _n, _p in replacements_final_list:
        if (_PAD.search(_o) is not None or _APOS_R.search(_o) is not None
                or _APOS_L.search(_o) is not None):
            # Version the cache key because rule-key normalization now mirrors
            # all three text-side boundary transformations, not only _PAD.
            _cache_key = ('v4', _o)
            _v = _pgc.get(_cache_key)
            if _v is None:
                _v = _PAD.sub(_sub, _o)
                _v = _APOS_R.sub(lambda _mo: _mo.group(0) + _BOL + ' ', _v)
                _v = _APOS_L.sub(
                    lambda _mo: _mo.group(1) + ' ' + _BOL + _mo.group(2), _v
                )
                _pgc[_cache_key] = _v
            _pmap[_o] = _v
    def _remember_global_replacement(placeholder, new):
        # Boundary spaces are structural and may be consumed by a later
        # punctuation/component rule.  The $...$ core is globally unique, so
        # restore that stable token and leave any surviving outer spaces in
        # place instead of leaking an unrecoverable raw placeholder.
        core = placeholder.strip(' ')
        replacement = new.strip(' ')
        prior = valid_replacements.get(core)
        if prior is not None and prior != replacement:
            raise ValueError(f"conflicting global placeholder core: {core!r}")
        valid_replacements[core] = replacement

    for old, new, placeholder in replacements_final_list:
        if old in text:
            text = text.replace(old, placeholder)
            _remember_global_replacement(placeholder, new)
        else:
            _p_old = _pmap.get(old)
            if _p_old is not None and _p_old in text:
                text = text.replace(_p_old, placeholder)
                _remember_global_replacement(placeholder, new)
    # 6) 2文字語根の置換。Placeholderに隣接した2文字語根のみ置換する設計(202412)。
    #    旧実装は固定2周(2回)だったが、3つ以上連続する2文字接辞(例: san/ig/ej/et, lern/ej/et/ar)を
    #    取りこぼし、偽語根(jet=ジェット機, tar=風袋, jar=年 等)を生んでいた。
    #    → 「マッチしなくなるまで反復(fixpoint)」へ一般化。各ラウンドは "!" の数で一意化し、
    #      round0 は旧pass1・round1 は旧pass2 と完全に後方互換(2周以内の挙動は不変)。
    two_char_rounds = []
    _round = 0
    while _round < 12:  # 安全上限(通常2〜3ラウンドで収束)
        _d = {}
        _mk = "!" * _round  # round0="" (旧pass1と同一), round1="!" (旧pass2と同一), ...
        for old, new, placeholder in replacements_list_for_2char:
            if old in text:
                ph = _mk + placeholder + _mk
                text = text.replace(old, ph)
                _d[ph] = new
        if not _d:
            break
        two_char_rounds.append(_d)
        _round += 1

    # print(text)# ⇑ここまでがplaceholderによる置換作業。以降⇓は、placeholderを置換後の文字列に置き換える作業。

    # 7) ここからplaceholderを最終的な文字列に復元していく(後のラウンドから=挿入の逆順がポイント)
    for _d in reversed(two_char_rounds):
        for placeholder, new in reversed(_d.items()):
            text = text.replace(placeholder, new)
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    # 7) 局所置換箇所(@...@)・置換禁止箇所(%...%)も復元
    for original, place_holder_, replaced_original in sorted_replacements_list_for_localized_string:
        text = text.replace(place_holder_, replaced_original.replace("@",""))
    for original, place_holder_ in sorted_replacements_list_for_intact_parts:
        text = text.replace(place_holder_, original.replace("%",""))
    # 行頭番兵の除去(仮想スペースごと)
    text = text.replace(' ' + _BOL, '').replace(_BOL + ' ', '').replace(_BOL, '')
    # 8) 必要に応じてHTML用の整形を実施
    if "HTML" in format_type:
        text = text.replace("\n", "<br>\n")
        # text = wrap_text_with_ruby(text, chunk_size=10)
        text = re.sub(r"   ", "&nbsp;&nbsp;&nbsp;", text)  # 3つ以上の空白を変換
        text = re.sub(r"  ", "&nbsp;&nbsp;", text)  # 2つ以上の空白を変換

    return text

# ================================
# 6) multiprocessing 関連
# ================================
def process_segment(lines: List[str],

    placeholders_for_skipping_replacements: List[str] , replacements_list_for_localized_string: List[Tuple[str, str, str]] ,
    placeholders_for_localized_replacement: List[str] , replacements_final_list: List[Tuple[str, str, str]] ,
    replacements_list_for_2char: List[Tuple[str, str, str]] , format_type: str ) -> str:# orchestrate_comprehensive_esperanto_text_replacementの引数をそのまま持って来た。

    # 文字列のリストを結合してから置換処理を実行 linesには\nが含まれていない状態の文字列群が格納されている。
    segment = ''.join(lines)# 202502変更
    result = orchestrate_comprehensive_esperanto_text_replacement(
    segment, placeholders_for_skipping_replacements, replacements_list_for_localized_string,
    placeholders_for_localized_replacement, replacements_final_list, replacements_list_for_2char, format_type)# ここでメインの文字列(漢字)置換関数'orchestrate_comprehensive_esperanto_text_replacement'の実行!

    return result


def parallel_process(text: str, num_processes: int ,

    placeholders_for_skipping_replacements: List[str] , replacements_list_for_localized_string: List[Tuple[str, str, str]] ,
    placeholders_for_localized_replacement: List[str] , replacements_final_list: List[Tuple[str, str, str]] ,
    replacements_list_for_2char: List[Tuple[str, str, str]] , format_type: str ) -> str:# orchestrate_comprehensive_esperanto_text_replacementの引数をそのまま持って来た。
    """
    与えられた text を行単位で分割し、'process_segment' をマルチプロセスで並列実行した結果を結合。
    """
    if num_processes <= 1:
        # ここで「シングルコアで orche～ を直呼び」する
        return orchestrate_comprehensive_esperanto_text_replacement(
            text,
            placeholders_for_skipping_replacements,
            replacements_list_for_localized_string,
            placeholders_for_localized_replacement,
            replacements_final_list,
            replacements_list_for_2char,
            format_type
        )

    lines = re.findall(r'.*?\n|.+$', text)# 202502変更 '\n'を末尾に残したまま分割。(split('\n')は、'\n'を消してしまう。)
    num_lines = len(lines)

    # 行数が 0または1 の場合は単純に処理して返す (エラー回避の安全策)
    # （text.split('\n')で空でも [""] になるため num_lines=1 になるケースが多いです）
    if num_lines <= 1:
        # 並列化の意味がほぼないので、そのまま処理
        return orchestrate_comprehensive_esperanto_text_replacement(
            text,
            placeholders_for_skipping_replacements,
            replacements_list_for_localized_string,
            placeholders_for_localized_replacement,
            replacements_final_list,
            replacements_list_for_2char,
            format_type
        )

    # 通常ケース: 行数が2以上
    lines_per_process = max(num_lines // num_processes, 1)
    # 各プロセスに割り当てる行のリストを決定
    ranges = [(i * lines_per_process, (i + 1) * lines_per_process) for i in range(num_processes)]
    # 最後に残り全部を割り当て
    ranges[-1] = (ranges[-1][0], num_lines)  # 最後のプロセスが残り全てを処理

    with multiprocessing.Pool(processes=num_processes) as pool:
        # 並列処理を実行
        results = pool.starmap(process_segment,
            [(lines[start:end],
                placeholders_for_skipping_replacements,replacements_list_for_localized_string,placeholders_for_localized_replacement,
                replacements_final_list,replacements_list_for_2char,format_type)
                for (start, end) in ranges])
    # 結果を結合
    return ''.join(results)# 202502変更


## 追加

def apply_ruby_html_header_and_footer(processed_text: str, format_type: str) -> str:
    """
    指定された出力形式に応じて、processed_text に対するHTMLヘッダーとフッターを適用する。

    Args:
        processed_text (str): 既に生成された置換後のテキスト（HTMLの一部）。
        format_type (str): 出力形式。例えば、'HTML格式_Ruby文字_大小调整' など。

    Returns:
        str: ヘッダーとフッターが付加された最終的なHTMLテキスト。
    """
    if format_type in ('HTML格式_Ruby文字_大小调整','HTML格式_Ruby文字_大小调整_汉字替换'):
        # html形式におけるルビサイズの変更形式
        ruby_style_head="""<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>エスペラント語根分解ルビ注釈テキスト</title>
    <style>

    html, body {
      -webkit-text-size-adjust: 100%;
      -moz-text-size-adjust: 100%;
      -ms-text-size-adjust: 100%;
      text-size-adjust: 100%;
    }


      :root {
        --ruby-color: blue;
        --ruby-font-size: 0.5em;
      }
      html {
        font-size: 100%; /* 多くのブラウザは16px相当が標準 */
      }

      .text-M_M {
        font-size: 1rem!important;
        font-family: Arial, sans-serif;
        line-height: 2.0 !important;  /* text-M_Mのline-heightとrubyのline-heightは一致させる必要がある。 */
        display: block; /* ブロック要素として扱う */
        position: relative;
      }

      /* ▼ ルビ（フレックスでルビを上に表示） */
      ruby {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        vertical-align: top !important;
        line-height: 2.0 !important;
        margin: 0 !important;
        padding: 0 !important;
        font-size: 1rem !important;
      }

      /* ▼ 追加マイナス余白（ルビサイズ別に上書き） */
      rt {
        display: block !important;
        font-size: var(--ruby-font-size);
        color: var(--ruby-color);
        line-height: 1.05;/*ルビを改行するケースにおけるルビの行間*/
        text-align: center;
        /* margin-top: 0.2em !important;
        transform: translateY(0.4em) !important; */
      }
      rt.XXXS_S {
        --ruby-font-size: 0.3em;
        margin-top: -8.3em !important;/* ルビの高さ位置はここで調節する。 */
        transform: translateY(-0em) !important;
      }
      rt.XXS_S {
        --ruby-font-size: 0.3em;
        margin-top: -7.2em !important;/* ルビの高さ位置はここで調節する。 */
        transform: translateY(-0em) !important;
      }
      rt.XS_S {
        --ruby-font-size: 0.3em;
        margin-top: -6.1em !important;
        transform: translateY(-0em) !important;
      }
      rt.S_S {
        --ruby-font-size: 0.4em;
        margin-top: -4.85em !important;
        transform: translateY(-0em) !important;
      }
      rt.M_M {
        --ruby-font-size: 0.5em;
        margin-top: -4.00em !important;
        transform: translateY(-0.0em) !important;
      }
      rt.L_L {
        --ruby-font-size: 0.6em;
        margin-top: -3.55em !important;
        transform: translateY(-0.0em) !important;
      }
      rt.XL_L {
        --ruby-font-size: 0.7em;
        margin-top: -3.20em !important;
        transform: translateY(-0.0em) !important;
      }
      rt.XXL_L {
        --ruby-font-size: 0.8em;
        margin-top: -2.80em !important;
        transform: translateY(-0.0em) !important;
      }

    </style>
  </head>
  <body>
  <p class="text-M_M">
"""
        ruby_style_tail = "</p></body></html>"
    elif format_type in ('HTML格式','HTML格式_汉字替换'):
        ruby_style_head = """<style>
ruby rt {
    color: blue;
}
</style>
"""
        ruby_style_tail = "<br>"
    else:
        ruby_style_head = ""
        ruby_style_tail = ""

    return ruby_style_head + processed_text + ruby_style_tail


# --- 使用例 ---
# たとえば、既に生成済みの processed_text がある場合
# format_type = 'HTML格式_Ruby文字_大小调整'
# final_text = apply_ruby_style(processed_text, format_type)
# st.write(final_text)  # または st.components.v1.html(final_text, height=500)
