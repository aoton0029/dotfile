# 共通の作業ルール

## ドキュメントには図を置く

構造・流れ・状態・関係を説明するときは、依頼に「図」と書かれていなくても Mermaid 図を添える。
判断は依頼の文言ではなく書く内容で決める。

- 「A が B を経由して C を呼ぶ」→ `flowchart` + `subgraph`
- 「まず〜し、次に〜する」→ `sequenceDiagram`
- 「〜なら〜、失敗したら〜」→ `flowchart TD`
- 「〜から〜に変わる」→ `stateDiagram-v2`
- 「〜は〜を複数持つ」→ `erDiagram`

この形の文を3つ以上書きそうになったら図に替える。順序は **図 → 読み方3行 → 補足文**。
文章だけでよいのは、判断理由とトレードオフ、および分岐の無い直列手順。

設計書・仕様書を作るときは `docs-design` スキルを使う。図の描き方は
`~/.claude/skills/docs-design/references/diagram-guide.md`。

