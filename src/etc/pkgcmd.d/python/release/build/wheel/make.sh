#!/bin/bash

build="$1"

mkdir -p "$build"
python setup.py bdist_wheel -d dist &&
    mv "dist/$pkg_name-$pkg_version"*".whl" "$build/"

