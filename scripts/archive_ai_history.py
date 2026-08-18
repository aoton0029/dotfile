#!/usr/bin/env python3
"""ローカルの Claude Code / Codex 会話履歴をマスクしてアーカイブリポジトリに蓄積する。

標準ライブラリのみで動作する。LLM に本文を読ませないため、標準出力には
サマリのみを出し、明細は アーカイブリポジトリ/.archive-report/ に書き出す。

使い方:
    python archive_ai_history.py setup [--repo PATH] [--remote URL]
    python archive_ai_history.py sync  [--dry-run] [--since 7d] [--tool claude|codex]
                                       [--full] [--push] [--no-pull]
    python archive_ai_history.py search <query> [--limit 20]
    python archive_ai_history.py show <session-id> [--start N] [--end N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))

DEFAULT_REPO = Path.home() / "ai-history"
CONFIG_NAME = ".archive-config.json"
REPORT_DIR = ".archive-report"

# 保存時の既定の間引き閾値
MAX_STRING_BYTES = 2048
MAX_SUMMARY_LINES = 30

DEFAULT_CONFIG = {
    "exclude_projects": [],
    "extra_patterns": [],
    "mask_hosts": [],
    "secret_hit_threshold": 40,
    "auto_push": False,
}


# --------------------------------------------------------------------------
# マスク処理
# --------------------------------------------------------------------------

class Masker:
    """文字列から秘匿情報を落とす。「疑わしきはマスク」で運用する。"""

    def __init__(self, config: dict):
        self.hits = 0
        self.rules: list[tuple[re.Pattern, str, bool, bool]] = []

        user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        self.user = user

        # 1. 秘密鍵ブロック（最優先）
        self._add(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            "<PRIVATE_KEY>",
            flags=re.DOTALL,
            secret=True,
            strong=True,
        )
        # 2. KEY=VALUE 形式（.env など）
        self._add(
            r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|APIKEY|API_KEY|CREDENTIAL)"
            r"[A-Z0-9_]*)\s*[=:]\s*[\"']?(?!<SECRET>)[^\s\"',}]+",
            r"\1=<SECRET>",
            secret=True,
        )
        # 3. 既知のトークン書式
        self._add(r"\bsk-[A-Za-z0-9_\-]{16,}", "<SECRET>", secret=True)
        self._add(r"\bghp_[A-Za-z0-9]{20,}", "<SECRET>", secret=True)
        self._add(r"\bgithub_pat_[A-Za-z0-9_]{20,}", "<SECRET>", secret=True)
        self._add(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}", "<SECRET>", secret=True)
        self._add(r"\bAKIA[0-9A-Z]{16}\b", "<SECRET>", secret=True)
        self._add(r"\bAIza[0-9A-Za-z_\-]{30,}", "<SECRET>", secret=True)
        self._add(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{20,}", "Bearer <SECRET>", secret=True, strong=True)
        # 4. メールアドレス
        self._add(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "<EMAIL>")
        # 5. ホームディレクトリ（ユーザー名より先に潰す）
        self._add(r"(?i)[A-Z]:\\\\Users\\\\[^\\\\\"'\s]+", "<HOME>")
        self._add(r"(?i)[A-Z]:\\Users\\[^\\\"'\s]+", "<HOME>")
        self._add(r"(?i)/[a-z]/Users/[^/\"'\s]+", "<HOME>")
        self._add(r"/home/[^/\"'\s]+", "<HOME>")
        self._add(r"/Users/[^/\"'\s]+", "<HOME>")
        # 6. ユーザー名の単独出現
        if user:
            self._add(r"(?i)\b" + re.escape(user) + r"\b", "<USER>")
        # 7. 高エントロピー文字列（コミットハッシュ等の誤検出が多いので閾値には数えない）
        self._add(r"\b[A-Fa-f0-9]{40,}\b", "<SECRET>", secret=True, strong=False)
        self._add(r"\b[A-Za-z0-9+/]{48,}={0,2}\b", "<SECRET>", secret=True, strong=False)
        # 8. グローバルIP
        self._add(r"\b(?!10\.|127\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|0\.)"
                  r"(?:\d{1,3}\.){3}\d{1,3}\b", "<IP>")
        # 9. 設定で指定されたホスト
        for host in config.get("mask_hosts", []):
            self._add(r"(?i)\b" + re.escape(host) + r"\b", "<HOST>")
        # 10. 設定で指定された追加パターン
        for entry in config.get("extra_patterns", []):
            if isinstance(entry, str):
                self._add(entry, "<REDACTED>")
            else:
                self._add(entry["pattern"], entry.get("replacement", "<REDACTED>"))

    def _add(self, pattern: str, repl: str, flags: int = 0,
             secret: bool = False, strong: bool | None = None) -> None:
        """secret: 検証パスの対象 / strong: 閾値カウントの対象。

        strong を省略すると secret と同値になる。高エントロピー判定のように
        誤検出しやすいルールは strong=False を明示し、閾値を押し上げないようにする。
        """
        if strong is None:
            strong = secret
        self.rules.append((re.compile(pattern, flags), repl, secret, strong))

    def mask(self, text: str) -> str:
        for regex, repl, _secret, strong in self.rules:
            text, n = regex.subn(repl, text)
            if n and strong:
                self.hits += n
        return text

    def residue(self, text: str) -> int:
        """マスク後に秘匿パターンが残っていないかを数える（フェイルクローズ用）。"""
        count = 0
        for regex, _repl, secret, _strong in self.rules:
            if secret:
                count += len(regex.findall(text))
        return count


# --------------------------------------------------------------------------
# 間引き処理
# --------------------------------------------------------------------------

def trim(node, full: bool):
    """thinking / 巨大な文字列 / 添付の base64 を落とす。形式に依存しない再帰処理。"""
    if isinstance(node, dict):
        if not full:
            if node.get("type") in ("thinking", "redacted_thinking"):
                return {"type": node.get("type"), "omitted": True}
            source = node.get("source")
            is_attachment = isinstance(source, dict) and "data" in source
            if node.get("type") == "image" or is_attachment:
                return {"type": "image", "omitted": True}
        return {k: trim(v, full) for k, v in node.items()}
    if isinstance(node, list):
        return [trim(v, full) for v in node]
    if isinstance(node, str) and not full:
        raw = node.encode("utf-8", "ignore")
        if len(raw) > MAX_STRING_BYTES:
            head = raw[:MAX_STRING_BYTES].decode("utf-8", "ignore")
            return f"{head}\n<TRUNCATED {len(raw)} bytes>"
    return node


def mask_tree(node, masker: Masker):
    """全ての文字列値にマスクを適用する。キー名は変換しない。"""
    if isinstance(node, dict):
        return {k: mask_tree(v, masker) for k, v in node.items()}
    if isinstance(node, list):
        return [mask_tree(v, masker) for v in node]
    if isinstance(node, str):
        return masker.mask(node)
    return node


# --------------------------------------------------------------------------
# 収集
# --------------------------------------------------------------------------

def device_id() -> str:
    name = os.environ.get("AI_HISTORY_DEVICE") or socket.gethostname()
    return re.sub(r"[^a-z0-9\-]", "-", name.lower()).strip("-") or "unknown"


def hash6(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:6]


def project_slug(encoded_cwd: str, mapping: dict) -> str:
    tokens = [t for t in encoded_cwd.split("-") if t]
    last = tokens[-1] if tokens else ""
    last = re.sub(r"[^A-Za-z0-9_.]", "", last)
    digest = hash6(encoded_cwd)
    if not last or last.lower() in {"users", "documents", "home", "src", "repos"}:
        return f"proj-{digest}"
    known = mapping.get(last)
    if known is None:
        mapping[last] = digest
        return last
    return last if known == digest else f"{last}-{digest}"


def discover(tool: str | None, since: datetime | None) -> list[dict]:
    """取り込み候補のセッションファイルを列挙する。"""
    found = []
    if tool in (None, "claude"):
        root = Path.home() / ".claude" / "projects"
        for path in root.glob("*/*.jsonl"):
            found.append({"tool": "claude", "path": path, "group": path.parent.name})
    if tool in (None, "codex"):
        root = Path.home() / ".codex" / "sessions"
        for path in root.glob("*/*/*/*.jsonl"):
            found.append({"tool": "codex", "path": path, "group": None})
    if since:
        cutoff = since.timestamp()
        found = [f for f in found if f["path"].stat().st_mtime >= cutoff]
    return sorted(found, key=lambda f: f["path"].stat().st_mtime)


def session_id_of(entry: dict) -> str:
    stem = entry["path"].stem
    m = re.search(r"([0-9a-f]{8})[0-9a-f-]*$", stem)
    return m.group(1) if m else hash6(stem)


def first_text(obj) -> str | None:
    """最初のユーザー発話らしき文字列を拾う。形式差を吸収するため緩く探す。"""
    if isinstance(obj, dict):
        if obj.get("type") == "text" and isinstance(obj.get("text"), str):
            return obj["text"]
        for key in ("content", "message", "text"):
            if key in obj:
                found = first_text(obj[key])
                if found:
                    return found
    elif isinstance(obj, list):
        for item in obj:
            found = first_text(item)
            if found:
                return found
    elif isinstance(obj, str) and obj.strip():
        return obj
    return None


def timestamp_of(obj, fallback: float) -> str:
    for key in ("timestamp", "created_at", "time"):
        value = obj.get(key) if isinstance(obj, dict) else None
        if isinstance(value, str) and len(value) >= 10:
            return value
    return datetime.fromtimestamp(fallback, JST).isoformat()


# --------------------------------------------------------------------------
# リポジトリ操作
# --------------------------------------------------------------------------

def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=check,
    )


def repo_path(args) -> Path:
    return Path(getattr(args, "repo", None) or os.environ.get("AI_HISTORY_REPO") or DEFAULT_REPO)


def load_config(repo: Path) -> dict:
    config = dict(DEFAULT_CONFIG)
    path = repo / CONFIG_NAME
    if path.exists():
        config.update(json.loads(path.read_text(encoding="utf-8")))
    return config


def load_state(repo: Path, device: str) -> dict:
    path = repo / ".state" / f"{device}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"last_run": None, "ingested": {"claude": [], "codex": []}}


def parse_since(text: str | None) -> datetime | None:
    if not text:
        return None
    m = re.fullmatch(r"(\d+)([dhw])", text)
    if not m:
        raise SystemExit(f"--since の書式が不正: {text} (例: 7d, 24h, 2w)")
    n, unit = int(m.group(1)), m.group(2)
    delta = {"d": timedelta(days=n), "h": timedelta(hours=n), "w": timedelta(weeks=n)}[unit]
    return datetime.now(JST) - delta


# --------------------------------------------------------------------------
# setup
# --------------------------------------------------------------------------

README_TEXT = """# ai-history

