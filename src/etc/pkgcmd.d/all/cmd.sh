
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


## ``pkg-git-hook`` command -- runs git hook scripts from git-hook/<HOOK>/
##
## Invoked by the global ``core.hooksPath`` trampolines as
## ``pkg-git-hook <HOOK> [ARGS...]`` where HOOK is the git hook name
## (``pre-commit``, ``commit-msg``, ...) and ARGS are the arguments git
## passed to the hook.  Runs every executable in ``git-hook/<HOOK>/``
## (all applying package types, sorted), stops at the first failure and
## returns its exit code, then chains to the repository-local
## ``.git/hooks/<HOOK>`` if one is executable.
##
## Silent on success: git hooks are expected not to print unless they
## have something to report.
pkgcmd:pkg-git-hook:all:run() {
    local hook="$1" script local_hook
    shift
    if [ -z "$hook" ]; then
        die "pkg-git-hook: missing hook name argument."
    fi
    while read-0 script; do
        "$script" "$@" || return "$?"
    done < <(pkg._list_scripts "git-hook/$hook" | sort -z)
    local_hook="$(git rev-parse --git-dir 2>/dev/null)/hooks/$hook"
    if [ -x "$local_hook" ]; then
        exec "$local_hook" "$@"
    fi
    return 0
}

