#!/bin/sh -x
set -e

git clean -fdx

export DIST=`lsb_release -sc`
export GNUPGHOME="/srv/gnupg" 
echo "VER is $VER"

# clear out any $@ potentially passed in
set --

# build the debs
RELEASEDIR=/tmp/cdep-release.$$
mkdir -p $RELEASEDIR/out~
rm -rf $RELEASEDIR/out~/* || true
cp -a ../build/* $RELEASEDIR/out~

(cd $RELEASEDIR/out~ ; ./scripts/build-debian.sh)


REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
printf '%s\n' "$VER" >"$OUTDIR_TMP/version"
printf '%s\n' "ceph" >"$OUTDIR_TMP/name"

cp -a $RELEASEDIR/out~/debian-repo/* $OUTDIR_TMP/.
rm -rf $RELEASEDIR

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
