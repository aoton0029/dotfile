<INSTRUCTIONS>
<!-- codex のソース読み取り時は UTF-8 で読み込むこと。 -->

Always read source files as UTF-8. If encoding looks wrong, re-read with UTF-8 explicitly.

<!-- 設計書・仕様書・技術メモは図を主役にすること。 -->

When a document explains structure, flow, state, or relationships, include Mermaid diagrams
even if the user did not ask for them. Decide from the content, not the wording.

- "A calls C through B" -> `flowchart` + `subgraph`
- "first X, then Y" -> `sequenceDiagram`
- "if X, on failure Z" -> `flowchart TD`
- "moves from X to Y" -> `stateDiagram-v2`
- "X has many Y" -> `erDiagram`

About to write three or more such sentences? Draw the diagram instead.
Order: diagram -> at most 3 lines on how to read it -> prose.

Under 15 nodes. Label every arrow. Mark external boundaries with `subgraph`. Include one
failure path in sequence diagrams. ASCII node IDs, Japanese only in display labels.

Prose alone is fine only for reasoning and trade-offs, and for flows with no branching.
</INSTRUCTIONS>
