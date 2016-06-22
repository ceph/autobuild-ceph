#!/bin/bash -x

git submodule foreach 'git clean -fdx && git reset --hard'
rm -rf ceph-object-corpus
rm -rf ceph-erasure-code-corpus
rm -rf src/gmock
rm -rf src/leveldb
rm -rf src/libs3
rm -rf src/mongoose
rm -rf src/civetweb
rm -rf src/rocksdb
rm -rf src/erasure-code/jerasure/gf-complete
rm -rf src/erasure-code/jerasure/jerasure
rm -rf .git/modules/
git clean -fdx && git reset --hard
/srv/git/bin/git submodule sync
/srv/autobuild-ceph/use-mirror.sh
/srv/git/bin/git submodule update --init
git clean -fdx
rm -fr /tmp/*virtualenv*
