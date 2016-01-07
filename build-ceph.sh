#!/bin/bash -x
set -e

git submodule foreach 'git clean -fdx && git reset --hard'
rm -rf ceph-object-corpus
rm -rf ceph-erasure-code-corpus
rm -rf src/gmock
rm -rf src/leveldb
rm -rf src/libs3
rm -rf src/mongoose
rm -rf src/civetweb
rm -rf src/rocksdb
rm -rf src/erasure-code/jerasure/gf-complete
rm -rf src/erasure-code/jerasure/jerasure
rm -rf .git/modules/
git clean -fdx && git reset --hard
/srv/git/bin/git submodule sync
/srv/autobuild-ceph/use-mirror.sh
/srv/git/bin/git submodule update --init
git clean -fdx

echo --START-IGNORE-WARNINGS
[ ! -x install-deps.sh ] || ./install-deps.sh
[ ! -x autogen.sh ] || ./autogen.sh || exit 1
autoconf || true
echo --STOP-IGNORE-WARNINGS
[ -z "$CEPH_EXTRA_CONFIGURE_ARGS" ] && CEPH_EXTRA_CONFIGURE_ARGS=--with-tcmalloc
[ ! -x configure ] || CFLAGS="-fno-omit-frame-pointer -g -O2" CXXFLAGS="-fno-omit-frame-pointer -g" ./configure --with-debug --with-radosgw --with-libatomic-ops --without-lttng --disable-static --with-librocksdb-static=check $CEPH_EXTRA_CONFIGURE_ARGS || exit 2

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

function can_parallel_make_check() {
    local commit=$(git rev-parse tags/v0.88^{})
    git rev-list HEAD | grep --quiet $commit
}

function maybe_parallel_make_check() {
    if can_parallel_make_check ; then
        echo -j$(get_processors)
    fi
}
#
# Return MIN(4, MAX(1, (number of processors / 2)))
# Do not try to use more than 4 because it will stress
# IO too much
#
function get_processors() {
    if test $(nproc) -ge 16 ; then
        echo 4
    elif test $(nproc) -ge 2 ; then
        expr $(nproc) / 2
    else
        echo 1
    fi
}


function display_failures() {
    local dir=$1
    # can be removed after hammer is retired
    # or https://github.com/ceph/ceph/pull/4923
    # is backported to all branches.
    if ! test -f src/Makefile-env.am || ! grep -q VERBOSE src/Makefile-env.am ; then
        cat src/test-suite.log
    fi
}

make -j$(get_processors) "$@" || exit 4

# run "make check", but give it a time limit in case a test gets stuck

trap "pkill -9 ceph-osd || true ; pkill -9 ceph-mon || true" EXIT

if ! ../maxtime 5400 make $(maybe_parallel_make_check) check "$@" ; then
    display_failures .
    exit 5
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
