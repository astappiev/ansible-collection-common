{{ ansible_managed | comment }}

# If not running zsh, don't do anything
[ -z "$ZSH_VERSION" ] && return

__set_zshrc_color_prompt() {
    # Set prompt with color
    # %F{color} starts color, %f ends it.
    # %n is user, %m is hostname, %~ is cwd.
    PROMPT='%F{ {{ hostname_prompt_color }} }%n@%m%f:%F{blue}%~%f$ '
    
    # Remove from precmd_functions to run only once
    precmd_functions=("${(@)precmd_functions:#__set_zshrc_color_prompt}")
    unfunction __set_zshrc_color_prompt
}

precmd_functions+=(__set_zshrc_color_prompt)
