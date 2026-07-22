# --- dotfiles: .zshrc ---

HISTSIZE=10000
SAVEHIST=20000
HISTFILE=~/.zsh_history
setopt APPEND_HISTORY SHARE_HISTORY

_this="${(%):-%N}"
[ -L "$_this" ] && _this="$(readlink -f "$_this")"
source "$(dirname "$_this")/../common/aliases.sh"
unset _this
