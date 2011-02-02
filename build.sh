#!/bin/sh -x
set -e

[ ! -x autogen.sh ] || ./autogen.sh || exit 1
autoconf || true
[ ! -x configure ] || ./configure || exit 2

if [ ! -e Makefile ]; then
    echo "$0: no Makefile, aborting." 1>&2
    exit 3
fi

# Actually build the project

# clear out any $@ potentially passed in
set --

# enable ccache if it is installed
export CCACHE_DIR="$PWD/../../ccache"
if command -v ccache >/dev/null; then
  if [ ! -e "$CCACHE_DIR" ]; then
    echo "$0: have ccache but cache directory does not exist: $CCACHE_DIR" 1>&2
  else
    set -- CC='ccache gcc' CXX='ccache g++'
  fi
else
  echo "$0: no ccache found, compiles will be slower." 1>&2
fi

ionice -c3 nice -n20 make -j16 "$@" || exit 4

# The "make -q check" probe in build.sh.example is faulty in that
# screwups in Makefiles make it think there are no unit tests to
# run. That's unacceptable; use a dumber probe.
if [ -e src/gtest ]; then
    # run "make check", but give it a time limit in case a test gets stuck
    ../maxtime 1800 ionice -c3 nice -n20 make check "$@" || exit 5
fi

git ls-files --modified >../modified-files
if [ -s ../modified-files ]; then
    echo "MODIFIED FILES:" 1>&2
    cat ../modified-files 1>&2
    exit 6
fi

git ls-files --exclude-standard --others >../added-files
if [ -s ../added-files ]; then
    echo "ADDED FILES:" 1>&2
    cat ../added-files 1>&2
    # TODO this is not considered fatal until we fix the current problems
    #exit 7
fi

exit 0
