
## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
pkgcmd:ts:is_base() {
    [ -e tsconfig.json ]
}

pkgcmd:ts:applies() {
    [ -e tsconfig.json ]
}


## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:t:ts:run() {
    echo Not Implemented yet
}


## ``pkg`` and ``lint`` are provided by the ``all`` package type
## (``pkg-common`` and the ``lint/`` hook scripts); the ts-specific
## parts live in ``release/`` and ``dist/check/`` here.

