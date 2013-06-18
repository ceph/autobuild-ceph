#!/bin/sh -x
set -e

# clear out any $@ potentially passed in
set --

DISTS=`cat ../../dists`
RPM_VERSION=`git describe --always | cut -c2- | cut -d- -f1`
RPM_RELEASE=`if expr index $(git describe --always) '-' > /dev/null ; then git describe --always | cut -d- -f2- | tr '-' '.' ; else echo "0"; fi`

VER=${RPM_VERSION}-${RPM_RELEASE}

# Build packages and sign repo
export GNUPGHOME="/srv/gnupg"
./scripts/build-rpm.sh || exit 3

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
printf '%s\n' "$VER" >"$OUTDIR_TMP/version"
printf '%s\n' "ceph-deploy" >"$OUTDIR_TMP/name"

cp -a rpm-repo/*/SRPMS $OUTDIR_TMP
cp -a rpm-repo/*/RPMS/* $OUTDIR_TMP

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

exit 0
