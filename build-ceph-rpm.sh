#!/bin/sh -x
set -e

# pull down submodules
git submodule foreach 'git clean -fdx && git reset --hard'
rm -rf ceph-object-corpus
rm -rf src/leveldb
rm -rf src/libs3
git submodule update --init
git clean -fdx

DISTS=`cat ../../dists`
TARGET="$(cat ../../rsync-target)"
TARGET="$(basename $TARGET)"
REV="$(git rev-parse HEAD)"
VER="$(git describe)"

# Try to determine branch name
BRANCH=$(../branches.sh -v | grep $REV | awk '{print $2}') || BRANCH="unknown"
BRANCH=$(basename $BRANCH)
echo "Building branch=$BRANCH, sha1=$REV, version=$VER"

# set up key for signing RPMs
export GNUPGHOME=/srv/gnupg
KEYID=03C3951A
if ! gpg --list-keys 2>&1 | grep $KEYID  > /dev/null
then
    echo "Can not find RPM signing key" 1>&2
    exit 4
fi

echo --START-IGNORE-WARNINGS
[ ! -x autogen.sh ] || ./autogen.sh || exit 1
autoconf || true
echo --STOP-IGNORE-WARNINGS
[ ! -x configure ] || ./configure --with-debug --with-radosgw --with-fuse --with-tcmalloc --with-libatomic-ops --with-gtk2 --with-nss || exit 2

if [ ! -e Makefile ]; then
    echo "$0: no Makefile, aborting." 1>&2
    exit 3
fi

# Actually build the project

# clear out any $@ potentially passed in
set --

# enable ccache if it is installed
export CCACHE_DIR="$PWD/../../ccache"
if command -v ccache >/dev/null; then
  if [ ! -e "$CCACHE_DIR" ]; then
    echo "$0: have ccache but cache directory does not exist: $CCACHE_DIR" 1>&2
  else
    set -- CC='ccache gcc' CXX='ccache g++'
  fi
else
  echo "$0: no ccache found, compiles will be slower." 1>&2
fi

#
#  Build Source tarball.  We do this after runing autogen/configure so that
#  ceph.spec has the correct version number filled in.
echo "**** Building Tarball ***"
make dist-bzip2

# Set up build area
BUILDAREA=./rpmbuild
mkdir -p ${BUILDAREA}/SOURCES
mkdir -p ${BUILDAREA}/SRPMS
mkdir -p ${BUILDAREA}/SPECS
mkdir -p ${BUILDAREA}/RPMS
mkdir -p ${BUILDAREA}/BUILD
cp -a ceph-*.tar.bz2 ${BUILDAREA}/SOURCES/.

# Build RPMs
BUILDAREA=`readlink -fn ${BUILDAREA}`   ### rpm wants absolute path
rpmbuild -ba --define "_topdir ${BUILDAREA}" --define "_unpackaged_files_terminate_build 0" ceph.spec

# Create and build an RPM for the repository

cat <<EOF > ${BUILDAREA}/SPECS/ceph-release.spec
Name:           ceph-release       
Version:        1
Release:        0%{?dist}
Summary:        Ceph repository configuration
Group:          System Environment/Base 
License:        GPLv2
URL:            http://gitbuilder.ceph.com/$dist
Source0:        ceph.repo	
#Source0:        RPM-GPG-KEY-CEPH
#Source1:        ceph.repo	
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:	noarch

%description
This package contains the Ceph repository GPG key as well as configuration
for yum and up2date.  

%prep

%setup -q  -c -T
install -pm 644 %{SOURCE0} .
#install -pm 644 %{SOURCE1} .

%build

%install
rm -rf %{buildroot}
#install -Dpm 644 %{SOURCE0} \
#    %{buildroot}/%{_sysconfdir}/pki/rpm-gpg/RPM-GPG-KEY-CEPH
install -dm 755 %{buildroot}/%{_sysconfdir}/yum.repos.d
install -pm 644 %{SOURCE0} \
    %{buildroot}/%{_sysconfdir}/yum.repos.d

%clean
#rm -rf %{buildroot}

%post

%postun 

