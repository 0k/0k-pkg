
## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
pkgcmd:kal-shunit:is_base() {
    [ -x test/test -o -x bin/test ] || return 1
}


pkgcmd:t:kal-shunit:run() {
    if [ -x test/test ]; then
        cd test
        ./test "$@"
    else
        cd test
        ../bin/test "$@"
    fi
}


pkgcmd:p:kal-shunit:run() {
    if [ -x test/test ]; then
        cd test
        ./test -p "$@"
    else
        cd test
        ../bin/test -p "$@"
    fi
}


pkgcmd:pkg:kal-shunit:run() {
    mk_deb "$@"
}

