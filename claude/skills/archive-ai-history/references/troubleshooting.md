# サマリの読み方と対処

`sync` の出力例:

```
mode      : apply
repo      : C:\Users\xxx\ai-history
scanned   : 312
written   : 4
skipped   : done=305 excluded=2 empty=0 secretful=1 residue=0 failed=0
committed : True
pushed    : False
report    : C:\Users\xxx\ai-history\.archive-report\last-run.txt
```

`written` が実際に追加された件数。`skipped` の内訳ごとに意味が違う。

## skipped の内訳

### `done`

取り込み済み。正常。毎回ほとんどがこれになる。

### `excluded`

`.archive-config.json` の `exclude_projects` にマッチした。設定どおりなら正常。
意図しないプロジェクトが落ちている場合は正規表現が広すぎる。

### `empty`

パースできる行が1行も無かった。空セッションや壊れたファイル。通常は無視してよい。

### `secretful`

秘匿系のマスクが `secret_hit_threshold`（既定40）を超えたため、
**安全側に倒して取り込みを見送った**。

`.env` を読んだ、認証情報を大量に扱った、といったセッションで起きる。
対処は、閾値を上げるのではなく:

1. どのプロジェクトのセッションかを `.archive-report/last-run.txt` で確認する
   （ファイルパスとセッションIDのみが書かれている。**中身は開かない**）
2. そのプロジェクトを `exclude_projects` に追加することをユーザーに提案する
3. どうしても取り込みたい場合のみ、ユーザーの判断で閾値を上げる

### `residue`

マスク後の再スキャンで秘匿パターンが残っていた。**フェイルクローズが働いた状態**で、
そのセッションは書き出されていない。

マスク規則の取りこぼしを意味するので、閾値調整では解決しない。
`.archive-report/last-run.txt` で件数を確認し、
`exclude_projects` で外すか、`extra_patterns` の追加を検討する。
これが頻発する場合は `Masker` 側のルールに不備がある可能性が高い。

### `failed`

ファイルが読めなかった（ロック中・権限）。Claude Code や Codex を実行中の
セッションで起きることがある。次回の `sync` で拾われるので通常は放置でよい。

## commit / push

### `committed: False` なのに `written` が 0 でない

git のコミットに失敗している。`git -C <repo> status` を確認する。
rebase 中断などで作業ツリーが汚れている可能性がある。

### `pushed: False`

`--push` も `auto_push` も指定していなければ正常（既定は commit 止まり）。
指定したのに `False` の場合は `.archive-report/last-run.txt` の末尾に
push のエラーが記録されている。

## エラー終了

### `ERROR: アーカイブリポジトリが未初期化`

`setup` を先に実行する。[setup.md](setup.md) を参照。

### `ERROR: アーカイブ先が public です`

意図的に public にしているのでなければ private に変更してもらう。
このチェックは外さない。

### `ERROR: pull に失敗しました`

別デバイスからの push と競合している。`git -C <repo> status` で状態を確認し、
コンフリクトを解消してもらう。

`.state/` と `index/` はデバイスごとにファイルを分けているため
通常は競合しないが、`.archive-config.json` を複数デバイスで同時に編集すると
競合しうる。その場合は手動でマージする。
