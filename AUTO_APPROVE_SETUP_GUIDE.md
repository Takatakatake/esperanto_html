# Claude Code & Codex 自動承認設定ガイド

**最終更新**: 2025年12月25日 07:00 JST
**目的**: 全ての操作を確認なしで自動実行するための設定

---

## 1. Claude Code 設定

### 1.1 設定ファイルの場所と優先順位

| 優先度 | ファイル | 用途 |
|:------:|---------|------|
| 高 | `~/.claude/settings.local.json` | ローカル設定（優先適用） |
| 中 | `~/.claude/settings.json` | 共有設定 |
| - | `~/.claude-pro1/settings.json` | `claudea` コマンド用（Opus） |
| - | `~/.claude-pro2/settings.json` | `claudem` コマンド用（Opus） |

### 1.2 現在の設定内容

#### ~/.claude/settings.json

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions",
    "allow": [
      "Bash",
      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep",
      "WebFetch",
      "WebSearch",
      "Task",
      "TodoWrite",
      "NotebookEdit",
      "LSP",
      "mcp__*",
      "AskUserQuestion",
      "EnterPlanMode",
      "ExitPlanMode"
    ],
    "deny": []
  }
}
```

#### ~/.claude/settings.local.json（優先）

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions",
    "allow": [
      "Bash",
      "Read",
      "Write",
      "Edit",
      "Glob",
      "Grep",
      "WebFetch",
      "WebSearch",
      "TodoWrite",
      "Task",
      "NotebookEdit",
      "LSP",
      "mcp__*",
      "AskUserQuestion",
      "EnterPlanMode",
      "ExitPlanMode"
    ],
    "deny": []
  }
}
```

#### ~/.claude-pro1/settings.json & ~/.claude-pro2/settings.json

```json
{
  "model": "opus",
  "permissions": {
    "defaultMode": "bypassPermissions",
    "allow": [
      "Bash",
      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep",
      "WebFetch",
      "WebSearch",
      "Task",
      "TodoWrite",
      "NotebookEdit",
      "LSP",
      "mcp__*",
      "AskUserQuestion",
      "EnterPlanMode",
      "ExitPlanMode"
    ],
    "deny": []
  }
}
```

### 1.3 設定項目の説明

| 項目 | 値 | 説明 |
|------|-----|------|
| `defaultMode` | `"bypassPermissions"` | 全ての確認プロンプトをスキップ |
| `allow` | ツール配列 | 自動許可するツール一覧 |
| `deny` | `[]` | 拒否するツール（現在は空） |

### 1.4 defaultMode の選択肢

| 値 | 動作 |
|----|------|
| `default` | 標準動作 - 各ツール使用時に確認 |
| `acceptEdits` | ファイル編集のみ自動承認 |
| `plan` | Plan Mode - 分析のみ、変更不可 |
| `bypassPermissions` | **全ての確認をスキップ** |

### 1.5 許可されるツール一覧

| ツール | 説明 |
|--------|------|
| `Bash` | シェルコマンド実行（全コマンド許可） |
| `Read` | ファイル読み取り |
| `Edit` | ファイル編集 |
| `Write` | ファイル作成 |
| `Glob` | ファイルパターン検索 |
| `Grep` | ファイル内容検索 |
| `WebFetch` | Webページ取得 |
| `WebSearch` | Web検索 |
| `Task` | サブエージェント起動 |
| `TodoWrite` | タスク管理 |
| `NotebookEdit` | Jupyter Notebook編集 |
| `LSP` | 言語サーバープロトコル |
| `mcp__*` | 全てのMCPツール |
| `AskUserQuestion` | ユーザーへの質問 |
| `EnterPlanMode` | プランモード開始 |
| `ExitPlanMode` | プランモード終了 |

### 1.6 Bashツールの記法

| 記法 | 意味 |
|------|------|
| `Bash` | 全てのコマンドを許可 |
| `Bash(git:*)` | gitで始まるコマンドを許可 |
| `Bash(npm install)` | 特定コマンドのみ許可 |

**注意**: `Bash(*)` は無効な記法です。全コマンド許可には `Bash` を使用。

---

## 2. Codex 設定

### 2.1 設定ファイルの場所

```
~/.codex/config.toml
```

