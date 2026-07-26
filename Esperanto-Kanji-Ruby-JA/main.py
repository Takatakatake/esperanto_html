# メインの Streamlit アプリ (機能拡充版202502)

import streamlit as st
import re
import io
import os
import json
import pandas as pd  # 必要なら使う
from typing import List, Dict, Tuple, Optional
import streamlit.components.v1 as components

# Streamlit Cloud等では作業ディレクトリがリポジトリのルート(複数アプリの親)になるため、
# './app_data/...' の相対パスが解決できずFileNotFoundになる。このスクリプト(アプリ)の
# 置かれたディレクトリへCWDを固定し、ローカル/Cloudどちらでも相対パスを正しく解決する。
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import multiprocessing
# multiprocessing時のPicklingError回避のため 'spawn' を明示: streamlitでは必ず必要。
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass  # すでに start method が設定済みの場合はここで無視する


from esp_text_replacement_module import (
    x_to_circumflex,
    x_to_hat,
    hat_to_circumflex,
    circumflex_to_hat,

    replace_esperanto_chars,
    import_placeholders,

    orchestrate_comprehensive_esperanto_text_replacement,
    parallel_process,
    apply_ruby_html_header_and_footer,
    circumflex_to_x, hat_to_x,
)

## 関数のキャッシュを活用することで、デフォルトの置換用JSONファイル(50MB程度)の読み込みを早くする。(約1.0秒→0.5秒 の短縮)
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    """
    JSONファイルをロードし、以下の3つのリストをタプルとして返す:
      1) replacements_final_list
      2) replacements_list_for_localized_string
      3) replacements_list_for_2char
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    replacements_final_list = data.get(
        "全域替换用のリスト(列表)型配列(replacements_final_list)", []
    )
    replacements_list_for_localized_string = data.get(
        "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", []
    )
    replacements_list_for_2char = data.get(
        "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", []
    )

    return (
        replacements_final_list,
        replacements_list_for_localized_string,
        replacements_list_for_2char,
    )

# ページ設定
st.set_page_config(page_title="エスペラント文の注釈ルビ・漢字化ツール", page_icon="📖", layout="wide")

st.title("エスペラント文の注釈ルビ・漢字化ツール")
st.caption("語根ごとに日本語注釈をルビ表示 / 漢字置換(ルビつき・純テキスト)")
st.markdown("📘 [**プロジェクト早わかりガイド**](https://takatakatake.github.io/kanji_assign/index.html) — 語根分解・漢字割り当て・各アプリの全体像を1ページで(日本語/中文/한국어 切替可)")

st.write("---")

# 1) JSONファイル (置換ルール) をロードする (デフォルト or アップロード)
selected_option = st.radio(
    "変換モードを選択:",
    ("📖 注釈ルビ（語根の上に日本語訳）", "🈶 漢字化（漢字＋語根ルビ）", "✂️ 漢字化・純粋置換（タグなしテキスト）", "📤 自作JSONを使う（上級）")
)

st.caption("はじめての方は **「📖 注釈ルビ」のまま**でOKです（原文はそのまま、語根の上に日本語訳が付きます）。")

if "🈶" in selected_option or "✂️" in selected_option:
    st.caption("💡 漢字モードでは、漢字の右肩の小さな文字（例: 扩ᴬᴷ・金ⱽ・员ᴬ）が付くことがあります。これは同じ漢字を複数の語根で共用する際の**判別マーク**（語根の綴り由来）で、読み分けの助けになります。")



replacements_final_list: List[Tuple[str, str, str]] = []
replacements_list_for_localized_string: List[Tuple[str, str, str]] = []
replacements_list_for_2char: List[Tuple[str, str, str]] = []

if selected_option == "📖 注釈ルビ（語根の上に日本語訳）":
    default_json_path = "./app_data/置換リスト_ルビ.json"
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(default_json_path)
        st.success("✅ 注釈ルビモードの準備ができました。このまま下の入力欄に文章を入れて「🔁 変換する」を押してください。")
    except Exception as e:
        st.error(f"JSONファイルの読み込みに失敗: {e}")
        st.stop()
elif selected_option == "🈶 漢字化（漢字＋語根ルビ）":
    kanji_json_path = "./app_data/置換リスト_漢字.json"
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(kanji_json_path)
        st.success("✅ 漢字化モードの準備ができました（漢字が本文・語根がルビ）。下の入力欄に文章を入れて「🔁 変換する」を押してください。")
    except Exception as e:
        st.error(f"漢字化版JSONの読み込みに失敗: {e}")
        st.stop()
elif selected_option == "✂️ 漢字化・純粋置換（タグなしテキスト）":
    pure_json_path = "./app_data/置換リスト_漢字_純粋置換.json"
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(pure_json_path)
        st.success("✅ 漢字化・純粋置換モードの準備ができました（タグなしの漢字テキストに変換。例: amikeco → 友性o）。下の入力欄に文章を入れて「🔁 変換する」を押してください。")
    except Exception as e:
        st.error(f"純粋置換版JSONの読み込みに失敗: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("置換用JSONファイル(.json)をアップロード（ファイル名が『○○(合并3个JSON文件).json』形式のもの）", type="json")
    if uploaded_file is not None:
        try:
            combined_data = json.load(uploaded_file)
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
            st.success("アップロードしたJSONの読み込みに成功しました。")
            if not (replacements_final_list or replacements_list_for_localized_string or replacements_list_for_2char):
                st.error("このJSONには置換ルールが見つかりません（キー名が想定と異なる可能性）。JSON生成に使ったツールの『合并3个JSON文件』形式かご確認ください。")
            _probe = next((e[1] for e in replacements_final_list[:200] if isinstance(e, (list, tuple)) and len(e) >= 2 and isinstance(e[1], str) and e[1].strip()), "")
            if "<ruby>" in _probe:
                st.caption("🔍 検出: **HTMLルビ形式**で作られたJSONのようです → 下の出力形式は「HTMLルビ形式」系を選んでください。")
            elif _probe:
                st.caption("🔍 検出: **タグなし形式**のJSONのようです → 下の出力形式は「括弧形式」か「単純置換」を選んでください。")
        except Exception as e:
            st.error(f"アップロードJSONファイルの読み込みに失敗しました（{e}）。この欄に入れるのは『合并3个JSON文件』形式の置換用JSONです。手動補正ファイル（user_corrections.json）は、下の『📂 手動補正ファイル…を読み込む』欄へどうぞ。")
            st.stop()
    else:
        st.warning("JSONファイルがアップロードされていません。処理を停止します。")
        st.stop()

# 1.5) 手動補正(軽量オーバーレイ)を最優先で適用
#   「語根分解の手動補正」ページで保存した補正(app_data/user_corrections.json)を、
#   置換用JSONを再生成せずに実行時へ反映する。補正語より長い語を先に置換するよう安全挿入。
# 1.4) 手元の user_corrections.json をこのセッションへ読み込む(任意)
with st.expander("📂 手動補正ファイル(user_corrections.json)を読み込む(任意)"):
    st.caption("「語根分解の手動補正」ページでダウンロードした補正を、このセッションに適用します(他の利用者には影響しません)。")
    _cor_up = st.file_uploader("user_corrections.json", type="json", key="main_cor_upload")
    if _cor_up is not None and st.session_state.get("main_cor_loaded") != getattr(_cor_up, "file_id", True):
        try:
            import esp_overlay_module as _ovu
            _decs = [c.get("decomp") for c in json.load(_cor_up) if isinstance(c, dict) and c.get("decomp")]
            _new = []
            for _dc in _decs:
                try: _new.append(_ovu.build_correction(_dc, "./app_data"))
                except Exception: pass
            if _new:
                _ovu.save_corrections("./app_data", _new)
            else:
                st.error("有効な補正が0件でした。『語根分解の手動補正』ページでダウンロードした user_corrections.json かご確認ください（現在の補正は変更していません）。")
            st.session_state["main_cor_loaded"] = getattr(_cor_up, "file_id", True)
            st.success(f"{len(_new)} 件の補正をこのセッションに適用しました。") if _new else None
        except Exception as _e:
            st.error(f"読み込み失敗（{_e}）。『語根分解の手動補正』ページでダウンロードした user_corrections.json かご確認ください。")

try:
    import esp_overlay_module as _ov
    _ov_mode = "kanji" if selected_option in ("🈶 漢字化（漢字＋語根ルビ）", "✂️ 漢字化・純粋置換（タグなしテキスト）") else "ruby"
    _ov_entries_raw = _ov.load_overlay_entries("./app_data", _ov_mode)
    if selected_option == "✂️ 漢字化・純粋置換（タグなしテキスト）":
        import re as _re_ov
        _ov_entries = [[o, _re_ov.sub(r"</?ruby>", "", _re_ov.sub(r"<rt[^>]*>.*?</rt>", "", n, flags=_re_ov.DOTALL | _re_ov.IGNORECASE), flags=_re_ov.IGNORECASE), ph] for o, n, ph in _ov_entries_raw]
    else:
        _ov_entries = _ov_entries_raw
    if _ov_entries and not str(selected_option).startswith("📤"):
        # 自作JSONモードは形式が不明のため補正オーバーレイ(HTML)は適用しない
        replacements_final_list = _ov.merge_overlay(replacements_final_list, _ov_entries)
        st.info(f"語根分解の品質補正データ {len(_ov.load_corrections('./app_data'))} 件を自動適用中です（**操作は不要**。内容は「語根分解の手動補正」ページで確認・編集できます）。")
except Exception:
    pass  # オーバーレイは任意機能。失敗しても通常の置換は継続する。

# 2) placeholders (占位符) の読み込み
placeholders_for_skipping_replacements: List[str] = import_placeholders(
    './app_data/placeholders_skip.txt'
)
placeholders_for_localized_replacement: List[str] = import_placeholders(
    './app_data/placeholders_localcapture.txt'
)

st.write("---")


# 設定パラメータ (UI) - 高度な設定
with st.expander("⚙️ 高度な設定(並列処理・通常は変更不要)"):
    st.write("""
            ここでは、文字列(漢字)置換時に使用する並列処理のプロセス数を決めます。
            """)
    use_parallel = st.checkbox("並列処理を使う", value=False)
    num_processes = st.number_input("同時プロセス数", min_value=2, max_value=2, value=2, step=1)
    st.caption("⚠️ 並列処理はプロセスごとに置換リスト(約400MB)を複製します。Streamlit Cloud等のメモリが小さい環境では、メモリ超過でアプリが停止する恐れがあります(ローカルの多コアPC向けの機能です)。")


st.write("---")

# 例: 出力形式など。必要に応じて追加カスタマイズ
# 出力形式: 同梱JSONを使う場合は自動選択(操作不要)。アップロードJSONのときだけ手動で選ぶ。
_FMT_CHOICES = [
    ("HTMLルビ形式・幅調整つき【標準】 — 語根の上に訳がルビ表示: amiko → amik(上に「友」)o", "HTML格式_Ruby文字_大小调整"),
    ("HTMLルビ形式・幅調整つき【漢字置換】 — 漢字が本文・語根がルビ: amiko → 友(上に「amik」)o", "HTML格式_Ruby文字_大小调整_汉字替换"),
    ("HTMLルビ形式・シンプル(幅調整なし)", "HTML格式"),
    ("HTMLルビ形式・シンプル【漢字置換】", "HTML格式_汉字替换"),
    ("括弧形式 — タグなし: amiko → amik(友)o", "括弧(号)格式"),
    ("括弧形式【漢字置換】 — タグなし: amiko → 友(amik)o", "括弧(号)格式_汉字替换"),
    ("単純置換 — 訳/漢字だけ残す: amiko → 友o", "替换后文字列のみ(仅)保留(简单替换)"),
]
if selected_option == "📖 注釈ルビ（語根の上に日本語訳）":
    format_type = "HTML格式_Ruby文字_大小调整"
    st.info("出力形式: **HTMLルビ形式(幅調整つき)** — 同梱の注釈ルビJSONに合わせて自動選択済み。語根の上に訳がルビ表示されます。")
elif selected_option == "🈶 漢字化（漢字＋語根ルビ）":
    format_type = "HTML格式_Ruby文字_大小调整_汉字替换"
    st.info("出力形式: **HTMLルビ形式(漢字本文+語根ルビ)** — 同梱の漢字化JSONに合わせて自動選択済み。")
elif selected_option == "✂️ 漢字化・純粋置換（タグなしテキスト）":
    format_type = "替换后文字列のみ(仅)保留(简单替换)"
    st.info("出力形式: **単純置換(タグなしテキスト)** — 純粋置換JSONに合わせて自動選択済み。HTML不要でそのままコピーして使えます。")
else:
    _sel = st.selectbox(
        "出力形式を選択 (アップロードしたJSONを**作成したときの形式**に合わせてください)",
        [label for label, _v in _FMT_CHOICES],
    )
    format_type = dict(_FMT_CHOICES)[_sel]

# フォーム外で、変数 processed_text を初期化
processed_text = ""

# 4) 入力テキストのソースを選択 (アップロード or テキストエリア)
st.subheader("入力テキストのソース")
source_option = st.radio("入力テキストをどうしますか？", ("手動入力", "ファイルアップロード"))

uploaded_text = ""
if source_option == "ファイルアップロード":
    text_file = st.file_uploader("テキストファイルをアップロード (UTF-8)", type=["txt", "csv", "md"])
    if text_file is not None:
        uploaded_text = text_file.read().decode("utf-8", errors="replace")
        st.info("ファイルを読み込みました。")
    else:
        st.warning("テキストファイルがアップロードされていません。手動入力に切り替えるかファイルをアップロードしてください。")


# アップロードがあれば、フォーム生成前に session_state へ反映(key バインドの初期値として)
if uploaded_text:
    # 同一ファイルの再セットは初回のみ(欄内の手動修正が毎rerunで上書き破棄されるのを防ぐ)
    _tfid = getattr(text_file, "file_id", True)
    if st.session_state.get("_last_text_upload") != _tfid:
        st.session_state["text0_value"] = uploaded_text
        st.session_state["_last_text_upload"] = _tfid

_c1, _c2 = st.columns([1, 3])
with _c1:
    st.button("📝 サンプル文を入力する", on_click=lambda: st.session_state.update(text0_value='Saluton! Ĉu vi jam aŭdis, ke Esperanto estas internacia lingvo? Mi eĉ komencis lerni ĝin hodiaŭ, ĉar la komputilo kaj la telefono faciligas la lernadon. La amikeco inter la popoloj kreskas ĉiutage.'))
with _c2:
    st.caption("はじめての方へ: ボタンを押すとサンプル文が入り、すぐ変換を試せます。")

# st.stop経路(自作JSON未アップロード等)で text0_value がwidget cleanupで消えた場合の復元
if "text0_value" not in st.session_state and "_text0_keep" in st.session_state:
    st.session_state["text0_value"] = st.session_state["_text0_keep"]

with st.form(key='profile_form'):
    # text_area を key="text0_value" で session_state と双方向バインドする。
    # 旧方式(value=initial_text で session_state を初期値にする)は、送信時にウィジェットが
    # value= で前回値に戻され「1つ前の入力で変換される(1ステップ遅延)」バグの原因だった。
    # key= 方式では送信時に現在の入力がそのまま反映される。
    text0 = st.text_area(
        "エスペラントの文章を入力してください",
        height=150,
        key="text0_value"
    )
    st.session_state["_text0_keep"] = text0  # st.stop経路のwidget cleanup対策(非ウィジェットキーは生存)
    st.caption("💡 字上符付き文字は **cx / c^ / ĉ** のどの表記でも入力できます(例: sxatas・s^atas・ŝatas)。長文(数千行)は変換に数十秒かかることがあります。")

    with st.expander("🔖 一部だけ変換したくない/したい場合(%・@マーカー)"):
        st.markdown("""