Claude Code / Codex のローカル会話履歴を、秘匿情報をマスクした上で蓄積したもの。
`scripts/archive_ai_history.py`（dotfiles リポジトリ）が自動生成する。

**このリポジトリは private を維持すること。** マスクは万全ではない。

- `claude/<project>/`, `codex/YYYY/MM/DD/` — マスク済みセッション
- `index/<device>.jsonl` — 検索用メタデータ
- `.state/<device>.json` — デバイスごとの取り込み済み記録
"""

GITIGNORE_TEXT = f"{REPORT_DIR}/\n"


def cmd_setup(args) -> int:
    repo = repo_path(args)
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        subprocess.run(["git", "init", "-b", "main", str(repo)], check=True,
                       capture_output=True, text=True)
    for name, text in ((("README.md"), README_TEXT), (".gitignore", GITIGNORE_TEXT)):
        path = repo / name
        if not path.exists():
            path.write_text(text, encoding="utf-8")
    config_path = repo / CONFIG_NAME
    if not config_path.exists():
        config_path.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for sub in ("index", ".state"):
        (repo / sub).mkdir(exist_ok=True)

    if args.remote:
        existing = git(repo, "remote", check=False).stdout.split()
        if "origin" in existing:
            git(repo, "remote", "set-url", "origin", args.remote)
        else:
            git(repo, "remote", "add", "origin", args.remote)

    print(f"repo      : {repo}")
    print(f"device    : {device_id()}")
    print(f"config    : {config_path}")
    print(f"visibility: {check_visibility(repo)}")
    return 0


def check_visibility(repo: Path) -> str:
    """アーカイブ先が public でないことを確認する。判定できない場合は unknown。"""
    result = git(repo, "remote", "get-url", "origin", check=False)
    url = result.stdout.strip()
    if not url:
        return "no-remote (ローカルのみ)"
    probe = subprocess.run(["gh", "repo", "view", url, "--json", "visibility"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    if probe.returncode != 0:
        return "unknown (gh で確認できず — 手動で private を確認すること)"
    try:
        return json.loads(probe.stdout).get("visibility", "unknown").lower()
    except json.JSONDecodeError:
        return "unknown"


# --------------------------------------------------------------------------
# sync
# --------------------------------------------------------------------------

def cmd_sync(args) -> int:
    repo = repo_path(args)
    if not (repo / ".git").exists():
        print(f"ERROR: アーカイブリポジトリが未初期化: {repo}")
        print("       先に `setup` を実行すること。")
        return 2

    visibility = check_visibility(repo)
    if visibility == "public":
        print("ERROR: アーカイブ先が public です。中止します。")
        return 2

    config = load_config(repo)
    device = device_id()
    state = load_state(repo, device)
    excludes = [re.compile(p) for p in config.get("exclude_projects", [])]
    threshold = int(config.get("secret_hit_threshold", 40))

    if not args.no_pull and not args.dry_run:
        pull = git(repo, "pull", "--rebase", "--autostash", check=False)
        if pull.returncode != 0 and "origin" in git(repo, "remote", check=False).stdout:
            print("ERROR: pull に失敗しました。手動で解決してください。")
            print(pull.stderr.strip()[:400])
            return 2

    mapping_path = repo / "index" / "projects.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.exists() else {}

    candidates = discover(args.tool, parse_since(args.since))
    stats = {"scanned": len(candidates), "written": 0, "skipped_done": 0,
             "skipped_excluded": 0, "skipped_secret": 0, "skipped_residue": 0,
             "skipped_empty": 0, "failed": 0}
    report: list[str] = []
    preview: list[str] = []
    index_lines: list[str] = []

    for entry in candidates:
        tool = entry["tool"]
        sid = session_id_of(entry)
        if sid in state["ingested"].get(tool, []):
            stats["skipped_done"] += 1
            continue

        slug = project_slug(entry["group"], mapping) if entry["group"] else None
        if slug and any(rx.search(slug) or rx.search(entry["group"]) for rx in excludes):
            stats["skipped_excluded"] += 1
            report.append(f"excluded  {tool}/{sid} ({slug})")
            continue

        try:
            raw_lines = entry["path"].read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            stats["failed"] += 1
            report.append(f"ioerror   {tool}/{sid}: {exc.__class__.__name__}")
            continue

        masker = Masker(config)
        records, prompt, started = [], None, None
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if started is None:
                started = timestamp_of(obj, entry["path"].stat().st_mtime)
            if prompt is None:
                prompt = first_text(obj)
            records.append(mask_tree(trim(obj, args.full), masker))

        if not records:
            stats["skipped_empty"] += 1
            continue

        if masker.hits > threshold:
            stats["skipped_secret"] += 1
            report.append(f"secretful {tool}/{sid}: {masker.hits} hits (閾値 {threshold})")
            continue

        body = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
        residue = masker.residue(body)
        if residue:
            stats["skipped_residue"] += 1
            report.append(f"residue   {tool}/{sid}: {residue} 件の秘匿パターンが残存")
            continue

        started = started or datetime.now(JST).isoformat()
        day = started[:10]
        if tool == "claude":
            dest = repo / "claude" / (slug or "unknown") / f"{day}_{sid}.jsonl"
        else:
            dest = repo / "codex" / day.replace("-", "/") / f"{sid}.jsonl"

        masked_prompt = masker.mask(prompt or "")[:200].replace("\n", " ")
        if args.dry_run:
            preview.append(f"--- {dest.relative_to(repo)} ({len(records)} 行)")
            preview.append(f"    {masked_prompt}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body + "\n", encoding="utf-8")

        index_lines.append(json.dumps({
            "tool": tool, "session_id": sid, "device": device, "project": slug,
            "started_at": started, "message_count": len(records),
            "first_prompt": masked_prompt,
            "path": str(dest.relative_to(repo)).replace("\\", "/"),
        }, ensure_ascii=False))
        state["ingested"].setdefault(tool, []).append(sid)
        stats["written"] += 1

    report_dir = repo / REPORT_DIR
    report_dir.mkdir(exist_ok=True)
    (report_dir / "last-run.txt").write_text(
        "\n".join(report) or "(特記事項なし)", encoding="utf-8")
    if preview:
        (report_dir / "preview.txt").write_text("\n".join(preview), encoding="utf-8")

    if args.dry_run:
        emit_summary(stats, repo, dry_run=True, committed=False, pushed=False)
        return exit_code(stats, pushed=False)

    if stats["written"]:
        index_path = repo / "index" / f"{device}.jsonl"
        index_path.parent.mkdir(exist_ok=True)
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(index_lines) + "\n")
        mapping_path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
        state["last_run"] = datetime.now(JST).isoformat()
        state_path = repo / ".state" / f"{device}.json"
        state_path.parent.mkdir(exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")

        git(repo, "add", "-A")
        message = f"chore: {device} の履歴 {stats['written']} 件を追加"
        git(repo, "commit", "-m", message, check=False)

    pushed = False
    if stats["written"] and (args.push or config.get("auto_push")):
        result = git(repo, "push", "-u", "origin", "HEAD", check=False)
        pushed = result.returncode == 0
        if not pushed:
            report.append("push 失敗: " + result.stderr.strip()[:200])
            (report_dir / "last-run.txt").write_text("\n".join(report), encoding="utf-8")

    emit_summary(stats, repo, dry_run=False, committed=bool(stats["written"]), pushed=pushed)
    return exit_code(stats, pushed, push_requested=bool(args.push or config.get("auto_push")))


def exit_code(stats: dict, pushed: bool, push_requested: bool = False) -> int:
    """cron / タスクスケジューラから失敗を検知できるように終了コードを返す。

    0: 正常（取り込み0件でも、対象が無いだけなら正常）
    1: 取り込むべきものがあったのに1件も通らなかった / push を要求したのに失敗した
    """
    rejected = stats["skipped_secret"] + stats["skipped_residue"] + stats["failed"]
    if stats["written"] == 0 and rejected:
        return 1
    if push_requested and stats["written"] and not pushed:
        return 1
    return 0


def emit_summary(stats: dict, repo: Path, dry_run: bool, committed: bool, pushed: bool) -> None:
    """標準出力は必ずこの短いサマリのみ。明細は .archive-report/ に出す。"""
    lines = [
        f"mode      : {'dry-run' if dry_run else 'apply'}",
        f"repo      : {repo}",
        f"scanned   : {stats['scanned']}",
        f"written   : {stats['written']}",
        f"skipped   : done={stats['skipped_done']} excluded={stats['skipped_excluded']} "
        f"empty={stats['skipped_empty']} secretful={stats['skipped_secret']} "
        f"residue={stats['skipped_residue']} failed={stats['failed']}",
        f"committed : {committed}",
        f"pushed    : {pushed}",
        f"report    : {repo / REPORT_DIR / 'last-run.txt'}",
    ]
    print("\n".join(lines[:MAX_SUMMARY_LINES]))


# --------------------------------------------------------------------------
# search / show
# --------------------------------------------------------------------------

def cmd_search(args) -> int:
    repo = repo_path(args)
    needle = args.query.lower()
    hits = []
    for path in sorted((repo / "index").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if needle in line.lower():
                try:
                    hits.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    hits.sort(key=lambda h: h.get("started_at", ""), reverse=True)
    if not hits:
        print("該当なし")
        return 0
    for hit in hits[: args.limit]:
        print(f"{hit['started_at'][:16]}  {hit['tool']:6} {hit['session_id']}  "
              f"{hit.get('project') or '-'}  {hit['first_prompt'][:80]}")
    if len(hits) > args.limit:
        print(f"... 他 {len(hits) - args.limit} 件")
    return 0


def cmd_show(args) -> int:
    repo = repo_path(args)
    target = None
    for path in sorted((repo / "index").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            entry = json.loads(line)
            if entry["session_id"].startswith(args.session_id):
                target = entry
                break
    if not target:
        print(f"セッションが見つかりません: {args.session_id}")
        return 1
    lines = (repo / target["path"]).read_text(encoding="utf-8").splitlines()
    for line in lines[args.start : args.end]:
        print(line)
    print(f"--- {target['path']} の {args.start}..{min(args.end, len(lines))} / 全 {len(lines)} 行")
    return 0


# --------------------------------------------------------------------------

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo", help="アーカイブリポジトリのパス (既定: $AI_HISTORY_REPO or ~/ai-history)")

    parser = argparse.ArgumentParser(description=__doc__, parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str):
        return sub.add_parser(name, help=help_text, parents=[common])

    p_setup = add("setup", "アーカイブリポジトリを初期化する")
    p_setup.add_argument("--remote", help="origin に設定するリモートURL (private のこと)")
    p_setup.set_defaults(func=cmd_setup)

    p_sync = add("sync", "差分を取り込んでコミットする")
    p_sync.add_argument("--dry-run", action="store_true")
    p_sync.add_argument("--since", help="例: 7d, 24h, 2w")
    p_sync.add_argument("--tool", choices=["claude", "codex"])
    p_sync.add_argument("--full", action="store_true", help="間引きせず元に近い形で保存する")
    p_sync.add_argument("--push", action="store_true")
    p_sync.add_argument("--no-pull", action="store_true")
    p_sync.set_defaults(func=cmd_sync)

    p_search = add("search", "インデックスを検索する（本文は読まない）")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=20)
    p_search.set_defaults(func=cmd_search)

    p_show = add("show", "セッションの一部を表示する")
    p_show.add_argument("session_id")
    p_show.add_argument("--start", type=int, default=0)
    p_show.add_argument("--end", type=int, default=40)
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
