# tech-notes Vault の場所と構造

この参照は `capture-knowledge` / `recall-knowledge` / `deepen-knowledge` /
`quiz-knowledge` の4スキル共通。

## Vault の場所を解決する

1. 環境変数 `TECH_NOTES` があればそのパス
2. なければ `~/tech-notes`
3. どちらも存在しなければ、**勝手に作らず**パスを尋ねる

見つけた Vault ルートを基準に、以下の相対パスだけを使う。

## 構造

```
<vault>/
  MOC/            分野ごとの入口ノート。中身は Dataview クエリ1つだけ
  knowledge/      技術そのものの知識。フラット（サブフォルダを作らない）
  decisions/      実プロジェクトでの選択記録 (ADR)。ファイル名は "YYYY-MM-DD <題>"
  templates/      Obsidian コアプラグイン「テンプレート」用
  attachments/
```

### knowledge/ はフラット

分類はフォルダではなく **タグと MOC** で行う。カードは複数分野にまたがるが
フォルダは1つしか選べないため。分野別サブフォルダを作らないこと。

代償として **ファイル名は Vault 全体で一意**である必要がある
（`[[wikilink]]` は basename で解決されるため、重複はリンク解決の事故になる）。
新規作成前に必ず全体の同名チェックをする。

### knowledge/ と decisions/ の役割

- `decisions/` は**一回性**。「あのプロジェクトで、あの制約下で、こう決めた」
- `knowledge/` は**再利用可能**。decisions から一般化して抽出したもの

`decisions/` では**顧客名・システム名などの固有名詞を使わず、判断を左右した制約の形に
抜き出して書く**（「A社の受注基盤」ではなく「日次100万件の更新がある既存テーブル」）。
秘匿目的ではなく、制約の形で書けばそのまま `knowledge/` へ昇格できるため。
固有名詞を消すと判断が追えなくなる箇所だけは元の記述を残してよい。

decision を書いたら知識として持ち出せる部分を knowledge に昇格させ、
knowledge 側からは根拠となった decision へ `[[...]]` を張る。

## MOC ノート

該当分野の MOC が無ければ作る。中身は Dataview クエリだけでよい
（一覧を手でメンテするファイルは作らない）。

````markdown
# concurrency

```dataview
TABLE summary AS "一言で", confidence AS "確信度", updated AS "更新"
FROM "knowledge" AND #concurrency
SORT updated DESC
```
````

Dataview は人間が Obsidian で見るとき専用。AI 側はクエリを実行できないので、
検索は常に frontmatter を直接読む前提で行う。
