# --- dotfiles: .bashrc ---

[ -z "$PS1" ] && return

HISTSIZE=10000
HISTFILESIZE=20000
shopt -s histappend
shopt -s checkwinsize

_this="${BASH_SOURCE[0]}"
[ -L "$_this" ] && _this="$(readlink -f "$_this")"
# shellcheck source=../common/aliases.sh
source "$(dirname "$_this")/../common/aliases.sh"
unset _this
