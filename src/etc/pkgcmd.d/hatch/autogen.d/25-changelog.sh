# -*- mode: shell-script -*-
##
## Vendored from 0k-pkg (``hatch/autogen.d/25-changelog.sh``).
## Refresh with ``pkg vendor``; to keep local edits, add a line
## ``## pkgcmd: local-override`` in the first five lines.
##
## Generates ``CHANGELOG.rst`` from git history with ``gitchangelog``.
## Skipped with a warning when the tool is missing, unless
## ``AUTOGEN_STRICT=1`` (release pipeline).
##

if [ -e .gitchangelog.rc ]; then
    depends_soft gitchangelog || return 0
    gitchangelog > CHANGELOG.rst.tmp || {
        rm -f CHANGELOG.rst.tmp
        echo "Changelog NOT generated: gitchangelog failed." >&2
        return 1
    }
    if [ -f CHANGELOG.rst ] && diff CHANGELOG.rst CHANGELOG.rst.tmp >/dev/null; then
        echo "No changes in CHANGELOG.rst" >&2
        rm CHANGELOG.rst.tmp
    else
        echo "Updating CHANGELOG.rst" >&2
        mv CHANGELOG.rst.tmp CHANGELOG.rst
    fi
fi
