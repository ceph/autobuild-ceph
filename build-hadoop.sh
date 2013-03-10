#!/bin/bash -x

set -e

HADOOP_ERRORS_IGNORE=""

#using Java6 openjdk for now.
HADOOP_JAVA_HOME="/usr/lib/jvm/java-6-openjdk"
export JAVA_HOME=$HADOOP_JAVA_HOME

#get the libcephfs jar and so files so the build works
GETLIBSOUTPUT=`python ../../get-libcephfs-java-jar.py`

echo $GETLIBSOUTPUT

HADOOP_ERRORS_IGNORE="\
grep -vi \"warning\"" #| \
#grep -v \"is not a pointer or array, skip client functions\" | \
#grep -v \"is a pointer to type 'string', skip client functions\""

REV="$(git rev-parse HEAD)"

DESTDIR_TMP="install.tmp"
OUTDIR="../out/output/sha1/$REV"
CURRENT_DIR=`pwd`

install -d -m0766 -- "$DESTDIR_TMP"

NCPU=$(( 2 * `grep -c processor /proc/cpuinfo` ))

echo "$0: building..."
echo --START-IGNORE-WARNINGS
# filter out idl errors "Unable to determine origin..." to avoid gitbuilder failing
ionice -c3 nice -n20 ant -Divy.default.ivy.user.dir=$CURRENT_DIR examples cephfs cephfs-test 2> >( eval ${HADOOP_ERRORS_IGNORE} ) || exit 4

OUTDIR_TMP="${OUTDIR}.tmp"

install -d -m0755 -- "$OUTDIR_TMP"
tar czf "${OUTDIR_TMP}/hadoop.tgz" -C "${CURRENT_DIR}" .
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"


exit 0

