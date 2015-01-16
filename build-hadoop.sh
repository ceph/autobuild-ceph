#!/bin/bash -x

set -x
set -e

# maven 3.0.4 on ubuntu 12.04 has some problems. fabfile will install a copy
# of maven 3.1.1 at /srv/apache-maven-3.1.1. setup the necessary pointers.
export M2_HOME=/srv/apache-maven-3.1.1
export M2=$M2_HOME/bin
export PATH=$M2:$PATH

# maven3 creates a local repository of downloaded artificats in the current
# user's home directory. the autobuild-ceph user doesn't have a home
# directory. use a different location for this repository.
export LOCAL_MAVEN_REPO=/tmp/autobuild-ceph-m3home
if [ ! -d "$LOCAL_MAVEN_REPO" ]; then
  mkdir $LOCAL_MAVEN_REPO
fi
export MAVEN_OPTS="-Dmaven.repo.local=$LOCAL_MAVEN_REPO"

# skip tests when building; tests need ceph cluster
mvn package -Dmaven.test.skip=true

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
cp target/*.jar $OUTDIR_TMP
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
printf '%s\n' "cephfs-hadoop" >"$OUTDIR_TMP/name"

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

exit 0
