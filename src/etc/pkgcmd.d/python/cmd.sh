
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


## ``p`` command -- runs all tests in profile mode, fails at first failure, produce diffable content.
pkgcmd:p:python:run() {
    echo Not Implemented yet
}


## ``pkg`` command -- check code and make package and validate them
pkgcmd:pkg:python:run() {
    pkg-py "$@"
}


## ``stats`` command -- runs linting stats, output diffable content
pkgcmd:stats:python:run() {
    pkg-py "$@"
}


## ``lint`` command -- runs linting stats, output diffable content
pkgcmd:lint:python:run() {
    [ -e setup.cfg ] &&  egrep '^[flake8]' setup.cfg >/dev/null 2>&1 && {
          flake8
    }
}

