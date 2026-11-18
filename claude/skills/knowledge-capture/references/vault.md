# KnowledgeVault の場所と、スキルが使う場所

この参照は `knowledge-capture` / `knowledge-recall` / `knowledge-deepen` /
`knowledge-quiz` の4スキル共通。

Vault の構成と規約の正本は Vault 自身にある。このファイルは、Vault の場所の見つけ方と、
4スキルが Vault のどこを使うかだけを書く。**作業の前に必ず Vault の `AGENTS.md` と、
書く space の `spaces/<space>/RULES.md` を読む。** この参照と食い違ったら Vault 側に従う。

## Vault の場所を解決する

Vault は GitHub の `KnowledgeVault` リポジトリで、クローン先はマシンによって違う。次の順で解決する。

1. **スキル引数でパスが渡されていればそれ**（`/knowledge-recall --vault <path> <テーマ>` など）。
2. **`~/.claude/knowledge-vault-path`** — 1行目に Vault ルートの絶対パスだけを書いたファイル。
3. どちらも無ければ **`AskUserQuestion` でパスを尋ね、答えを 2 のファイルに書き出す**。

解決したパスは使う前に、**ディレクトリが実在し、`AGENTS.md` と `spaces/` を含むか**を確かめる。
含まないなら Vault ではないので、**勝手にディレクトリを作らず**その旨を伝えて 3 に戻る。
`~/.claude/knowledge-vault-path` の内容が壊れていた場合も同じ（黙って作り直さず、指摘してから聞く）。

## space

書く先は `spaces/<space>/` の下だけ。space は `AGENTS.md` の「space」の表にある**既定の space**
（今は `main`）を使う。ユーザーが別の space を指定したときだけ変える。
以下のパスは `<space>` = `main` の例で書く。

## 4スキルが使う場所

| スキルの言葉 | Vault の場所 | 見分け方 |
|---|---|---|
| 知識カード（再利用できる原理） | `spaces/main/encyclopedia/` | frontmatter の `type: tech` |
| 判断の記録（一回性の選択） | `spaces/main/syntheses/` | `type: decision`、ファイル名は `YYYY-MM-DD <題>` |
| 分野 | frontmatter の `categories`（複数可） | 語は `_meta/taxonomy.md` |
| 分野の入口（MOC） | `spaces/main/maps/<category>.md` | `type: map` |
| 人に確認を求める提案 | `spaces/main/_review/` | 未登録の category、`owner: human` のカードへの変更など |

- `encyclopedia/` は**フラット**。カテゴリのサブフォルダは作らない。分野は `categories` だけで表す。
  分類を変えてもファイルが動かないので、リンクが壊れない。
- `encyclopedia/` には `type: term`（用語の定義）や `person` なども並ぶ。
  カードを探すときは `type: tech` で絞る。recall では `term` と `syntheses/` も検索に含めてよい。
- テンプレートは `_meta/templates/main/tech.md`（カード）、`decision.md`（判断の記録）、`map.md`（入口）。
  新しく作るときはテンプレートを読み、`{{title}}` と `{{date:YYYY-MM-DD}}` を自分で埋める。

## 書いてはいけない場所

- `human/`、`_meta/`、`AGENTS.md`、`spaces/<space>/RULES.md`、`README.md`、`CLAUDE.md` は読むだけ。
- `owner: human` のノートは書き換えない。変えたいときは `_review/` に差分を提案する。
- 既存のノートを改名・移動・削除しない。

## 判断の記録とカードの関係

- `decision` は**一回性**。「あのプロジェクトで、あの制約下で、こう決めた」
- `tech` のカードは**再利用可能**。decision から一般化して取り出したもの

decision では**顧客名・システム名などの固有名詞を使わず、判断を左右した制約の形に
抜き出して書く**（「A社の受注基盤」ではなく「日次100万件の更新がある既存テーブル」）。
秘匿目的ではなく、制約の形で書けばそのままカードへ取り出せるため。
固有名詞を消すと判断が追えなくなる箇所だけは元の記述を残してよい。

decision を書いたら知識として持ち出せる部分をカードに取り出し、
カード側からは根拠となった decision へ `[[...]]` を張る。

## 入口（maps）

該当分野の `maps/<category>.md` が無ければ、テンプレート `map.md` から作る。
中身は Obsidian の Bases のクエリ（`base` のコードブロック）だけで、一覧を手で書かない。

Bases は人間が Obsidian で見るとき専用。AI 側はクエリを実行できないので、
検索は常に frontmatter を直接読む前提で行う。
