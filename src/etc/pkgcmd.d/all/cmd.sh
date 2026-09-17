
## performance tip:
## use builtins, as 'c' command is bash-written and will be
## greatful if you would NOT spawn process. And please return
## as soon as you know it is NOT a recognised package.
# pkgcmd:all:is_base() {
# }

pkgcmd:all:applies() {
    return 0
}

## ``t`` command -- runs all tests, fails at first failure by default
# pkgcmd:t:all:run() {
#     echo Not Implemented yet
# }


## ``p`` command -- runs all tests in profile mode, fails at first failure, produce diffable content.
# pkgcmd:p:all:run() {
#     echo Not Implemented yet
# }


## ``pkg`` command -- check code and make package and validate them
pkgcmd:pkg:all:run() {
    pkg-common "$@"
}


## ``stats`` command -- runs linting stats, output diffable content
# pkgcmd:stats:all:run() {
# }


## ``lint`` command -- runs lint checks from lint/ directory
pkgcmd:lint:all:run() {
    local script
    while read-0 script; do
        echo "${script##*/}..."
        "$script" "$@" || return 1
    done < <(pkg._list_scripts lint | sort -z)
}


## ``pkg-git-hook`` command -- runs git hook scripts from git-hook/<HOOK>/
##
## Invoked by the global ``core.hooksPath`` trampolines as
## ``pkg-git-hook <HOOK> [ARGS...]`` where HOOK is the git hook name
## (``pre-commit``, ``commit-msg``, ...) and ARGS are the arguments git
## passed to the hook.  Runs every executable in ``git-hook/<HOOK>/``
## (all applying package types, sorted), stops at the first failure and
## returns its exit code, then chains to the repository-local
## ``.git/hooks/<HOOK>`` if one is executable.
##
## Silent on success: git hooks are expected not to print unless they
## have something to report.
pkgcmd:pkg-git-hook:all:run() {
    local hook="$1" script local_hook
    shift
    if [ -z "$hook" ]; then
        die "pkg-git-hook: missing hook name argument."
    fi
    while read-0 script; do
        "$script" "$@" || return "$?"
    done < <(pkg._list_scripts "git-hook/$hook" | sort -z)
    local_hook="$(git rev-parse --git-dir 2>/dev/null)/hooks/$hook"
    if [ -x "$local_hook" ]; then
        exec "$local_hook" "$@"
    fi
    return 0
}



##
## ``vendor`` command -- materialise 0k-pkg build scripts into the project
##
## Copies the canonical ``autogen.sh`` and every ``autogen.d/`` script
## provided by the applying plugins into the project, so that a fresh
## ``git clone`` can run ``./autogen.sh`` without 0k-pkg installed
## (the autotools model: ``autoreconf`` is private, ``configure`` is
## shipped).  Provenance is recorded in
## ``.package.d/autogen.d/MANIFEST`` and checked at release time by
## ``all/source/check/vendored``.
##
## A project file whose first five lines contain
## ``## pkgcmd: local-override`` is left untouched.  Files listed in
## the previous MANIFEST but no longer provided by any plugin are
## removed; files never listed are never touched.
##
## Options: ``--dry-run`` (``-n``) reports without writing.
##

## Path of the canonical autogen.sh shipped with 0k-pkg.
pkg._vendor_autogen_src() {
    local bin
    bin="$(readlink -f "$CONFIG_PATH/pkgcmd.d")" || return 1
    bin="${bin%/etc/pkgcmd.d}"
    echo "$bin/share/autogen.sh"
}

## Commit of the 0k-pkg checkout providing the plugins (empty when
## the config path is not a git checkout).
pkg._vendor_source_commit() {
    git -C "$(readlink -f "$CONFIG_PATH/pkgcmd.d")" rev-parse --short HEAD 2>/dev/null
}

pkg._vendor_sha() {
    sha256sum "$1" | cut -f 1 -d " "
}

pkg._vendor_has_override() {
    head -n 5 "$1" 2>/dev/null | grep -q '^## pkgcmd: local-override'
}

## Emits ``relpath\0sha\0plugin\0src\0`` for every file that vendoring
## would install (autogen.sh first, then plugin autogen.d scripts).
pkg._vendor_candidates() {
    local src plugin file
    src="$(pkg._vendor_autogen_src)" || die "vendor: cannot locate 0k-pkg share directory."
    [ -f "$src" ] || die "vendor: canonical autogen.sh not found at '$src'."
    p0 "autogen.sh" "$(pkg._vendor_sha "$src")" "share" "$src"
    ## The ``autogen`` plugin applies only once ``autogen.sh`` exists,
    ## which is precisely what vendoring installs: always include it.
    ## Sorted by destination so the MANIFEST is stable whatever the
    ## plugin detection order.
    while read-0 plugin file; do
        p0 ".package.d/autogen.d/${file##*/}" "$(pkg._vendor_sha "$file")" "$plugin" "$file"
    done < <(PKGCMD_ALTERNATIVES="$(pkg._vendor_alternatives)" pkg._list_plugin_files autogen.d |
                 pkg._sort_pairs_by_basename)
}

