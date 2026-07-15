#
# Ansible managed
#

# safety nets
alias cp='cp -i'
alias mv='mv -i'
alias rm='rm -i --preserve-root'

# navigation
alias ..='cd ..'
alias ...='cd ../..'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias lt='ls --human-readable --size -1 -S --classify'
alias hist='history | grep'

# working with files
alias count='find . -type f | wc -l'
alias cpv='rsync -ah --info=progress2'
alias df='df -H'
alias du='du -h'

# tmux shell aliases
alias tn='tmux new-session'
alias ta='tmux attach || tmux new-session'
alias tat='tmux attach -t'
alias tls='tmux list-sessions'

# nvidia shortcuts
alias nsmi='nvidia-smi'
