#!/bin/sh -x
set -e

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

flavor=`hostname | sed -e "s|gitbuilder-\([^-]*\)-\([^-]*\)-\([^-]*\)-\([^-]*\)-\([^-]*\)$|\5|"`
config="../../kernel-config.$flavor"
if [ ! -e "$config" ]; then
    echo "no $config found for flavor $flavor"
    exit 1
fi

install -d -m0755 build~/out
(
    # we really need this to get the packages the way we want them, so just enforce it here
    grep -v '^CONFIG_LOCALVERSION_AUTO=' $config
    echo 'CONFIG_LOCALVERSION_AUTO=y'
    ) >build~/out/.config

echo "$0: new kernel config options:"
# listnewconfig was contained in v2.6.36, but it seems out/ignore/*
# doesn't work quite right to ignore everything before that, so
# instead just ignore errors coming from it
ionice -c3 nice -n20 make O=build~/out listnewconfig "$@" || :

echo "$0: running make oldconfig..."
yes '' | ionice -c3 nice -n20 make O=build~/out oldconfig "$@"

#echo "$0: applying perf.patch..."
#patch -p1 < ../../perf.patch

echo "$0: building..."
# build dir has ~ suffix so it gets ignored by git and doesn't make
# the source tree look modified (get "+" in version); using subdir out
# so the debs go to e.g.
# build~/linux-image-2.6.38-ceph-00020-g4b2a58a_ceph_amd64.deb

NCPU=$(( 2 * `grep -c processor /proc/cpuinfo` ))
ionice -c3 nice -n20 make O=build~/out LOCALVERSION=-ceph deb-pkg -j$NCPU "$@" || exit 4

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
mv -- build~/*.deb "$OUTDIR_TMP/"

# build a simple repro in OUTDIR_TMP too
DIST="squeeze"    # this could be anything
(
    cd $OUTDIR_TMP

    install -d -m0755 -- "conf"
    cat > conf/distributions <<EOF
Codename: $DIST
Suite: stable
Components: main
Architectures: i386 amd64 source
Origin: New Dream Network
Description: Kernel autobuilds
DebIndices: Packages Release . .gz .bz2
DscIndices: Sources Release .gz .bz2
EOF

    for f in image headers;
    do
	reprepro -b . includedeb $DIST linux-$f-*.deb

	# make a consistently named symlink
	dbg=`ls linux-$f-*.deb | grep -- -dbg`
	normal=`ls linux-$f-*.deb | grep -v -- -dbg`
	ln -s $normal linux-$f.deb
	ln -s $dbg linux-$f-dbg.deb
    done
)

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

exit 0
