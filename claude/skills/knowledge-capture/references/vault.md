# tech-notes Vault の場所と構造

この参照は `knowledge-capture` / `knowledge-recall` / `knowledge-deepen` /
`knowledge-quiz` の4スキル共通。

## Vault の場所を解決する

Vault は別リポジトリで、クローン先はマシンによって違う。次の順で解決する。

1. **スキル引数でパスが渡されていればそれ**（`/knowledge-recall --vault <path> <テーマ>` など）。
2. **`~/.claude/tech-notes-path`** — 1行目に Vault ルートの絶対パスだけを書いたファイル。
3. どちらも無ければ **`AskUserQuestion` でパスを尋ね、答えを 2 のファイルに書き出す**。

解決したパスは使う前に、**ディレクトリが実在し `knowledge/` を含むか**を確かめる。
含まないなら Vault ではないので、**勝手にディレクトリを作らず**その旨を伝えて 3 に戻る。
`~/.claude/tech-notes-path` の内容が壊れていた場合も同じ（黙って作り直さず、指摘してから聞く）。

見つけた Vault ルートを基準に、以下の相対パスだけを使う。

## 構造

```
<vault>/
  MOC/            分野ごとの入口ノート。中身は Dataview クエリ1つだけ
  knowledge/      技術そのものの知識。カテゴリごとのサブディレクトリに分類
    concurrency/
    storage/
    ...
  decisions/      実プロジェクトでの選択記録 (ADR)。フラット。ファイル名は "YYYY-MM-DD <題>"
  templates/      Obsidian コアプラグイン「テンプレート」用
  attachments/
```

### knowledge/ はカテゴリ別

カードは `knowledge/<カテゴリ>/<ノート名>.md` に置く。

- **カテゴリは主分野1つ**で決める。フォルダは1つしか選べないので、迷ったら
  「このカードを探しに行くとき最初に開く場所」を選ぶ
- **またがる分野は `tags` で表現する**。フォルダは主分野だけ、タグは複数。
  横断的な分類はタグと MOC の仕事で、フォルダはあくまで置き場所
- **カテゴリ名はタグ名・MOC 名と揃える**（英小文字の kebab-case。
  `knowledge/concurrency/` ↔ `#concurrency` ↔ `MOC/concurrency.md`）
- **新カテゴリを作るのは、そこに入るカードが3枚以上見込めるときだけ。**
  それ未満は既存の近いカテゴリに入れるか `knowledge/` 直下に置く。
  1枚しかないフォルダが並ぶと、分類が探索の役に立たなくなる

**ファイル名は Vault 全体で一意**である必要がある。フォルダを分けても
`[[wikilink]]` は basename で解決されるため、別カテゴリでも同名は事故になる。
新規作成前に必ず**全カテゴリ横断**で同名チェックをする。

検索・走査は常に `knowledge/` 以下を**再帰的に**行う（直下だけ見ない）。
Dataview の `FROM "knowledge"` もサブフォルダを含むので、MOC 側の変更は要らない。

既にフラットに置かれているカードは、まとめて移動しない。
`knowledge-deepen` などでそのカードを触ったついでに、該当カテゴリへ移す。

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
