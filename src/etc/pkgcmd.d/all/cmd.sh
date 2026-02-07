
## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
# pkgcmd:all:is_base() {
# }

pkgcmd:all:applies() {
    return 0
}

## ``t`` command -- runs all tests, fails at first failure by default
# pkgcmd:t:all:run() {
#     echo Not Implemented yet
# }


## ``p`` command -- runs all tests in profile mode, fails at first failure, produce diffable content.
# pkgcmd:p:all:run() {
#     echo Not Implemented yet
# }


## ``pkg`` command -- check code and make package and validate them
pkgcmd:pkg:all:run() {
    pkg-common "$@"
}


## ``stats`` command -- runs linting stats, output diffable content
# pkgcmd:stats:all:run() {
#     pkg-py "$@"
# }


## ``lint`` command -- runs lint checks from lint/ directory
pkgcmd:lint:all:run() {
    local script
    while read-0 script; do
        echo "${script##*/}..."
        "$script" "$@" || return 1
    done < <(pkg._list_scripts lint | sort -z)
}

