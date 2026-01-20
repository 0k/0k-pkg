# -*- mode: shell-script -*-

## performance tip:
## use builtins, as 'c' command is bash-written and will be greatful
## if you would NOT spawn process. And please return as soon as you
## know it is NOT a recognised package.

pkgcmd:myname:is_base() {
    [ -e __openerp__.py ]
}



## ``t`` command -- runs all tests, fails at first failure by default
pkgcmd:t:myname:run() {
    echo "Not implemented yet"
}


## ``p`` command -- runs all tests in profile mode, fails at first
## failure, produce diffable content.
pkgcmd:p:myname:run() {
    echo "Not implemented yet"
}


## ``pkg`` command -- make a one-file package of the current workdir
## state
pkgcmd:pkg:myname:run() {
    echo "Not implemented yet"
}
