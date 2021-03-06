#!/bin/sh -x

mydir='/srv/autobuild-ceph'

export CEPH_EXTRA_CONFIGURE_ARGS="$CEPH_EXTRA_CONFIGURE_ARGS --without-cryptopp"
export CEPH_EXTRA_CMAKE_ARGS

if ! hostname | grep -q ^gitbuilder- ; then
    echo "hostname "`hostname`"does not make sense to me; i fail"
    exit 1
fi

if hostname | grep -q -- -notcmalloc ; then
    echo "hostname has -notcmalloc"
    export CEPH_EXTRA_CONFIGURE_ARGS="$CEPH_EXTRA_CONFIGURE_ARGS --without-tcmalloc"
    export CEPH_EXTRA_CMAKE_ARGS="$CEPH_EXTRA_CMAKE_ARGS -DALLOCATOR=libc"
else
    export CEPH_EXTRA_CONFIGURE_ARGS="$CEPH_EXTRA_CONFIGURE_ARGS --with-tcmalloc"
    export CEPH_EXTRA_CMAKE_ARGS="$CEPH_EXTRA_CMAKE_ARGS -DALLOCATOR=tcmalloc"
fi
if hostname | grep -q -- -gcov ; then
    echo "hostname has -gcov"
    export CEPH_EXTRA_CONFIGURE_ARGS="$CEPH_EXTRA_CONFIGURE_ARGS --enable-coverage"
fi

if hostname | grep -q -- ceph-deb- ; then
    exec $mydir/build-ceph-deb-native.sh
fi
if hostname | grep -q -- ceph-tarball- ; then
    if hostname | grep -q -- -cmake ; then
	exec $mydir/build-ceph-cmake.sh
    fi
    exec $mydir/build-ceph.sh
fi
if hostname | grep -q -- ceph-rpm- ; then
    exec $mydir/build-ceph-rpm.sh
fi

hostname | sed -e "s|gitbuilder-\([^-]*\)-\([^-]*\)-.*$|\1 \2|" > /tmp/$$
read -r builder type < /tmp/$$
if [ -n "$builder" -a -n "$type" ]; then
    if test -f $mydir/build-${builder}-${type}.sh; then
        exec $mydir/build-${builder}-${type}.sh
    fi
fi

echo "i don't know what to do with hostname "`hostname`
exit 1