- `%...%` で囲んだ部分は**変換されず原文のまま**残ります(50文字以内)。
  例: `%Universala Kongreso% okazos.` → **Universala Kongreso** はそのまま
- `@...@` で囲んだ部分**だけ**を変換します(18文字以内)。
  例: `@amiko@ kaj mi` → **amiko** だけ変換
""")

    letter_type = st.radio('エスペラント文字の表記(出力)', ('ĉ ĝ ĥ ĵ ŝ ŭ (標準)', 'cx gx hx jx sx ux (x形式)', 'c^ g^ h^ j^ s^ u^ (^形式)'))

    submit_btn = st.form_submit_button('🔁 変換する', type="primary")


    if submit_btn and not (text0 or "").strip():
        st.warning("テキストが空です。エスペラント文を入力してから「変換する」を押してください。")
        st.stop()

    if submit_btn:
        # text0 は key="text0_value" で session_state と双方向バインド済み。
        # ここで手動代入するとウィジェット生成後の session_state 変更となりエラーになるため行わない。

        if use_parallel:
            processed_text = parallel_process(
                text=text0,
                num_processes=num_processes,
                placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                replacements_list_for_localized_string=replacements_list_for_localized_string,
                placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                replacements_final_list=replacements_final_list,
                replacements_list_for_2char=replacements_list_for_2char,
                format_type=format_type
            )
        else:
            processed_text = orchestrate_comprehensive_esperanto_text_replacement(
                text=text0,
                placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                replacements_list_for_localized_string=replacements_list_for_localized_string,
                placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                replacements_final_list=replacements_final_list,
                replacements_list_for_2char=replacements_list_for_2char,
                format_type=format_type
            )

        # 1パス目に「先頭1字孤立」過分解(子音1字の遊離: fero->f/er/o 等)があれば、
        # 自動補正を最優先でmergeして2パス目を描画(機構レベルで欠陥クラスを一掃)。
        # 孤立が無ければ何もしない(通常テキストは大半がこれ)。
        try:
            import esp_overlay_module as _ovx
            _afmode = "kanji" if selected_option in ("🈶 漢字化（漢字＋語根ルビ）", "✂️ 漢字化・純粋置換（タグなしテキスト）") else "ruby"  # sample_btn_marker
            _auto_strip_pure = (selected_option == "✂️ 漢字化・純粋置換（タグなしテキスト）")
            _auto = _ovx.auto_overlay_entries(processed_text, "./app_data", _afmode)
            if _auto and _auto_strip_pure:
                import re as _re_af
                _auto = [[o, _re_af.sub(r"</?ruby>", "", _re_af.sub(r"<rt[^>]*>.*?</rt>", "", n, flags=_re_af.DOTALL | _re_af.IGNORECASE), flags=_re_af.IGNORECASE), ph] for o, n, ph in _auto]
            if _auto:
                _GGx = _ovx.merge_overlay(replacements_final_list, _auto)
                if use_parallel:
                    processed_text = parallel_process(
                        text=text0, num_processes=num_processes,
                        placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                        replacements_list_for_localized_string=replacements_list_for_localized_string,
                        placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                        replacements_final_list=_GGx,
                        replacements_list_for_2char=replacements_list_for_2char,
                        format_type=format_type)
                else:
                    processed_text = orchestrate_comprehensive_esperanto_text_replacement(
                        text=text0,
                        placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                        replacements_list_for_localized_string=replacements_list_for_localized_string,
                        placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                        replacements_final_list=_GGx,
                        replacements_list_for_2char=replacements_list_for_2char,
                        format_type=format_type)
        except Exception:
            pass  # 自動補正は任意。失敗しても1パス目の結果をそのまま使う。

        # letter_typeに応じて再変換
        if letter_type == 'ĉ ĝ ĥ ĵ ŝ ŭ (標準)':
            processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
            processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
        elif letter_type == 'cx gx hx jx sx ux (x形式)':
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_x)
            processed_text = replace_esperanto_chars(processed_text, hat_to_x)
        elif letter_type == 'c^ g^ h^ j^ s^ u^ (^形式)':
            processed_text = replace_esperanto_chars(processed_text, x_to_hat)
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)

        processed_text = apply_ruby_html_header_and_footer(processed_text, format_type)

        # 結果を session_state に保存（再実行で消えない＋結果を編集可能にするため）
        st.session_state["result_html"] = processed_text
        st.session_state["edited_html"] = processed_text          # 編集用の初期値＝生成結果
        st.session_state["result_is_html"] = ("HTML" in format_type)
        st.toast("✅ 変換が完了しました。下に結果が表示されています。")

# =========================================
# フォーム外の処理: 結果のプレビュー・編集・ダウンロード
# =========================================
def _reset_edited_html():
    # 「編集を破棄」用コールバック（ウィジェット生成後に session_state を変更すると
    #  エラーになるため、コールバック内で生成結果へ戻す）
    st.session_state["edited_html"] = st.session_state.get("result_html", "")

if st.session_state.get("result_html"):
    # st.stop()経路(自作JSON未アップロード等)のwidget cleanupで edited_html が消えた場合の再シード
    if "edited_html" not in st.session_state:
        st.session_state["edited_html"] = st.session_state["result_html"]
    st.caption("**結果の見方**: 「HTMLプレビュー」タブが完成イメージです（各語根の上の小さい文字が日本語訳のルビ）。"
               "「HTMLソース（編集可）」タブは中身のHTML文字列で、ブログ等への貼り付けや直接修正ができます。"
               "修正はプレビューとダウンロードに反映されます（再変換すると生成結果に戻ります）。")

    # 編集後の内容（なければ生成結果）。プレビュー・ダウンロードとも、この内容を使う。
    current_html = st.session_state.get("edited_html", st.session_state["result_html"])

    # 長文時はプレビューのみ一部省略（編集とダウンロードは常に全文が対象）
    MAX_PREVIEW_LINES = 250
    lines = current_html.splitlines()
    if len(lines) > MAX_PREVIEW_LINES:
        preview_text = "\n".join(lines[:247]) + "\n...\n" + "\n".join(lines[-3:])
        st.warning(
            f"テキストが長いため（総行数 {len(lines)} 行）、プレビューは一部省略しています"
            "（編集・ダウンロードは全文が対象です）。"
        )
    else:
        preview_text = current_html

    if st.session_state.get("result_is_html"):
        tab1, tab2 = st.tabs(["HTMLプレビュー", "HTMLソース（編集可）"])
        with tab1:
            components.html(preview_text, height=500, scrolling=True)
        with tab2:
            st.text_area(
                "出力HTMLを直接編集できます（編集後、プレビューとダウンロードに反映されます）",
                key="edited_html",
                height=300
            )
            st.button("編集を破棄して生成結果に戻す", on_click=_reset_edited_html)
        download_name = "置換結果.html"
    else:
        tab3_list = st.tabs(["📋 コピー用(右上のアイコンでコピー)", "✏️ 編集"])
        with tab3_list[0]:
            st.code(preview_text, language=None)
        with tab3_list[1]:
            st.text_area("出力を直接編集できます", key="edited_html", height=300)
            st.button("編集を破棄して生成結果に戻す", on_click=_reset_edited_html)
        download_name = "置換結果.txt"

    download_data = current_html.encode('utf-8')
    st.download_button(
        label="置換結果のダウンロード（編集を反映）",
        data=download_data,
        file_name=download_name,
        mime="text/html"
    )
    st.caption("※ ダウンロードした .html ファイルは、**ダブルクリックするとブラウザでルビ付きのまま**開けます。Word等に貼りたい場合はブラウザで開いてからコピーしてください。")
    st.page_link("pages/1_🔧_語根分解の手動補正.py", label="🔧 分解がおかしい箇所があった → 手動補正ページで直す(即反映)")

st.write("---")
st.header("Ligilo-oj (URL-oj) / 言語版・语言版本・언어판")
st.markdown("""
#### 日中韓 三言語版 ⇓ (Japana / Ĉina / Korea)
- **日本語版 (Japana)**: https://esperanto-radiko-cjk-annotator.streamlit.app/
- **中文版 (Ĉina)**: https://esperanto-radiko-cjk-annotator-zh.streamlit.app/
- **한국어판 (Korea)**: https://esperanto-radiko-cjk-annotator-ko.streamlit.app/

#### GitHub-deponejo (fontkodo & uzadaj instrukcioj) ⇓
https://github.com/Takatakatake/esperanto-radiko-cjk-annotator
""")
