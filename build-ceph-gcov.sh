#!/bin/sh -x
set -e

#
# remove everything but .git. It's the same as rm -fr * only less
# scary. gitbuilder requires the build directory to be present, we're
# adding a new harcoded constraint, just taking advantage of any existing
# one. 
# 
# Although it should be possible to git clean -ffdx, there are complicated
# corner cases (involving submodules in particular but not only) that makes
# it complicated when switching from one branch to another.
#
rm -fr ../build/*
git reset --hard
#
# This is properly taken care of by autogen.sh post firefly but we
# need this for branches before firefly.
#
/srv/git/bin/git submodule sync
/srv/autobuild-ceph/use-mirror.sh
/srv/git/bin/git submodule update --init

echo --START-IGNORE-WARNINGS
[ ! -x autogen.sh ] || ./autogen.sh || exit 1
autoconf || true
echo --STOP-IGNORE-WARNINGS
[ ! -x configure ] || ./configure --enable-coverage --with-debug --with-radosgw --with-fuse --with-tcmalloc --with-libatomic-ops --with-gtk2 --with-profiler --enable-cephfs-java || exit 2

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

NCPU=$(( 2 * `grep -c processor /proc/cpuinfo` ))
ionice -c3 nice -n20 make -j$NCPU "$@" || exit 4

# The "make -q check" probe in build.sh.example is faulty in that
# screwups in Makefiles make it think there are no unit tests to
# run. That's unacceptable; use a dumber probe.
if [ -e src/gtest ]; then
    # run "make check", but give it a time limit in case a test gets stuck
    ../maxtime 1800 ionice -c3 nice -n20 make check "$@" || exit 5
fi

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
MACH="$(uname -m)"
INSTDIR="inst.tmp"
[ ! -e "$INSTDIR" ]
../maxtime 1800 ionice -c3 nice -n20 make install DESTDIR="$PWD/$INSTDIR"
tar czf "$OUTDIR_TMP/ceph.$MACH.tgz" -C "$INSTDIR" .
rm -rf -- "$INSTDIR"

# put our temp files inside .git/ so ls-files doesn't see them
git ls-files --modified >.git/modified-files
if [ -s .git/modified-files ]; then
    rm -rf "$OUTDIR_TMP"
    echo "error: Modified files:" 1>&2
    cat .git/modified-files 1>&2
    exit 6
fi

git ls-files --exclude-standard --others >.git/added-files
if [ -s .git/added-files ]; then
    rm -rf "$OUTDIR_TMP"
    echo "error: Added files:" 1>&2
    cat .git/added-files 1>&2
    exit 7
fi

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

exit 0
