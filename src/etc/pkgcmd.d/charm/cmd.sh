
## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
# pkgcmd:all:is_base() {
# }

pkgcmd:charm:applies() {
    [[ -f "metadata.yml" ]]
}

## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:t:charm:run() {
    local f md=(**/metadata.yml)
    if [ -x "bin/test" ]; then
        bin/test "$@"
    fi
}
