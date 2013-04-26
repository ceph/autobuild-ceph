#!/bin/sh

cd /srv/autobuild-ceph/gitbuilder.git/build

for b in `git branch -a | grep origin`; do
	touch ../out/pass/`git rev-parse $b`
done

for s in `git show-ref --tags -d | awk '{print $1}'`; do
	touch ../out/pass/$s
done

