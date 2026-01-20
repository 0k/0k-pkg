# -*- mode: shell-script -*-

## performance tip:
## use builtins, as 'c' command is bash-written and will be greatful
## if you would NOT spawn process. And please return as soon as you
## know it is NOT a recognised package.

## return errlvl 1 -- is not this package, subdir may contain other packages
pkgcmd:default:is_base() {
    [ -e LICENSE -o -e COPYING -o -d bin -o -d src -o -d sbin ] ||
        [[ "$PWD" == "$DEV_DIR/java/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/python/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/charm/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/c/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/php/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/xul/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/site/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/rb/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/js/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/go/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/other/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/projects/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/graphane/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/doc/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/docker/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/lib/"* ]] ||
        [[ "$PWD" == "$DEV_DIR/python/android-sdk-linux" ]]
}