### 2.2 現在の設定内容

```toml
model = "gpt-5.2-codex"
model_reasoning_effort = "xhigh"

# Maximum freedom settings - no confirmation prompts
approval_policy = "never"
sandbox = "danger-full-access"
sandbox_permissions = [
  "disk-full-read-access",
  "disk-full-write-access"
]

[projects."/home/yt"]
trust_level = "trusted"

[projects."/home/yt/ダウンロード"]
trust_level = "trusted"

[projects."/home/yt/ドキュメント"]
trust_level = "trusted"

[notice]
hide_full_access_warning = true
hide_rate_limit_model_nudge = true
```

### 2.3 主要設定項目

| 項目 | 値 | 説明 |
|------|-----|------|
| `approval_policy` | `"never"` | 承認を一切求めない |
| `sandbox` | `"danger-full-access"` | サンドボックスなし |
| `sandbox_permissions` | 全読み書き | ディスク全体へのアクセス |
| `trust_level` | `"trusted"` | プロジェクトを信頼 |

### 2.4 approval_policy / -a オプションの選択肢

| 値 | 動作 |
|----|------|
| `untrusted` | 信頼されたコマンドのみ自動実行 |
| `on-failure` | 失敗時のみ承認を求める |
| `on-request` | モデルが判断して承認を求める |
| `never` | **承認を一切求めない** |
| `full-auto` | 自動実行（on-request + sandbox） |

### 2.5 sandbox / -s オプションの選択肢

| 値 | 動作 |
|----|------|
| `read-only` | 読み取りのみ |
| `workspace-write` | ワークスペース内のみ書き込み可 |
| `danger-full-access` | **全アクセス許可（サンドボックスなし）** |

---

## 3. シェルエイリアス

### 3.1 ~/.bashrc の現在の設定

```bash
# Claude Code アカウント切り替え（Opusモデル用）
alias claudea='CLAUDE_CONFIG_DIR=~/.claude-pro1 claude'
alias claudem='CLAUDE_CONFIG_DIR=~/.claude-pro2 claude'

# Claude Code & Codex - 完全自動モード
alias claudeauto='claude --dangerously-skip-permissions'
alias codexauto='codex --dangerously-bypass-approvals-and-sandbox'
alias codexfull='codex --full-auto -s danger-full-access -a never'
```

### 3.2 エイリアスの説明

| エイリアス | 説明 |
|-----------|------|
| `claude` | 通常起動（settings.jsonで自動承認済み） |
| `claudea` | ~/.claude-pro1設定を使用（Opusモデル） |
| `claudem` | ~/.claude-pro2設定を使用（Opusモデル） |
| `claudeauto` | 全権限チェックを完全スキップ |
| `codex` | 通常起動（config.tomlで自動承認済み） |
| `codexauto` | 全確認スキップ＋サンドボックス無効 |
| `codexfull` | フルオートモード＋全権限アクセス |

---

## 4. コマンドラインオプション

### 4.1 Claude Code

```bash
# 全権限スキップ
claude --dangerously-skip-permissions

# 権限モード指定
claude --permission-mode bypassPermissions

# 特定ツールのみ許可
claude --allowedTools "Bash(git:*)" "Read" "Edit"
```

### 4.2 Codex

```bash
# 全自動実行
codex --full-auto

# 承認なし + サンドボックスなし（最も自由）
codex --dangerously-bypass-approvals-and-sandbox

# 個別指定
codex -a never -s danger-full-access

# 設定値を上書き
codex -c 'approval_policy="never"'
```

---

## 5. 設定の反映方法

### 5.1 エイリアスの反映

```bash
source ~/.bashrc
```

### 5.2 Claude Code

- **新しいセッションを開始**すると自動的に反映
- 現在のセッションには反映されない（`/exit` で終了後、再起動）

### 5.3 Codex

- 新しいセッションを開始すると自動的に反映

---

## 6. 設定の確認コマンド

### 6.1 Claude Code

```bash
# 設定ファイルの確認
cat ~/.claude/settings.json
cat ~/.claude/settings.local.json

# defaultModeの確認
grep '"defaultMode"' ~/.claude/settings.json ~/.claude/settings.local.json

# セッション内で確認
/permissions
```

