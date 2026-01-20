
if ! type -p toml >/dev/null; then
    warn "hatch packages requires \`\`toml\`\` cli. Install it with \`\`cargo install toml-cli\`\`."
    return 0
fi

if ! type -p jq >/dev/null; then
    warn "hatch packages requires \`\`jq\`\`."
    return 0
fi

## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
pkgcmd:hatch:is_base() {
    [ -e pyproject.toml ]
}

pkgcmd:hatch:applies() {
    [ -e pyproject.toml ] || return 1
    if ! build_system=$(toml get pyproject.toml build-system.requires); then
        return 1
    fi
    if ! build_requirements=($(jq -r '.[]' <<<"$build_system")); then
        return 1
    fi
    if ! [[ " ${build_requirements[*]} " == *" hatchling "* ]]; then
        return 1
    fi
    if ! [[ " ${build_requirements[*]} " == *" hatch-vcs "* ]]; then
        return 1
    fi
    return 0
}

## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:t:hatch:run() {
    hatch run test
}


## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:pkg-version:hatch:run() {
    hatch version
}

## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:pkg-name:hatch:run() {
    toml get -r pyproject.toml project.name
}


## ``p`` command -- runs all tests in profile mode, fails at first failure, produce diffable content.
pkgcmd:p:hatch:run() {
    echo Not Implemented yet
}


# ## ``lint`` command -- runs linting stats, output diffable content
# pkgcmd:lint:hatch:run() {
#     [ -e setup.cfg ] &&  egrep '^[flake8]' setup.cfg >/dev/null 2>&1 && {
#           flake8
#     }
# }

