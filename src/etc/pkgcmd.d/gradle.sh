# -*- mode: shell-script -*-

## performance tip:
## use builtins, as 'c' command is bash-written and will be greatful
## if you would NOT spawn process. And please return as soon as you
## know it is NOT a recognised package.

## return errlvl 1 -- is not this package, subdir may contain other packages
pkgcmd:gradle:is_base() {
    [ -e build.gradle ]
}

