# dotfiles

Windows (PowerShell) と WSL/Linux の両方で使う設定ファイルを、シンボリックリンクで管理するリポジトリ。

## 構成

```
dotfiles/
├── links.json              # OS別のリンク定義 (src -> dest)
├── scripts/
│   ├── install.ps1          # Windows用インストーラ
│   └── install.sh           # WSL/Linux用インストーラ
├── shell/
│   ├── powershell/          # $PROFILE
│   ├── bash/.bashrc
│   ├── zsh/.zshrc
│   └── common/aliases.sh    # bash/zsh共通のエイリアス
├── git/
│   ├── .gitconfig
│   └── .gitignore_global
├── claude/
│   ├── CLAUDE.md             # ~/.claude/CLAUDE.md
│   └── settings.json         # ~/.claude/settings.json
└── editor/
    └── vscode/settings.json
```

設定の実体はこのリポジトリの中に置き、各環境の `$HOME` 配下からシンボリックリンクを張る。
編集は常にリポジトリ側のファイルに対して行う（リンク先を直接編集しても実体が更新されるだけなので実質同じ）。

`links.json` が唯一のマニフェスト。新しい設定ファイルを追加したいときは、ファイルを置いてから
`links.json` の `windows` / `linux` 配列にエントリを足すだけでよい。

## パス共有について

このリポジトリは `D:\notoa\Documents\app\cp\dotfiles` にある。WSL からは
`/mnt/d/notoa/Documents/app/cp/dotfiles` として同じファイルにアクセスできるので、
Windows・WSL のどちらで clone し直す必要もない。

## セットアップ

### Windows (PowerShell)

シンボリックリンク作成には管理者権限、または Windows の「開発者モード」が必要。

```powershell
cd D:\notoa\Documents\app\cp\dotfiles
.\scripts\install.ps1
```

### WSL / Linux

`jq` が必要（`sudo apt install -y jq`）。

```bash
cd /mnt/d/notoa/Documents/app/cp/dotfiles   # または git clone した先
./scripts/install.sh
```

## 動作

- 既にファイルが存在し、それがシンボリックリンクでなければ `<file>.backup` にリネームして退避してからリンクを張る。
- 既存のシンボリックリンクは張り直す（冪等）。
- リンク元 (`src`) が存在しない場合はスキップして警告を出す。

## マシン固有設定

`autocrlf` など、OSやマシンごとに変えたい git 設定は `~/.gitconfig.local`
（このリポジトリでは管理しない、各マシンに直接置くファイル）に書く。
`.gitconfig` から `[include] path = ~/.gitconfig.local` で読み込まれる。

## 設定を追加するとき

1. 該当ファイルをリポジトリ内の適切なディレクトリに置く。
2. `links.json` の `windows` / `linux` 配列にエントリを追加する。
3. 各OSで `install.ps1` / `install.sh` を再実行する。
