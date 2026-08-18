---
name: archive-ai-history
description: >
  複数デバイスのローカルにある Claude Code / Codex の会話履歴を、秘匿情報をマスクした上で
  private な git リポジトリに蓄積するスキル。「履歴をアーカイブして」「AI履歴を同期して」
  「会話ログをgitに上げて」「過去のセッションを検索して」といった依頼で使う。
  収集・マスク・検証・コミット・pushは全て scripts/archive_ai_history.py が行い、
  このスキルはその起動と、初回セットアップ・失敗時の原因説明・除外設定の提案だけを担う。
  履歴ファイル自体は絶対に読まない。
---

# AI履歴のアーカイブ

Claude Code と Codex のローカル履歴を、マスクした上でアーカイブリポジトリに溜める。

設計の詳細は dotfiles リポジトリの
[docs/ai-history-archive-design.md](../../../docs/ai-history-archive-design.md) を参照。

## 絶対に守ること

**`~/.claude/projects/` および `~/.codex/sessions/` 配下のファイルを
Read / Grep / cat / head などで開いてはならない。**
1セッションで数十万トークンになり、かつ未マスクの秘匿情報が
コンテキストに載る。これらの中身に触れる必要は一切ない。
参照が必要なときも必ず後述の `search` / `show` サブコマンド経由で扱う。

同様に、アーカイブリポジトリ配下の `claude/` `codex/` 以下の `.jsonl` も直接開かない。
`.archive-report/` の中身も原則開かない（ユーザーが自分で見るためのもの）。

## スクリプトの場所

dotfiles リポジトリの `scripts/archive_ai_history.py`。
このスキルは `~/.claude/skills` へのシンボリックリンク経由で読み込まれるため、
相対パスでは辿れないことがある。見つからない場合は
`~/Documents/dotfile/scripts/archive_ai_history.py` を試し、
それでも無ければユーザーに dotfiles リポジトリの場所を尋ねる。

## 通常の同期

```
python <script> sync
```

これだけで pull → 差分収集 → マスク → 検証 → commit まで完走する。
push まで行う場合は `--push` を付ける（既定では push しない）。

出力は10行程度のサマリだけが返る。これをそのままユーザーに要約して伝える。
`written` が取り込み件数、`skipped` の各項目が除外理由の内訳。

主なオプション:

| オプション | 用途 |
|---|---|
| `--dry-run` | 書き込まず、対象件数と `.archive-report/preview.txt` の生成のみ |
| `--since 7d` | 直近のぶんだけ（`7d` / `24h` / `2w`） |
| `--tool claude` | 片方のツールだけ |
| `--full` | 既定の間引き（thinking除去・2KB超の切り詰め）をせず保存 |
| `--push` | commit 後に push する |
| `--no-pull` | 先頭の `git pull --rebase` を省略 |

初めて実行するとき、あるいは設定を変えた直後は、
**まず `--dry-run` で流し、`.archive-report/preview.txt` をユーザー自身に
確認してもらってから** 本実行する。プレビューの中身はこちらで読まない。

## 失敗・スキップへの対応

サマリの `skipped` に 0 でない項目があれば、原因と対処をユーザーに伝える。
詳細は [references/troubleshooting.md](references/troubleshooting.md) を読む。

特に `secretful` / `residue` が出た場合は、そのセッションは**取り込まれていない**。
マスクで潰しきれない情報を含む可能性が高いので、
該当プロジェクトを `.archive-config.json` の `exclude_projects` に
追加することを提案する。

## 初回セットアップ

アーカイブリポジトリが未作成、または `sync` が「未初期化」で終了した場合に行う。
手順は [references/setup.md](references/setup.md) を読む。

## 過去の履歴を探す

```
python <script> search "<キーワード>"
python <script> show <session-id> --start 0 --end 40
```

`search` はインデックス（1セッション1行）だけを見るので安い。
`show` は本文を返すため、**ユーザーが特定のセッションを見たいと明示したときだけ**使い、
`--start` / `--end` で範囲を絞る。範囲指定なしで巨大なセッションを開かない。

## マスクルールを変える

アーカイブリポジトリの `.archive-config.json` を編集する。
項目の意味と追加パターンの書き方は
[references/masking.md](references/masking.md) を参照。

## やらないこと

- 履歴ファイルの中身を読むこと（上記のとおり禁止）
- マスク結果の良否を LLM が判断すること。判定はスクリプトの検証パスに任せ、
  最終的な目視はユーザーが行う
- アーカイブ先が public のときに実行すること。スクリプトが拒否するが、
  `unknown` と出た場合は private かどうかをユーザーに確認する
- 既にアーカイブ済みの履歴を消したり作り直したりすること。
  やり直したい場合は影響範囲をユーザーに提示してから
