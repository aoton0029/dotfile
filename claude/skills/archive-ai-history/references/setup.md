# 初回セットアップ

デバイスごとに1回だけ行う。2台目以降は「既存リポジトリを clone する」の手順になる。

## 0. 前提の確認

ユーザーに確認する:

- アーカイブ先リポジトリを **これから作る** のか、**既にある** のか
- リモートを持つか（GitHub private / 自前 / ローカルのみ）
- 置き場所（既定は `~/ai-history`。変える場合は環境変数 `AI_HISTORY_REPO`）

**リモートを持つ場合、private であることが絶対条件。** public のリポジトリを
指定された場合は理由を説明して断る。

## 1. 新規に作る場合

```
python <script> setup --remote git@github.com:<user>/ai-history.git
```

`--remote` は省略可（ローカルのみで運用する場合）。
以下が作られる:

```
~/ai-history/
├── README.md
├── .gitignore              # .archive-report/ を除外
├── .archive-config.json    # マスク・除外設定
├── index/
└── .state/
```

出力の `visibility` を確認する:

- `private` → そのまま進んでよい
- `no-remote (ローカルのみ)` → 問題ない
- `public` → **中止**。private にしてもらう
- `unknown` → `gh` で確認できなかった。ユーザーに private かどうか直接確認する

GitHub にリポジトリごと新規作成する場合は、先に次を実行してもらう:

```
gh repo create <user>/ai-history --private
```

## 2. 既存リポジトリがある2台目以降

```
git clone <url> ~/ai-history
```

clone するだけでよい。`.state/<device-id>.json` はデバイスごとに分かれるので、
このデバイス用のファイルが無ければ初回 `sync` 時に自動生成される。

## 3. 設定の初期調整

`~/ai-history/.archive-config.json` を開き、ユーザーと相談して埋める。

```json
{
  "exclude_projects": ["work-", "client"],
  "extra_patterns": [
    { "pattern": "(?i)\\bacme-internal\\b", "replacement": "<COMPANY>" }
  ],
  "mask_hosts": ["internal.example.co.jp"],
  "secret_hit_threshold": 40,
  "auto_push": false
}
```

特に `exclude_projects` は最初に決めておく価値がある。
業務リポジトリで作業したセッションは、マスクしても社内固有の文脈が残るため
そもそも取り込まないほうが安全。

正規表現は `~/.claude/projects/` のディレクトリ名（例
`c--Users-xxx-Documents-work-secret-app`）と、そこから導出した
プロジェクト slug の両方に対して照合される。

## 4. 動作確認

```
python <script> sync --dry-run --since 7d
```

サマリの `scanned` / `written` を確認し、
`~/ai-history/.archive-report/preview.txt` を**ユーザー自身に**開いてもらう。
マスクが効いているか、残したくない情報が通っていないかを目で見て判断してもらう。

問題なければ本実行する。

```
python <script> sync
```

初回はセッション数が多く時間がかかる。`--since 30d` などで区切ってもよい。

## 5. 定期実行（任意）

ユーザーが希望する場合のみ設定する。

**Windows (タスクスケジューラ)**

```
schtasks /create /tn "ai-history-sync" /tr "python C:\path\to\archive_ai_history.py sync --push" /sc daily /st 23:00
```

**Linux / WSL (cron)**

```
0 23 * * * python3 ~/Documents/dotfile/scripts/archive_ai_history.py sync --push
```

定期実行するなら `.archive-config.json` の `auto_push` を `true` にして
`--push` を省略してもよい。ただし自動 push はマスク漏れが即確定するため、
**private であることを再確認してから**有効にする。
