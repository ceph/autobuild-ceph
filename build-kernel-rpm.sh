#!/bin/sh -x
set -e

git clean -fdx && git reset --hard

REV="$(git rev-parse HEAD)"
VER="$(git describe)"


if [ ! -e Makefile ]; then
    echo "$0: no Makefile, aborting." 1>&2
    exit 3
fi

# Actually build the project

# clear out any $@ potentially passed in
set --

install -d -m0755 build~/out
export HOME=$(pwd)/build~/out

#Clear out RPM tree in build dir.
rm -Rf $HOME/rpmbuild
rpmdev-setuptree

# set up key for signing RPMs
export GNUPGHOME=/srv/gnupg
KEYID=03C3951A
if ! gpg --list-keys 2>&1 | grep $KEYID  > /dev/null
then
    echo "Can not find RPM signing key" 1>&2
    exit 4
fi


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

flavor=`hostname -s | sed -e "s|gitbuilder-\([^-]*\)-\([^-]*\)-\([^-]*\)-\([^-]*\)-\([^-]*\)$|\5|"`
config="../../kernel-config.$flavor"
if [ ! -e "$config" ]; then
    echo "no $config found for flavor $flavor"
    exit 1
fi

# we really need this to get the packages the way we want them, so just enforce it here
(
grep -v '^CONFIG_LOCALVERSION_AUTO=' $config
echo 'CONFIG_LOCALVERSION_AUTO=y'
) > .config



echo "$0: new kernel config options:"
# listnewconfig was contained in v2.6.36, but it seems out/ignore/*
# doesn't work quite right to ignore everything before that, so
# instead just ignore errors coming from it
ionice -c3 nice -n20 make listnewconfig "$@" || :

echo "$0: running make oldconfig..."
yes '' | ionice -c3 nice -n20 make oldconfig "$@"

#echo "$0: applying perf.patch..."
#patch -p1 < ../../perf.patch

echo "$0: building..."
# build dir has ~ suffix so it gets ignored by git and doesn't make
# the source tree look modified (get "+" in version); using subdir out
# so the debs go to e.g.
# build~/linux-image-2.6.38-ceph-00020-g4b2a58a_ceph_amd64.deb

NCPU=$(grep -c processor /proc/cpuinfo)
ionice -c3 nice -n20 make LOCALVERSION=-ceph rpm -j$NCPU "$@" || exit 4


OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
printf '%s\n' "$VER" >"$OUTDIR_TMP/version"
printf '%s\n' "ceph" >"$OUTDIR_TMP/name"


BUILDAREA=$HOME/rpmbuild/

# Sign RPMS
export GNUPGHOME=/srv/gnupg
echo "Signing RPMS ..."
for file in `find ${BUILDAREA} -name "*.rpm"`
do
    /srv/autobuild-ceph/rpm-autosign.exp --define "_gpg_name $KEYID" $file
done

# Create repo index for yum/zypper
for dir in ${BUILDAREA}/SRPMS ${BUILDAREA}/RPMS/*
do
    createrepo ${dir}
    gpg --detach-sign --armor -u $KEYID ${dir}/repodata/repomd.xml
done

# Move RPMS to output repo
for dir in ${BUILDAREA}/SRPMS ${BUILDAREA}/RPMS/*
do
    mv -v ${dir} $OUTDIR_TMP
done
rpmdev-wipetree

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

exit 0
