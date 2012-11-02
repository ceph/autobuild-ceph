#!/bin/bash -x

set -e

if test -f ./source3/VERSION; then
   vers=3x
else
   vers=4x
fi

CONFIGOPTS="--enable-selftest --with-ldap --with-ads"
REV="$(git rev-parse HEAD)"
if test x"${vers}" = x3x; then
	# version 3 requires a different setup
	cd source3
	./autogen-waf.sh
	DESTDIR_TMP="../install.tmp"
	OUTDIR="../../out/output/sha1/$REV"
	CONFIGOPTS="${CONFIGOPTS} --with-krb5"
else
	DESTDIR_TMP="install.tmp"
	OUTDIR="../out/output/sha1/$REV"
fi


install -d -m0755 -- "$DESTDIR_TMP"

echo "$0: configuring..."
ionice -c3 nice -n20 ./configure ${CONFIGOPTS}

NCPU=$(( 2 * `grep -c processor /proc/cpuinfo` ))

echo "$0: building..."
echo --START-IGNORE-WARNINGS
# filter out idl errors "Unable to determine origin..." to avoid gitbuilder failing
ionice -c3 nice -n20 make -j$NCPU 2> >(grep -v "Unable to determine origin of type") || exit 4

echo "$0: installing..."
ionice -c3 nice -n20 make -j$NCPU install DESTDIR=${DESTDIR_TMP} || exit 4
echo --STOP-IGNORE-WARNINGS

OUTDIR_TMP="${OUTDIR}.tmp"

SMBVERS=$(./bin/smbd --version | sed -e "s|Version ||")

fpm -s dir -t deb -n samba -v ${SMBVERS} -C ${DESTDIR_TMP} usr

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
