#!/usr/bin/env python3
"""Part 7: Fix remaining bare words - bare roots before <ruby>, remaining country names,
ALL-CAPS header words, frequently occurring proper nouns."""
import re

filepath = '202603_Revuo_eltiritaj_Esperantaj_pagxoj_kun_japanaj_tradukoj.html'

with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

original = text
changes = []

def fix(old, new, desc, count=1):
    global text
    if old not in text:
        print(f"  WARNING not found: {desc}")
        return
    if count == -1:
        n = text.count(old)
        text = text.replace(old, new)
        changes.append(f"{desc} (x{n})")
    else:
        text = text.replace(old, new, count)
        changes.append(desc)

# ============================================================
# A. Bare roots before <ruby> tags
# ============================================================
# Taj<ruby>land → <ruby>Taj<rt class="L_L">タイ</rt></ruby><ruby>land
# Taj = 3 base, 2 ann "タイ" → L_L
fix('Taj<ruby>land', '<ruby>Taj<rt class="L_L">タイ</rt></ruby><ruby>land', 'Taj → タイ (before land)', -1)

# ============================================================
# B. Remaining Japanio contexts
# ============================================================
# L142: Japanio) - in parentheses
fix(' Japanio)**', ' <ruby>Japan<rt class="XXL_L">日本</rt></ruby>io)**', 'L142: Japanio) → 日本')

# L422: Japanio** - with bold markers
fix(' Japanio**', ' <ruby>Japan<rt class="XXL_L">日本</rt></ruby>io**', 'L422: Japanio** → 日本')

# ============================================================
# C. Graz (Austrian city, 10 occurrences) → グラーツ
# Graz = 4 base, 4 ann "グラーツ" → L_L
# ============================================================
# Various contexts for Graz:
fix(' Graz-"', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby>-"', 'Graz- → グラーツ')
fix(' Graz <ruby>est', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby> <ruby>est', 'Graz est → グラーツ', -1)
fix(' Graz <ruby>oni', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby> <ruby>oni', 'Graz oni → グラーツ')
fix(' Graz.**', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby>.**', 'Graz. → グラーツ', -1)
fix(' Graz <ruby>spe', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby> <ruby>spe', 'Graz spe → グラーツ')
fix(' Graz, <ruby>kiu', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby>, <ruby>kiu', 'Graz, kiu → グラーツ')
fix(' Graz <ruby>don', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby> <ruby>don', 'Graz don → グラーツ')
fix(' Graz <ruby>al', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby> <ruby>al', 'Graz al → グラーツ')
# Catch any remaining Graz followed by space+ruby
fix(' Graz <ruby>', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby> <ruby>', 'Graz (generic) → グラーツ', -1)
# Graz followed by comma
fix(' Graz,', ' <ruby>Graz<rt class="L_L">グラーツ</rt></ruby>,', 'Graz, → グラーツ', -1)

# ============================================================
# D. Siga (Shiga prefecture, 2 occurrences) → 滋賀
# Siga = 4 base, 2 ann "滋賀" → L_L
# ============================================================
fix(' Siga <ruby>kaj', ' <ruby>Siga<rt class="L_L">滋賀</rt></ruby> <ruby>kaj', 'L227: Siga → 滋賀')
fix(' Siga.**', ' <ruby>Siga<rt class="L_L">滋賀</rt></ruby>.**', 'L224: Siga → 滋賀')

# ============================================================
# E. Eggenberg (Austrian castle/district, 2 occurrences) → エッゲンベルク
# Eggenberg = 9 base, 7 ann → XXL_L
# ============================================================
fix(' Eggenberg', ' <ruby>Eggenberg<rt class="XXL_L">エッゲンベルク</rt></ruby>', 'Eggenberg → エッゲンベルク', -1)

# ============================================================
# F. ALL-CAPS header bare words
# ============================================================
# L108: ĈI- (proximity particle in ALL-CAPS context)
fix('ĈI-<RUBY>AŬGUST', '<RUBY>ĈI<RT CLASS="M_M">近接</RT></RUBY>-<RUBY>AŬGUST', 'L108: ĈI → 近接 (ALL-CAPS)')

# L111: AŬSTRIO! (Austria in ALL-CAPS)
fix(' AŬSTRIO!**', ' <RUBY>AŬSTRI<RT CLASS="L_L">オーストリア</RT></RUBY>O!**', 'L111: AŬSTRIO → オーストリア (ALL-CAPS)')

# L111: "LA (bare in ALL-CAPS context)
fix('"LA <RUBY>VERD', '"<RUBY>LA<RT CLASS="M_M">THE</RT></RUBY> <RUBY>VERD', 'L111: "LA → THE (ALL-CAPS)')

# L111: UK (abbreviation - Universala Kongreso)
fix(' UK <RUBY>ATEND', ' <RUBY>UK<RT CLASS="XXL_L">世界大会</RT></RUBY> <RUBY>ATEND', 'L111: UK → 世界大会')

# L635: MALAGASIO! (Madagascar in ALL-CAPS)
fix(' MALAGASIO!**', ' <RUBY>MALAGAS<RT CLASS="XL_L">マダガスカル</RT></RUBY>IO!**', 'L635: MALAGASIO → マダガスカル (ALL-CAPS)')

# L123/L173: GRAZ (in ALL-CAPS header)
fix(' GRAZ**', ' <RUBY>GRAZ<RT CLASS="L_L">グラーツ</RT></RUBY>**', 'GRAZ → グラーツ (ALL-CAPS)', -1)

# ============================================================
# G. Other remaining words
# ============================================================
# L474: Duolingon (Duolingo with accusative) - proper app name
# Duolingo = 8 base, 7 ann "デュオリンゴ" → XXL_L
fix(' Duolingon, ', ' <ruby>Duoling<rt class="XXL_L">デュオリンゴ</rt></ruby>on, ', 'L474: Duolingon → デュオリンゴ')

# L595: Duolingo- (with hyphen)
fix(' Duolingo-<ruby>', ' <ruby>Duoling<rt class="XXL_L">デュオリンゴ</rt></ruby>o-<ruby>', 'L595: Duolingo → デュオリンゴ')

# L474: Instagramo (Instagram with -o ending)
# Instagram = 9 base, 6 ann "インスタグラム" → XXL_L
fix(' Instagramo <ruby>kaj', ' <ruby>Instagram<rt class="XXL_L">インスタグラム</rt></ruby>o <ruby>kaj', 'L474: Instagramo → インスタグラム')
fix(' Instagramo.**', ' <ruby>Instagram<rt class="XXL_L">インスタグラム</rt></ruby>o.**', 'L604: Instagramo → インスタグラム')

# ============================================================
# Report
# ============================================================
print(f"=== Part 7: Remaining bare words ===")
print(f"Total changes: {len(changes)}")
for c in changes:
    print(f"  - {c}")

if text != original:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"\nFile saved successfully.")
else:
    print(f"\nNo changes needed.")
