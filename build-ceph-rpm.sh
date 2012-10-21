#!/bin/sh -x
set -e

# pull down submodules
git submodule foreach 'git clean -fdx && git reset --hard'
rm -rf ceph-object-corpus
rm -rf src/leveldb
rm -rf src/libs3
git submodule init
git submodule update
git clean -fdx


DISTS=`cat ../../dists`

echo --START-IGNORE-WARNINGS
[ ! -x autogen.sh ] || ./autogen.sh || exit 1
autoconf || true
echo --STOP-IGNORE-WARNINGS
[ ! -x configure ] || ./configure --with-debug --with-radosgw --with-fuse --with-tcmalloc --with-libatomic-ops --with-gtk2 --with-nss || exit 2

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

#
#  Build Source tarball.  We do this after runing autogen/configure so that
#  ceph.spec has the correct version number filled in.
echo "**** Building Tarball ***"
make dist-bzip2

# Set up build area
BUILDAREA=./rpmbuild
mkdir -p ${BUILDAREA}/SOURCES
mkdir -p ${BUILDAREA}/SRPMS
mkdir -p ${BUILDAREA}/SPECS
mkdir -p ${BUILDAREA}/RPMS
mkdir -p ${BUILDAREA}/BUILD
cp -a ceph-*.tar.bz2 ${BUILDAREA}/SOURCES/.

# Build RPMs
BUILDAREA=`readlink -fn ${BUILDAREA}`   ### rpm wants absolute path
rpmbuild -bb --define "_topdir ${BUILDAREA}" --define "_unpackaged_files_terminate_build 0" ceph.spec

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
#printf '%s\n' "$VER" >"$OUTDIR_TMP/version"
#printf '%s\n' "ceph" >"$OUTDIR_TMP/name"
#mkdir -p $OUTDIR_TMP/conf

#MACH="$(uname -m)"
#INSTDIR="inst.tmp"
#[ ! -e "$INSTDIR" ]
#../maxtime 1800 ionice -c3 nice -n20 make install DESTDIR="$PWD/$INSTDIR"
#tar czf "$OUTDIR_TMP/ceph.$MACH.tgz" -C "$INSTDIR" .
#rm -rf -- "$INSTDIR"
for dir in $BUILDAREA/RPMS/* 
do
    if [ -d $dir ] ; then
        createrepo $dir
    fi
done
cp -a $BUILDAREA/RPMS $OUTDIR_TMP
rm -rf -- "$BUILDAREA"

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
