#!/bin/bash

build="$1"

mkdir -p "$build"
python setup.py sdist -v --formats=gztar &&
    mv "dist/$pkg_name-$pkg_version.tar.gz" "$build/"

