
## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
pkgcmd:autogen:is_base() {
  [ -x "./autogen.sh" ]
}

pkgcmd:autogen:applies() {
  [ -x "./autogen.sh" ]
}

## ``t`` command -- runs all tests, fails at first failure by default
# pkgcmd:t:autogen:run() {
#     echo Not Implemented yet
# }


## ``p`` command -- runs all tests in profile mode, fails at first failure, produce diffable content.
# pkgcmd:p:autogen:run() {
#     echo Not Implemented yet
# }


## ``pkg`` command -- check code and make package and validate them
#pkgcmd:pkg:autogen:run() {
#    pkg-common "$@"
#}


## ``pkg-name`` command -- check code and make package and validate them
pkgcmd:pkg-name:autogen:run() {
   ./autogen.sh --get-name
}


## ``pkg-version`` command -- check code and make package and validate them
pkgcmd:pkg-version:autogen:run() {
   ./autogen.sh --get-version
}


## ``stats`` command -- runs linting stats, output diffable content
# pkgcmd:stats:autogen:run() {
#     pkg-py "$@"
# }


## ``lint`` command -- runs linting stats, output diffable content
# pkgcmd:lint:autogen:run() {
#     [ -e setup.cfg ] &&  egrep '^[flake8]' setup.cfg >/dev/null 2>&1 && {
#           flake8
#     }
# }

