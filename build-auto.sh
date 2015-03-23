#!/bin/sh -x

mydir='/srv/autobuild-ceph'

export CEPH_EXTRA_CONFIGURE_ARGS="$CEPH_EXTRA_CONFIGURE_ARGS --without-cryptopp"

if ! hostname | grep -q ^gitbuilder- ; then
    echo "hostname "`hostname`"does not make sense to me; i fail"
    exit 1
fi

if hostname | grep -q -- -clang ; then
    echo "hostname has -clang, will build with CC=clang CXX=clang++"
    export CC=clang
    export CXX=clang++
    # Workaround nfortunate interactions between clang and distcc < 3.2.
    export CCACHE_CPP2=yes
    export CFLAGS="-Qunused-arguments $CFLAGS"
    export CXXFLAGS="-Qunused-arguments $CXXFLAXS"
fi
if hostname | grep -q -- -analyze ; then
    echo "hostname has -analyze, will wrap build with scan-build static analyzer"
    echo "Disabling CCache to ensure complete coverage."
    export CCACHE_DISABLE=yes
    export BUILD_WRAPPER="scan-build -o scan-build-report.tmp/"
fi
if hostname | grep -q -- -asan; then
    echo "hostname has -asan, will build with -fsanitize=address"
    export CFLAGS="-fsanitize=address $CFLAGS"
    export CXXFLAGS="-fsanitize=address $CXXFLAGS"
fi
if hostname | grep -q -- -tsan; then
    echo "hostname has -tsan, will build with -fsanitize=thread"
    export CFLAGS="-fsanitize=thread $CFLAGS"
    export CXXFLAGS="-fsanitize=thread $CXXFLAGS"
fi
if hostname | grep -q -- -wall; then
    echo "hostname has -wall, will build with all possible warnings enabled"
    export CFLAGS="-Wall -Weverything -Wpedantic $CFLAGS"
    export CXXFLAGS="-Wall -Weverything -Wpedantic $CXXFLAGS"
fi
if hostname | grep -q -- -notcmalloc ; then
    echo "hostname has -notcmalloc, will build --without-tcmalloc --without-cryptopp"
    export CEPH_EXTRA_CONFIGURE_ARGS="$CEPH_EXTRA_CONFIGURE_ARGS --without-tcmalloc"
fi
if hostname | grep -q -- -gcov ; then
    echo "hostname has -gcov, will --enable-coverage"
    export CEPH_EXTRA_CONFIGURE_ARGS="$CEPH_EXTRA_CONFIGURE_ARGS --enable-coverage"
fi

if hostname | grep -q -- ceph-deb- ; then
    exec $mydir/build-ceph-deb-native.sh
fi
if hostname | grep -q -- ceph-tarball- ; then
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

