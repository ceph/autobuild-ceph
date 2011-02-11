#!/bin/sh -x
set -e

[ ! -x autogen.sh ] || ./autogen.sh || exit 1
autoconf || true
[ ! -x configure ] || ./configure --with-debug --with-radosgw --with-fuse --with-tcmalloc --with-libatomic-ops --with-gtk2 || exit 2

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

TARDIR="../out/tarball/sha1"
install -d -m0755 -- "$TARDIR"
MACH="$(uname -m)"
REV="$(git rev-parse HEAD)"
INSTDIR="inst.tmp"
[ ! -e "$INSTDIR" ]
../maxtime 1800 ionice -c3 nice -n20 make install DESTDIR="$PWD/$INSTDIR"
TARBALL="$TARDIR/$MACH.$REV.tgz"
tar czf "$TARBALL.tmp" -C "$INSTDIR" .
rm -rf -- "$INSTDIR"

# put our temp files inside .git/ so ls-files doesn't see them
git ls-files --modified >.git/modified-files
if [ -s .git/modified-files ]; then
    echo "error: Modified files:" 1>&2
    cat .git/modified-files 1>&2
    exit 6
fi

git ls-files --exclude-standard --others >.git/added-files
if [ -s .git/added-files ]; then
    echo "error: Added files:" 1>&2
    cat .git/added-files 1>&2
    exit 7
fi

# we're successful, the binary tarball is ok to be published
mv -- "$TARBALL.tmp" "$TARBALL"

exit 0
