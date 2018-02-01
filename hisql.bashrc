#!/bin/bash


function __save_history { 
    p=$(HISTTIMEFORMAT="" history 1 | perl -lape 's/^\s*\d+\s+//' );
    (hisql add "$p"&)
}

# clobber previous value of PROMPT_COMMAND, might not be a good idea
export PROMPT_COMMAND="__save_history"


function reload_history {
    hisql save -T > $HISTFILE
    COUNT=$(cat $HISTFILE | wc -l)
    echo "Reload history... $COUNT entries"
    history -c; history -r
}

function fuzzyHistory {
    OLD_LINE=$READLINE_LINE
    CMD=$(hisql list | fzf --tac --no-sort --preview 'echo {}' --preview-window up:10:wrap --bind ctrl-x:abort,?:toggle-preview -q "$OLD_LINE")
    if [[ -n "$CMD" ]]; then
        READLINE_LINE=$CMD;
        oLANG=$LANG; LANG=C;
        READLINE_POINT=${#READLINE_LINE};
        LANG=$oLANG;
    fi
}

bind -x '"\C-f":fuzzyHistory'
hisql save -T > $HISTFILE
