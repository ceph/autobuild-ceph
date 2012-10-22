#!/bin/bash -x
set -e

DISTS=`cat ../../dists`
NAME=`cat ../../pkgname`
KEYID="03C3951A"
pbuilddir="/srv/debian-base"

# Actually build the project

# clear out any $@ potentially passed in
set --

# build the debs
export GNUPGHOME="/srv/gnupg"

VER=`git describe`

mkdir .temp
for f in `find . -maxdepth 1 | tail -n +2 | grep -v '^./.git$' | grep -v '^./.temp$'`
do
    mv $f .temp
done
mv .temp $NAME-$VER

cd $NAME-$VER

dch -v $VER 'autobuilder'
# strip out any .gitignore files (usually there to force empty dirs)
find . -name .gitignore -delete
cd ..
dpkg-source -b $NAME-$VER

yes | debsign -pgpg -sgpg -k$KEYID *.dsc

APTCACHE=/srv/aptcache

for dist in $DISTS
do
    sudo pbuilder --clean
    sudo /srv/ceph-build/update_pbuilder.sh $pbuilddir $dist
    ionice -c3 nice -n20 sudo pbuilder build \
	--binary-arch \
	--distribution $dist \
	--basetgz $pbuilddir/$dist.tgz \
	--buildresult . \
	--debbuildopts "-j`grep -c processor /proc/cpuinfo` -b" \
	*.dsc
done

yes | debsign -pgpg -sgpg -k$KEYID *.changes

REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
printf '%s\n' "$VER" >"$OUTDIR_TMP/version"
printf '%s\n' "$NAME" >"$OUTDIR_TMP/name"

mkdir -p $OUTDIR_TMP/conf
/srv/ceph-build/gen_reprepro_conf.sh $OUTDIR_TMP 03C3951A

for dist in $DISTS
do
    for f in *.changes
    do
	echo file $f
	reprepro --ask-passphrase -b $OUTDIR_TMP -C main --ignore=undefinedtarget --ignore=wrongdistribution include $dist $f
    done
done

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
    /srv/ceph-build/merge_repos.sh combined sha1/*
)

exit 0
