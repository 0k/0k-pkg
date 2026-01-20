
## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
pkgcmd:js:is_base() {
    [ -e package.json ]
}

pkgcmd:js:applies() {
    [ -e tsconfig.json ]
}


## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:t:js:run() {
    echo Not Implemented yet
}


## ``p`` command -- runs all tests in profile mode, fails at first failure, produce diffable content.
pkgcmd:p:js:run() {
    echo Not Implemented yet
}


## ``pkg`` command -- check code and make package and validate them
pkgcmd:pkg-name:js:run() {
    cat package.json | jq -r .name
}

pkgcmd:pkg-version:js:run() {
    cat package.json | jq -r .version
}

## ``stats`` command -- runs linting stats, output diffable content
pkgcmd:stats:js:run() {
    echo Not Implemented yet
}


## ``lint`` command -- runs linting stats, output diffable content
pkgcmd:lint:js:run() {
    echo Not Implemented yet
}