%files
%defattr(-,root,root,-)
#%doc GPL
%config(noreplace) /etc/yum.repos.d/*
#/etc/pki/rpm-gpg/*

%changelog
* Tue Aug 27 2011 Gary Lowell <glowell@inktank.com> - 1-0
- Initial Package
EOF
#  End of ceph-release.spec file.

# GPG Key
#gpg --export --armor $keyid > ${BUILDAREA}/SOURCES/RPM-GPG-KEY-CEPH
#chmod 644 ${BUILDAREA}/SOURCES/RPM-GPG-KEY-CEPH

# Install ceph.repo file
cat <<EOF > $BUILDAREA/SOURCES/ceph.repo
[Ceph]
name=Ceph packages for \$basearch
baseurl=http://gitbuilder.ceph.com/${TARGET}/ref/${BRANCH}/\$basearch
enabled=1
gpgcheck=1
gpgkey=https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/autobuild.asc

[Ceph-noarch]
name=Ceph noarch packages
baseurl=http://gitbuilder.ceph.com/${TARGET}/ref/${BRANCH}/noarch
enabled=1
gpgcheck=1
gpgkey=https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/autobuild.asc

[ceph-source]
name=Ceph source packages
baseurl=http://gitbuilder.ceph.com/${TARGET}/ref/${BRANCH}/SRPMS
enabled=1
gpgcheck=1
gpgkey=https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/autobuild.asc
EOF
# End of ceph.repo file

rpmbuild -bb --define "_topdir ${BUILDAREA}" --define "_unpackaged_files_terminate_build 0" ${BUILDAREA}/SPECS/ceph-release.spec

# Sign RPMS
export GNUPGHOME=/srv/gnupg
echo "Signing RPMS ..."
for file in `find ${BUILDAREA} -name "*.rpm"`
do
    /srv/autobuild-ceph/rpm-autosign.exp --define "_gpg_name $KEYID" $file
done

# Create repo index for yum/zypper
for dir in ${BUILDAREA}/SRPMS ${BUILDAREA}/RPMS/*
do
    createrepo ${dir}
    gpg --detach-sign --armor -u $KEYID ${dir}/repodata/repomd.xml
done

#REV="$(git rev-parse HEAD)"
OUTDIR="../out/output/sha1/$REV"
OUTDIR_TMP="${OUTDIR}.tmp"
install -d -m0755 -- "$OUTDIR_TMP"
printf '%s\n' "$REV" >"$OUTDIR_TMP/sha1"
printf '%s\n' "$VER" >"$OUTDIR_TMP/version"
printf '%s\n' "ceph" >"$OUTDIR_TMP/name"
#mkdir -p $OUTDIR_TMP/conf

#MACH="$(uname -m)"
#INSTDIR="inst.tmp"
#[ ! -e "$INSTDIR" ]
#../maxtime 1800 ionice -c3 nice -n20 make install DESTDIR="$PWD/$INSTDIR"
#tar czf "$OUTDIR_TMP/ceph.$MACH.tgz" -C "$INSTDIR" .
#rm -rf -- "$INSTDIR"

# Copy RPMS to output repo
for dir in ${BUILDAREA}/SRPMS ${BUILDAREA}/RPMS/*
do
    cp -a ${dir} $OUTDIR_TMP
done

rm -rf -- "$BUILDAREA"

# put our temp files inside .git/ so ls-files doesn't see them
git ls-files --modified >.git/modified-files
if [ -s .git/modified-files ]; then
    rm -rf "$OUTDIR_TMP"
    echo "error: Modified files:" 1>&2
    cat .git/modified-files 1>&2
    exit 6
fi

git ls-files --exclude-standard --others >.git/added-files
if [ -s .git/added-files ]; then
    rm -rf "$OUTDIR_TMP"
    echo "error: Added files:" 1>&2
    cat .git/added-files 1>&2
    exit 7
fi

# we're successful, the files are ok to be published; try to be as
# atomic as possible about replacing potentially existing OUTDIR
if [ -e "$OUTDIR" ]; then
    rm -rf -- "$OUTDIR.old"
    mv -- "$OUTDIR" "$OUTDIR.old"
fi
mv -- "$OUTDIR_TMP" "$OUTDIR"
rm -rf -- "$OUTDIR.old"

exit 0
