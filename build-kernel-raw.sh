#!/bin/sh -x
set -e

if [ ! -e Makefile ]; then
    echo "$0: no Makefile, aborting." 1>&2
    exit 3
fi

# Actually build the project

NPROCS=`grep -c processor /proc/cpuinfo`

# clear out any $@ potentially passed in
set --

# enable ccache if it is installed
export CCACHE_DIR="$PWD/../../ccache"
if command -v ccache >/dev/null; then
  if [ ! -e "$CCACHE_DIR" ]; then
    echo "$0: have ccache but cache directory does not exist: $CCACHE_DIR" 1>&2
  else
    CCACHE_PATH="$PATH"
    for d in /usr/{lib64,lib,lib32,libexec}/ccache{,/bin} ; do
      test -d "$d" && test -x "$d/g++" && CCACHE_PATH="$d:$PATH" && break
    done
    export PATH="$CCACHE_PATH"
  fi
else
  echo "$0: no ccache found, compiles will be slower." 1>&2
fi

(
    # we really need this to get the packages the way we want them, so just enforce it here
    grep -v '^CONFIG_LOCALVERSION_AUTO=' .config
    echo 'CONFIG_LOCALVERSION_AUTO=y'
    ) >.config.new
mv .config.new .config

echo "$0: new kernel config options:"
# listnewconfig was contained in v2.6.36, but it seems out/ignore/*
# doesn't work quite right to ignore everything before that, so
# instead just ignore errors coming from it
ionice -c3 nice -n20 make listnewconfig "$@" || :

echo "$0: running make oldconfig..."
yes '' | ionice -c3 nice -n20 make oldconfig "$@"

echo "$0: building..."
# build dir has ~ suffix so it gets ignored by git and doesn't make
# the source tree look modified (get "+" in version); using subdir out
# so the debs go to e.g.
# build~/linux-image-2.6.38-ceph-00020-g4b2a58a_ceph_amd64.deb
ionice -c3 nice -n20 make -j${NPROCS} "$@" || exit 4

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
mv -- arch/x86/boot/bzImage $OUTDIR_TMP/
mv -- vmlinux $OUTDIR_TMP/
mv -- System.map $OUTDIR_TMP/
cp -- .config $OUTDIR_TMP/config
cp -- include/config/kernel.release $OUTDIR_TMP/version

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

exit 0
