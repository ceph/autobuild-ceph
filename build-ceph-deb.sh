#!/bin/sh -x
set -e

git clean -fdx && git reset --hard
# Remove submodules from .git/config so its re-imported from .gitmodules:
for submodule in $(git submodule -q foreach 'echo submodule.$name')
do
    git config --remove-section  $submodule
done

# pull down submodules
git submodule foreach 'git clean -fdx && git reset --hard'
rm -rf ceph-object-corpus
rm -rf src/leveldb
rm -rf src/libs3
rm -rf src/mongoose
rm -rf src/civetweb
git submodule init
git submodule update
git clean -fdx


DISTS=`cat ../../dists`

echo --START-IGNORE-WARNINGS
[ ! -x autogen.sh ] || ./autogen.sh || exit 1
autoconf || true
echo --STOP-IGNORE-WARNINGS
[ ! -x configure ] || ./configure --with-debug --with-radosgw --with-fuse --with-tcmalloc --with-libatomic-ops --with-gtk2 --with-profiler --enable-cephfs-java || exit 2

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

# build the debs
mkdir -p release
GNUPGHOME="/srv/gnupg" ionice -c3 nice -n20 /srv/ceph-build/build_snapshot.sh release /srv/debian-base $DISTS

VER=`cd release && ls`
echo "VER is $VER"

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
printf '%s\n' "$VER" >"$OUTDIR_TMP/version"
printf '%s\n' "ceph" >"$OUTDIR_TMP/name"

mkdir -p $OUTDIR_TMP/conf
/srv/ceph-build/gen_reprepro_conf.sh $OUTDIR_TMP 03C3951A
GNUPGHOME="/srv/gnupg" /srv/ceph-build/push_to_repo.sh release $OUTDIR_TMP $VER main

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

# rebuild combined debian repo output
(
    cd ../out/output
    rm -rf combined
    GNUPGHOME="/srv/gnupg" /srv/ceph-build/merge_repos.sh combined sha1/*
)

exit 0
