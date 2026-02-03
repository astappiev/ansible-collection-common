{{ ansible_managed | comment }}

# check if running bash
[ -z "$BASH_VERSION" ] && return

# exit if not running interactively
case $- in
    *i*) ;;
      *) return;;
esac

__set_bashrc_color_prompt() {
    # Only run once using guard variable
    [ -n "${__bashrc_color_prompt_set:-}" ] && return
    __bashrc_color_prompt_set=1

    # set variable identifying the chroot you work in (used in the prompt below)
    if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
        debian_chroot=$(cat /etc/debian_chroot)
    fi

    if [ "$TERM" != "dumb" ]; then
        PS1='${debian_chroot:+($debian_chroot)}\[\033[01;{{ hostname_prompt_color_code }}m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
    else
        PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
    fi
}

PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND;}__set_bashrc_color_prompt"