## Reads ``plugin\0path\0`` pairs, emits them sorted by basename.
pkg._sort_pairs_by_basename() {
    local plugin file
    while read-0 plugin file; do
        printf "%s\t%s\n" "${file##*/}" "$plugin"$'\t'"$file"
    done | sort | while IFS=$'\t' read -r _ plugin file; do
        p0 "$plugin" "$file"
    done
}

## Applying plugins, with ``autogen`` forced in (see above).
pkg._vendor_alternatives() {
    local alt
    for alt in $PKGCMD_ALTERNATIVES; do
        [ "$alt" = autogen ] && { echo "$PKGCMD_ALTERNATIVES"; return 0; }
    done
    printf "%s\n%s\n" "$PKGCMD_ALTERNATIVES" autogen
}

pkgcmd:vendor:all:run() {
    local dry_run= arg manifest=.package.d/autogen.d/MANIFEST
    local rel sha plugin src action changed= tmp_manifest old_files
    for arg in "$@"; do
        case "$arg" in
            -n|--dry-run) dry_run=1;;
            *) die "vendor: unknown argument '$arg'.";;
        esac
    done
    [ -e .package.d/config ] || [ -e .package ] ||
        die "vendor: no '.package.d/config' here; run from a project root."

    tmp_manifest=$(mktemp) || die "vendor: cannot create temporary file."
    echo "source 0k-pkg $(pkg._vendor_source_commit)" > "$tmp_manifest"

    declare -A keep=()
    while read-0 rel sha plugin src; do
        keep["$rel"]=1
        if pkg._vendor_has_override "$rel"; then
            action="override (kept)"
        elif [ -f "$rel" ] && [ "$(pkg._vendor_sha "$rel")" = "$sha" ]; then
            action="up-to-date"
        elif [ -f "$rel" ]; then
            action="update"
        else
            action="install"
        fi
        printf "%-12s %-38s (from %s)\n" "$action" "$rel" "$plugin"
        case "$action" in
            update|install)
                changed=1
                if [ -z "$dry_run" ]; then
                    case "$rel" in */*) mkdir -p "${rel%/*}";; esac
                    cp "$src" "$rel" || die "vendor: cannot write '$rel'."
                    if [ "$rel" = autogen.sh ]; then
                        chmod +x "$rel"
                    else
                        chmod -x "$rel"
                    fi
                fi
                ;;
        esac
        if [ "$action" != "override (kept)" ]; then
            echo "$rel $sha $plugin" >> "$tmp_manifest"
        fi
    done < <(pkg._vendor_candidates)

    ## Remove files vendored earlier but no longer provided.
    if [ -f "$manifest" ]; then
        while read -r rel sha plugin; do
            [ "$rel" = source ] && continue
            [ "${keep[$rel]}" ] && continue
            [ -f "$rel" ] || continue
            if pkg._vendor_has_override "$rel"; then
                printf "%-12s %-38s (override, no longer provided)\n" "kept" "$rel"
                continue
            fi
            if [ "$(pkg._vendor_sha "$rel")" != "$sha" ]; then
                printf "%-12s %-38s (modified, no longer provided; not removed)\n" "kept" "$rel"
                continue
            fi
            printf "%-12s %-38s (no longer provided)\n" "remove" "$rel"
            changed=1
            [ "$dry_run" ] || rm -f "$rel"
        done < "$manifest"
    fi

    if [ "$dry_run" ]; then
        rm -f "$tmp_manifest"
        [ "$changed" ] && echo "Dry run: nothing written."
        return 0
    fi
    mkdir -p .package.d/autogen.d
    if [ -f "$manifest" ] && diff -q "$manifest" "$tmp_manifest" >/dev/null; then
        rm -f "$tmp_manifest"
    else
        mv "$tmp_manifest" "$manifest" || die "vendor: cannot write '$manifest'."
        chmod 0644 "$manifest"
        changed=1
    fi
    if [ "$changed" ]; then
        echo
        echo "Vendored scripts updated. Re-run './autogen.sh' and your tests, then commit."
    else
        echo "Already up to date."
    fi
}