### 6.2 Codex

```bash
# 設定ファイルの確認
cat ~/.codex/config.toml

# 主要設定の確認
grep -E "^(approval_policy|sandbox)" ~/.codex/config.toml

# ヘルプで利用可能オプション確認
codex --help
```

### 6.3 エイリアスの確認

```bash
alias | grep -E "claude|codex"
```

---

## 7. セキュリティに関する注意

### 7.1 リスク

この設定は利便性を最優先にしており、以下のリスクがあります：

1. **意図しないファイル変更**: AIが誤ってファイルを削除・変更する可能性
2. **危険なコマンド実行**: 全てのコマンドが自動実行される
3. **ネットワークアクセス**: curl/wget等が自動実行される

### 7.2 推奨事項

1. **重要なプロジェクトはGit管理**: 変更を追跡・復元可能に
2. **定期的なバックアップ**: 重要なファイルは別途バックアップ
3. **deny リストの活用**: 必要に応じて危険なコマンドを拒否

### 7.3 deny リストの設定例（オプション）

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions",
    "allow": ["..."],
    "deny": [
      "Read(~/.ssh/id_*)",
      "Read(~/.ssh/*_key)",
      "Read(~/.aws/credentials)",
      "Bash(rm -rf /:*)",
      "Bash(sudo rm -rf:*)",
      "Bash(:(){ :|:&};:)",
      "Bash(dd if=/dev/zero of=/dev/sda:*)",
      "Bash(mkfs:*)"
    ]
  }
}
```

---

## 8. トラブルシューティング

### 8.1 設定が反映されない場合

1. ファイルパスの確認
2. JSON/TOMLの構文エラーチェック
3. Claude Code/Codex の再起動（`/exit` → 再起動）

### 8.2 JSON構文チェック

```bash
python3 -m json.tool ~/.claude/settings.json
python3 -m json.tool ~/.claude/settings.local.json
```

### 8.3 TOML構文チェック

```bash
python3 -c "import tomllib; print(tomllib.load(open('$HOME/.codex/config.toml', 'rb')))"
```

### 8.4 エイリアスが効かない場合

```bash
# bashrc を再読み込み
source ~/.bashrc

# または新しいターミナルを開く
```

### 8.5 よくあるエラー

| エラー | 原因 | 解決策 |
|--------|------|--------|
| `Bash(*)` エラー | 無効な記法 | `Bash` に変更 |
| JSON parse error | 構文エラー | `python3 -m json.tool` で確認 |
| 設定が効かない | ファイル名間違い | `settings.local.json` を確認 |

---

## 9. 設定のリセット方法

### 9.1 Claude Code をデフォルトに戻す

```bash
# 設定をクリア
echo '{}' > ~/.claude/settings.json
echo '{}' > ~/.claude/settings.local.json
```

### 9.2 Codex の自動承認を無効化

```bash
# config.toml から該当行を削除
sed -i '/approval_policy/d' ~/.codex/config.toml
sed -i '/^sandbox/d' ~/.codex/config.toml
```

### 9.3 エイリアスを無効化

```bash
# ~/.bashrc から該当行を削除またはコメントアウト
# alias claude=... の行を # でコメントアウト
```

---

## 10. クイックリファレンス

### 完全自動モードで起動

```bash
# Claude Code（設定済みなのでそのまま）
claude

# Codex（設定済みなのでそのまま）
codex
```

### 一時的に標準モードで起動

```bash
# Claude Code（エイリアスをバイパス）
command claude

# Codex（設定を上書き）
codex -a untrusted -s read-only
```

### 設定確認ワンライナー

```bash
echo "=== Claude ===" && grep '"defaultMode"' ~/.claude/settings*.json 2>/dev/null && echo "=== Codex ===" && grep -E "^(approval_policy|sandbox)" ~/.codex/config.toml
```

---

## 変更履歴

| 日時 | 内容 |
|------|------|
| 2025-12-25 07:00 | 実際の設定に完全同期、claude-pro1/pro2作成 |
| 2025-12-25 06:50 | `Bash(*)` を `Bash` に修正、エラー対処法追加 |
| 2025-12-25 06:45 | 初版作成 |

---

*このドキュメントは実際の設定ファイルに基づいて作成されました。*
