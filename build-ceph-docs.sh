#!/bin/sh -x
set -e

# clear out any $@ potentially passed in
set --

vdir=/tmp/virtualenv-docs admin/build-doc

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
MACH="$(uname -m)"

cp -a build-doc/output/html/* $OUTDIR_TMP

# latest -> stable symlink
ln -s stable $OUTDIR_TMP/latest

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

exit 0
