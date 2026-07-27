# Windows新規環境セットアップ簡易指南 - Esperanto HTML作業

作成日: 2026-04-30  
用途: 新しいWindows環境で、エスペラント語根分解ルビHTMLの修正・検証作業を始めるための最小ガイド。

## 1. この文書の目的

Ubuntuで行ってきた次の作業を、Windowsでも安定して行うための手順をまとめます。

- エスペラント本文・日本語訳入りHTMLを修正する
- `エスペラントルビHTML修正ガイド260328.txt` に従って、語根分解ミス・注釈漏れを直す
- `ruby_css_verifier.py` でルビサイズを検証・修正する

詳しい背景説明よりも、新環境で迷わず動かすことを優先します。

## 2. 事前にコピーしておくもの

作業フォルダを1つ作り、少なくとも次を置きます。

```text
エスペラントルビHTML修正ガイド260328.txt
ruby_css_verifier.py
Unicode_BMP全范围文字幅(宽)_Arial16.json
修正対象のHTML
必要ならPDF、抽出済みEsperantoテキスト
```

重要:

- `ruby_css_verifier.py` と `Unicode_BMP全范围文字幅(宽)_Arial16.json` は同じフォルダに置くのが安全です。
- 日本語やエスペラント文字を含むファイル名が多いので、PowerShellではパスを必ず引用符で囲みます。
- 新規環境では、作業フォルダを深くしすぎない方が安全です。長い日本語パスで問題が出る場合は、`C:\Esperanto_HTML` のような短い場所に置きます。

## 3. 推奨環境

Windowsネイティブの Miniforge + Conda環境を使います。

理由:

- Windowsの `python` はMicrosoft Storeエイリアスのことがある
- 専用環境にすればPDF処理・HTML検証ライブラリを固定できる
- Windowsブラウザでの表示確認と相性がよい
- Ubuntuのbash資産をそのまま使う必要がある時だけWSLを使えばよい

## 4. Miniforgeを入れる

Miniforgeをインストールします。公式のMiniforge配布元から、Windows 64bit用の `Miniforge3-Windows-x86_64.exe` を入手します。

推奨インストール先:

```text
C:\Users\<ユーザー名>\miniforge3
```

インストール時は、基本的に「Just Me」でよいです。PATHに追加しなくても構いません。むしろ最初は追加せず、フルパスで呼ぶ方が事故が少ないです。

以後の例では、次の場所にある前提です。

```powershell
$env:USERPROFILE\miniforge3
```

## 5. Conda環境を作る

作業フォルダに移動します。

```powershell
cd "C:\Users\<ユーザー名>\Documents\Esperanto_HTML文書"
```

環境定義ファイルを作る場合は、`environment-windows.yml` を次の内容にします。

```yaml
name: esperanto-html
channels:
  - conda-forge
dependencies:
  - python=3.12
  - pip
  - beautifulsoup4
  - lxml
  - regex
  - pypdf
  - pymupdf
  - pdfplumber
  - charset-normalizer
```

環境を作成します。

```powershell
& "$env:USERPROFILE\miniforge3\Scripts\conda.exe" env create -f environment-windows.yml
```

`environment-windows.yml` を作らず、直接コマンドで作る場合は次でも構いません。

```powershell
& "$env:USERPROFILE\miniforge3\Scripts\conda.exe" create -n esperanto-html -c conda-forge python=3.12 pip beautifulsoup4 lxml regex pypdf pymupdf pdfplumber charset-normalizer -y
```

既に環境がある場合の更新:

```powershell
& "$env:USERPROFILE\miniforge3\Scripts\conda.exe" env update -n esperanto-html -f environment-windows.yml --prune
```

確認:

```powershell
& "$env:USERPROFILE\miniforge3\Scripts\conda.exe" env list
& "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" --version
```

主要ライブラリのimport確認:

