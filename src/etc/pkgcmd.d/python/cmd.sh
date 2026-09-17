
## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
pkgcmd:python:is_base() {
    [ -e setup.py ]
}

pkgcmd:python:applies() {
    [ -e setup.py ]
}

## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:t:python:run() {
    [ -e setup.cfg ] &&  egrep '^[nosetests]' setup.cfg >/dev/null 2>&1 && {
        nosetests -sx "$@"
        exit $?
    }
    echo Not Implemented yet
}


## ``pkg`` and ``lint`` are provided by the ``all`` package type
## (``pkg-common`` and the ``lint/`` hook scripts); the python-specific
## parts live in ``release/``, ``source/check/`` and ``lint/`` here.

