#!/bin/bash -x
set -e -o pipefail

SECONDS=0

function print_runtime() {
    printf "Total run time: %d:%02d\n" $((SECONDS / 60 )) $((SECONDS % 60))
}

bindir=`dirname $0`
. $bindir/reset-modules.sh

echo --START-IGNORE-WARNINGS
[ ! -x install-deps.sh ] || ./install-deps.sh
echo --STOP-IGNORE-WARNINGS

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"

trap "pkill -9 'ceph-(osd|mon)' || true; print_runtime" EXIT

./run-make-check.sh | tee $OUTDIR_TMP/run-make-check.log

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

exit 0
