
if ! type -p toml >/dev/null; then
    warn "cargo packages requires \`\`toml\`\` cli. Install it with \`\`cargo install toml-cli\`\`."
    return 0
fi

## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
pkgcmd:cargo:is_base() {
    [ -e Cargo.toml ]
}

pkgcmd:cargo:applies() {
    [ -e Cargo.toml ]
}


## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:t:cargo:run() {
    cargo test
}


## ``p`` command -- runs all tests in profile mode, fails at first failure, produce diffable content.
pkgcmd:p:cargo:run() {
    echo Not Implemented yet
}


pkgcmd:pkg-name:cargo:run() {
    toml get -r Cargo.toml package.name
}

pkgcmd:pkg-version:cargo:run() {
    toml get -r Cargo.toml package.version
}
