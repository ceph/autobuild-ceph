#!/bin/bash -x
set -e

. reset-modules.sh

echo --START-IGNORE-WARNINGS
[ ! -x install-deps.sh ] || ./install-deps.sh
echo --STOP-IGNORE-WARNINGS

mkdir build
cd build
cmake ..

make -j$(nproc) "$@" || exit 4

# run "make check", but give it a time limit in case a test gets stuck
#trap "pkill -9 ceph-osd || true ; pkill -9 ceph-mon || true" EXIT
#if ! ../maxtime 5400 make $(maybe_parallel_make_check) check "$@" ; then
#    exit 5
#fi

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "../$OUTDIR_TMP"
printf '%s\n' "$REV" >"../$OUTDIR_TMP/sha1"
MACH="$(uname -m)"
INSTDIR="inst.tmp"
[ ! -e "$INSTDIR" ]
../../maxtime 1800 ionice -c3 nice -n20 make install DESTDIR="$PWD/$INSTDIR"
tar czf "../$OUTDIR_TMP/ceph.$MACH.tgz" -C "$INSTDIR" .
rm -rf -- "$INSTDIR"

# put our temp files inside .git/ so ls-files doesn't see them
cd ..
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