```powershell
$env:PYTHONIOENCODING='utf-8'
& "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" -c "import bs4, lxml, regex, pypdf, fitz, pdfplumber, charset_normalizer; print('OK')"
```

## 6. Python実行の基本方針

裸の `python` / `python3` は使いません。

安全な実行:

```powershell
& "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" script.py
```

または:

```powershell
& "$env:USERPROFILE\miniforge3\Scripts\conda.exe" run -n esperanto-html python script.py
```

短い検証を何度も行う場合は、環境内Pythonを直接呼ぶ方が速くて分かりやすいです。

## 7. 文字コード対策

PowerShellでは、エスペラント特殊文字を含む出力で `cp932` エラーが出ることがあります。

検証作業の前に必ず指定します。

```powershell
$env:PYTHONIOENCODING='utf-8'
```

必要なら追加で:

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001
```

## 8. ruby_css_verifier.py の実行

`Unicode_BMP全范围文字幅(宽)_Arial16.json` が見つからないというエラーが出た場合は、文字幅JSONを `ruby_css_verifier.py` と同じフォルダに置き直します。

自動修正前に手動バックアップを残すなら:

```powershell
$src = "修正対象.html"
Copy-Item -LiteralPath $src -Destination "$src.bak_before_fix_$(Get-Date -Format yyyyMMdd_HHmmss)"
```

検証のみ:

```powershell
$env:PYTHONIOENCODING='utf-8'
& "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" "ruby_css_verifier.py" "修正対象.html" --margin 0.05
```

自動修正あり:

```powershell
$env:PYTHONIOENCODING='utf-8'
& "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" "ruby_css_verifier.py" "修正対象.html" --fix --margin 0.05
```

実際の配置が深い場合は、`ruby_css_verifier.py` のパスを引用符付きで指定します。

```powershell
$env:PYTHONIOENCODING='utf-8'
& "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" "京大エス研html文書＿Github＿実際にHTMLを作成する場所_編集場所＿git外\esperanto_html_redaktado\ruby_css_verifier.py" "RO_202605_eltiritaj_esperantaj_pagxoj_kun_japanaj_tradukoj.html" --fix --margin 0.05
```

`--margin 0.05` は、しきい値付近の境界ケースを無理に直さないための指定です。

## 9. HTML修正時の重点チェック

`エスペラントルビHTML修正ガイド260328.txt` を読んだうえで、特に次を確認します。

- 2文字以上のエスペラント語根が裸テキストで残っていないか
- `La/la`, `kaj`, `ĉu`, `eĉ`, `mi`, `ni`, `ĝi` などが裸で残っていないか
- 固有名詞が語根分解されていないか
- 固有名詞に `[人名]`, `[地名]`, `[団体]`, `[施設]`, `[雑誌]`, `[番組]` などが付いているか
- `s-ro`, `s-ino`, `d-ro`, `prof.`, `vd.`, `p.` など略語が1つのrubyになっているか
- 地名の対格 `n` がruby内に入り込んでいないか
- 一般語根のハイフンがruby内に入っていないか
- 外来語や人名が偶然エスペラント語根として分解されていないか
- `dis`, `ret`, `ĝoj`, `gas`, `tan`, `gant` など偽語根候補が、本当に文脈上の語根か

細かな日本語訳ニュアンスより、語根境界ミス・注釈漏れ・固有名詞タグ漏れを優先します。

## 10. 修正後の最小検証

ruby/rt数を確認します。

```powershell
$env:PYTHONIOENCODING='utf-8'
@'
from pathlib import Path
s = Path("修正対象.html").read_text(encoding="utf-8")
print("ruby", s.count("<ruby>"), s.count("</ruby>"))
print("rt", s.count("<rt "), s.count("</rt>"))
'@ | & "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" -
```

次に `ruby_css_verifier.py` を実行します。

```powershell
$env:PYTHONIOENCODING='utf-8'
& "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" "ruby_css_verifier.py" "修正対象.html" --fix --margin 0.05
```

理想:

```text
Fixable: 0
Boundary(skip): 数件
```

`Fixable: 0` なら、非境界のCSS修正対象は残っていません。

最後に、Windows側のChromeまたはEdgeでHTMLを開き、ルビが本文にかぶりすぎていないか目視します。

抽出済みEsperantoテキストがある場合は、HTMLからruby/rtを除去した本文と照合し、原文の文字列自体を誤って変えていないか確認します。語根分解や注釈を直す作業では、原文本文を勝手に直さないことが重要です。

## 11. PowerShellでUbuntu式コマンドを置き換える

Ubuntu/bashの here-doc:

```bash
python3 - <<'PY'
print("test")
PY
```

PowerShellではこうします。

```powershell
@'
print("test")
'@ | & "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" -
```

短い確認なら:

```powershell
& "$env:USERPROFILE\miniforge3\envs\esperanto-html\python.exe" -c "print('test')"
```

## 12. パス・検索・バックアップの注意

日本語ファイル名は `-LiteralPath` が安全です。

```powershell
Get-Content -LiteralPath "エスペラントルビHTML修正ガイド260328.txt" -Encoding UTF8
```

`rg` は対象HTMLを明示します。指定しないとバックアップや別年度HTMLまで検索されます。

```powershell
rg -n "Japanio|Eŭrop|Kameoka" "修正対象.html"
```

新規Windows環境で `rg` が無い場合は、まずPowerShell標準の `Select-String` で代用できます。

```powershell
Select-String -LiteralPath "修正対象.html" -Pattern "Japanio|Eŭrop|Kameoka"
```

`rg` を入れる場合は、wingetが使える環境なら次が簡単です。

```powershell
winget install BurntSushi.ripgrep.MSVC
```

`ruby_css_verifier.py --fix` は、自動で `.bak_YYYYMMDD_HHMMSS` のバックアップを作ります。これは正常です。

## 13. WSLを使うべき場面

通常のHTML修正・検証は、WindowsネイティブCondaで十分です。

WSLを使うとよい場面:

- Ubuntuで作ったbashスクリプトをそのまま使いたい
- `sed`, `awk`, `grep`, `python3` 前提の長い処理を流用したい
- Linux環境での再現性を確認したい

注意:

- `/mnt/c/...` 上の大量ファイル操作は遅いことがある
- Windows側エディタとWSL側で同時編集しない
- WSL側PythonとWindows側Conda Pythonは別環境

基本方針:

```text
普段は Windows Conda。
Ubuntuのシェル資産をそのまま使う時だけ WSL。
```

## 14. 生成AIに読ませる時の指示例

生成AIに作業を頼む時は、次のように指示するとよいです。

```text
Windows新規環境セットアップ簡易指南_Esperanto_HTML.md を読んで、
このWindows環境では esperanto-html Conda環境のPythonを使ってください。
裸の python/python3 は使わず、検証前に PYTHONIOENCODING=utf-8 を設定してください。
エスペラントルビHTML修正ガイド260328.txt に従い、
語根分解ミス・注釈漏れ・固有名詞タグ漏れを優先して確認してください。
ruby_css_verifier.py は --fix --margin 0.05 で実行してください。
```

## 15. まとめ

新しいWindows環境では、次だけ守ればかなり安定します。

1. Miniforgeを入れる
2. `esperanto-html` Conda環境を作る
3. Pythonはフルパスで明示する
4. `$env:PYTHONIOENCODING='utf-8'` を指定する
5. 日本語パスは引用符と `-LiteralPath`
6. `rg` は対象HTMLを明示する
7. `ruby_css_verifier.py --fix --margin 0.05` を使う
8. 抽出済みEsperantoテキストがあれば、原文復元一致を確認する
9. 最後にブラウザで目視確認する
10. Ubuntuのbash資産が必要な時だけWSLを使う
