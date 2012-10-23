#!/bin/sh -x

set -e

cd source3
./autogen-waf.sh

DESTDIR_TMP="../install.tmp"

install -d -m0755 -- "$DESTDIR_TMP"

echo "$0: configuring..."
ionice -c3 nice -n20 ./configure --with-ads --with-krb5 --with-ldap

NCPU=$(( 2 * `grep -c processor /proc/cpuinfo` ))

echo "$0: building..."
ionice -c3 nice -n20 make -j$NCPU || exit 4

echo "$0: installing..."
ionice -c3 nice -n20 make -j$NCPU install DESTDIR=${DESTDIR_TMP} || exit 4

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"

SMBVERS=$(./bin/smbd --version | sed -e "s|Version ||")

fpm -s dir -t deb -n samba -v ${SMBVERS} -C ${DESTDIR_TMP} -d libldap2-dev -d libkrb5-dev usr

install -d -m0755 -- "$OUTDIR_TMP"
mv *deb "$OUTDIR_TMP/"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"

DIST="squeeze"
(
    cd $OUTDIR_TMP

    install -d -m0755 -- "conf"
    cat > conf/distributions <<EOF
Codename: $DIST
Suite: stable
Components: main
Architectures: i386 amd64 source
Origin: New Dream Network
Description: samba autobuilds
DebIndices: Packages Release . .gz .bz2
DscIndices: Sources Release .gz .bz2
EOF

    for f in *.deb;
    do
	reprepro -b . includedeb $DIST $f
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
