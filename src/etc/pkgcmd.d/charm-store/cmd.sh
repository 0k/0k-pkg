
## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
# pkgcmd:all:is_base() {
# }

pkgcmd:charm-store:applies() {
    local md=(**/metadata.yml)
    [[ -f "${md[0]}" ]]
}

## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:t:charm-store:run() {
    local f md=(**/metadata.yml)
    for f in "${md[@]}"; do
        (
            cd "${f%/metadata.yml}"
            if pkgcmd:charm:applies; then
                t "$@"
            fi
        ) || break
    done
}
