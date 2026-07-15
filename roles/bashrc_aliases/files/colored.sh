#
# Ansible managed
#

if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    export LS_OPTIONS='--color=auto'
    export DIR_OPTIONS='--color=auto'
fi

alias ls='ls $LS_OPTIONS'
alias dir='dir $DIR_OPTIONS'
alias vdir='vdir $DIR_OPTIONS'
alias grep='grep --color=auto'

# colored GCC warnings and errors
export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# colored diff if colordiff is installed
if [ -x "$(command -v colordiff)" ]; then
    alias diff='colordiff'
fi
