# マスクルールと設定

方針は **「疑わしきはマスク」**。読めなくなるほうが、漏らすよりまし。

マスクは JSONL の各行をパースし、**全ての文字列値**に再帰適用される。
キー名は変換しない（構造を保つため）。

## 組み込みルール（適用順）

| # | 種別 | 置換後 | 検証対象 |
|---|---|---|---|
| 1 | `-----BEGIN ... PRIVATE KEY-----` ブロック | `<PRIVATE_KEY>` | ✓ |
| 2 | `*TOKEN/SECRET/PASSWORD/APIKEY/CREDENTIAL* = 値` | `KEY=<SECRET>` | ✓ |
| 3 | `sk-` / `ghp_` / `github_pat_` / `xox?-` / `AKIA` / `AIza` / `Bearer …` | `<SECRET>` | ✓ |
| 4 | メールアドレス | `<EMAIL>` | |
| 5 | ホームディレクトリ（Windows/WSL/macOS/Linux） | `<HOME>` | |
| 6 | ユーザー名の単独出現（`$USERNAME` / `$USER` から導出） | `<USER>` | |
| 7 | 40文字以上のhex / 48文字以上のbase64 | `<SECRET>` | ✓ |
| 8 | グローバルIPv4（プライベート帯は除く） | `<IP>` | |
| 9 | `mask_hosts` に列挙したホスト | `<HOST>` | |
| 10 | `extra_patterns` の各パターン | 指定の置換先 | |

「検証対象」に ✓ が付くルールは、**マスク後にもう一度スキャンされる**。
1件でも残っていればそのセッションは書き出されない（フェイルクローズ）。

## 間引き（既定。`--full` で無効化）

- `thinking` / `redacted_thinking` ブロック → `{"omitted": true}`
- 画像・添付の base64 → `{"type":"image","omitted":true}`
- 2KB を超える文字列 → 先頭2KB + `<TRUNCATED n bytes>`

「何をやったかが後から分かる粒度」を狙っており、
コードの全文や巨大なコマンド出力は残らない。
完全な記録が要るセッションだけ `--full --since 1d` などで別途取り込む。

## 設定項目

アーカイブリポジトリ直下の `.archive-config.json`。

### `exclude_projects`

正規表現の配列。マッチしたプロジェクトは**そもそも取り込まない**。
照合先は `~/.claude/projects/` のディレクトリ名と、そこから導出した slug の両方。

```json
"exclude_projects": ["work-", "^client", "secret"]
```

業務・受託リポジトリはここに入れておくのが安全。マスクは秘密鍵やトークンは
落とせるが、「どの顧客の何をやっているか」という文脈は落とせない。

### `extra_patterns`

追加のマスク規則。文字列なら `<REDACTED>` に、オブジェクトなら任意の置換先に。

```json
"extra_patterns": [
  "\\bPROJ-\\d{4,}\\b",
  { "pattern": "(?i)\\bacme\\b", "replacement": "<COMPANY>" }
]
```

Python の `re` 構文。JSON なのでバックスラッシュは二重にする。

### `mask_hosts`

社内ドメインなど、名前自体を隠したいホスト名の配列。

### `secret_hit_threshold`

1セッション中の秘匿系ヒット数の上限（既定 40）。
これを超えたセッションは「マスクで潰しきれていない疑いが強い」と判断して
**取り込まずスキップ**する。

`.env` を大量に読んだセッションなどで発火する。頻発する場合は、
閾値を上げるのではなく `exclude_projects` で当該プロジェクトを外すほうがよい。

### `auto_push`

`true` にすると `--push` なしでも push する。定期実行向け。
アーカイブ先が private であることを確認してから有効にする。

## ルールを増やしたくなったら

まず `extra_patterns` で足りるか検討する。組み込みルール自体の変更が要る場合は
スキルディレクトリ直下の `scripts/archive_ai_history.py` の `Masker.__init__` を編集する。
検証対象に加えるには `_add(..., secret=True)` を指定する。

**既に取り込み済みの履歴は遡ってマスクし直されない。**
ルールを追加した場合、過去分に同じ情報が残っている可能性がある点に注意する。
遡って適用したい場合は、該当ファイルを削除して `.state/<device>.json` の
`ingested` から該当 session_id を消し、再 `sync` する。
