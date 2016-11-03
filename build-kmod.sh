#!/bin/sh -x
set -e
export PATH=/usr/bin:/usr/sbin:/usr/sbin:/usr/local/sbin:/sbin:/bin
TARGET="$(cat ../../rsync-target)"
TARGET="$(basename $TARGET)"
REV="$(git rev-parse HEAD)"
VER="$(git describe)"

#Configure creates Makefile needed for clean:
cd /srv/ceph-kmod-rpm/
./configure
make clean
./configure
make
cat results_ceph-kmod/*/*/build.log

rm -Rf /srv/rpm_out/*
mkdir -p /srv/rpm_out/RPMS/x86_64
mkdir -p /srv/rpm_out/RPMS/noarch
mkdir -p /srv/rpm_out/SRPMS
cp -avf /srv/ceph-kmod-rpm/results_ceph-kmod/*/*/*src.rpm /srv/rpm_out/SRPMS
cp -avf /srv/ceph-kmod-rpm/results_ceph-kmod/*/*/*x86_64.rpm /srv/rpm_out/RPMS/x86_64

createrepo /srv/rpm_out/SRPMS
createrepo /srv/rpm_out/RPMS/x86_64
createrepo /srv/rpm_out/RPMS/noarch
cd /srv/autobuild-ceph/gitbuilder.git/build
OUTDIR="../out/output/sha1/$REV"
mkdir -p $OUTDIR
printf '%s\n' "$REV" >"$OUTDIR/sha1"
printf '%s\n' "$VER" >"$OUTDIR/version"
printf '%s\n' "ceph" >"$OUTDIR/name"
cp -avf /srv/rpm_out/SRPMS $OUTDIR/
cp -avf /srv/rpm_out/RPMS/x86_64 $OUTDIR/
cp -avf /srv/rpm_out/RPMS/noarch $OUTDIR/
