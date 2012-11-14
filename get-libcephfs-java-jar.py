
import logging
import urllib2
import urlparse
import os
import sys
from subprocess import Popen
from subprocess import PIPE
import glob


logging.basicConfig()
log = logging.getLogger(__name__)
#log = logging.getLogger()
log.setLevel(logging.INFO)

def get_ceph_binary_url(package=None,
                        branch=None, tag=None, sha1=None, dist=None,
                        flavor=None, format=None, arch=None):
    BASE = 'http://gitbuilder.ceph.com/{package}-{format}-{dist}-{arch}-{flavor}/'.format(
        package=package,
        flavor=flavor,
        arch=arch,
        format=format,
        dist=dist
        )

    log.info('BASE: %s' % (BASE))
    if sha1 is not None:
        assert branch is None, "cannot set both sha1 and branch"
        assert tag is None, "cannot set both sha1 and tag"
    else:
        # gitbuilder uses remote-style ref names for branches, mangled to
        # have underscores instead of slashes; e.g. origin_master
        if tag is not None:
            ref = tag
            assert branch is None, "cannot set both branch and tag"
        else:
            if branch is None:
                branch = 'master'
            ref = branch

        sha1_url = urlparse.urljoin(BASE, 'ref/{ref}/sha1'.format(ref=ref))
        log.info('sha1_url: %s' % (sha1_url))
        log.info('Translating ref to sha1 using url %s', sha1_url)
        sha1_fp = urllib2.urlopen(sha1_url)
        sha1 = sha1_fp.read().rstrip('\n')
        sha1_fp.close()

    log.debug('Using %s %s sha1 %s', package, format, sha1)
    bindir_url = urlparse.urljoin(BASE, 'sha1/{sha1}/'.format(sha1=sha1))
    log.info('sha1: %s bindir_url: %s' % (sha1, bindir_url))
    return (sha1, bindir_url)

def main():
    package='ceph'
    format='tarball'
    dist='precise'
    arch='x86_64'
    flavor='basic'
    branch='master'

    sha1,bindir_url = get_ceph_binary_url(package, branch,None,None,dist,flavor,format,arch)
    log.info('sha1: %s bindir_url: %s' % (sha1, bindir_url))

    p1 = Popen(args=[
            'install', '-d', '-m0755', '--', '/tmp/hadooptest/binary'],
            stdout=PIPE)
    p2 = Popen( args=[
            'uname', '-m',], stdin=p1.stdout, stdout=PIPE)
    p3 = Popen( args=[
            'sed', '-e', 's/^/ceph./; s/$/.tgz/',], stdin=p2.stdout, stdout=PIPE)
    p4 = Popen( args=[
            'wget',
            '-nv',
            '-O-',
            '--base={url}'.format(url=bindir_url),
            # need to use --input-file to make wget respect --base
            '--input-file=-',], stdin=p3.stdout, stdout=PIPE)
    p5 = Popen( args=[
            'tar', '-xzf', '-', '-C', '/tmp/hadooptest/binary',],
            stdin=p4.stdout,stdout=PIPE)
    p5.wait()

    log.info('copying libcephfs.so to lib/')

    p1 = Popen(args=[
            'install', '-d', '-m0755', '--', 'lib'],
            stdout=PIPE)

    soFiles = glob.glob('/tmp/hadooptest/binary/usr/local/lib/libcephfs*.so')
    for libFile in soFiles:
        #log.info('soFile: %s' % libFile)
        p1 = Popen(args=[
            'cp', libFile, 'lib/'])
        p1.wait()

    jarFiles = glob.glob('/tmp/hadooptest/binary/usr/local/lib/*.jar')
    for jarFile in jarFiles:
        #log.info('soFile: %s' % libFile)
        p1 = Popen(args=[
            'cp', jarFile, 'lib/'])
        p1.wait()

if __name__ == "__main__":
    main()

