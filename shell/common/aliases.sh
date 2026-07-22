# --- dotfiles: shared aliases (sourced by .bashrc and .zshrc) ---

alias ll='ls -la'
alias gs='git status'
alias gco='git checkout'
alias gp='git pull'
alias ..='cd ..'
alias ...='cd ../..'

_this="${BASH_SOURCE[0]:-${(%):-%N}}"
[ -L "$_this" ] && _this="$(readlink -f "$_this")"
export DOTFILES
DOTFILES="$(cd "$(dirname "$_this")/../.." && pwd)"
unset _this

if command -v starship >/dev/null 2>&1; then
  if [ -n "${ZSH_VERSION:-}" ]; then
    eval "$(starship init zsh)"
  elif [ -n "${BASH_VERSION:-}" ]; then
    eval "$(starship init bash)"
  fi
fi
