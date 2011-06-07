from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists, append, sed

env.roledefs['gitbuilder_ceph'] = [
    'ubuntu@gitbuilder-i386.ceph.newdream.net',
    'ubuntu@gitbuilder.ceph.newdream.net',
    ]

env.roledefs['gitbuilder_ceph_gcov'] = [
    'ubuntu@gitbuilder-gcov-amd64.ceph.newdream.net',
    ]

env.roledefs['gitbuilder_kernel'] = [
    'ubuntu@gitbuilder-kernel-amd64.ceph.newdream.net',
    ]

def _apt_install(*packages):
    sudo(' '.join(
            [
                'env DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical',
                'apt-get',
                '-q',
                '-o', 'Dpkg::Options::=--force-confnew',
                'install',
                '--no-install-recommends',
                '--assume-yes',
                '--',
                ]
            + list(packages)))

def _gitbuilder(flavor, git_repo, extra_remotes={}, extra_packages=[], ignore=[]):
    """
    extra_remotes will be fetch but not autobuilt. useful for tags.
    """
    # shut down old instance, it exists
    sudo("initctl list|grep -q '^autobuild-ceph\s' && stop autobuild-ceph || :")
    _apt_install(
        'ntp',
        'build-essential',
        'ccache',
        'git',
        'logrotate',
        *extra_packages
        )
    sudo(
        ' '.join([
                'adduser',
                '--system',
                '--home', '/nonexistent',
                '--no-create-home',
                '--gecos', '"Ceph autobuild"',
                '--group',
                '--disabled-password',
                '--disabled-login',
                'autobuild-ceph',
                ]),
        )
    sudo('install -d -m0755 --owner=root --group=root /srv/autobuild-ceph')
    local('git bundle create bundle refs/heads/master')
    put('bundle', 'bundle')
    local('rm -f bundle')
    with cd('/srv/autobuild-ceph'):
        sudo('git init')
        sudo('git pull ~ubuntu/bundle master')
        sudo('ln -sf build-{flavor}.sh build.sh'.format(flavor=flavor))
        if not exists('gitbuilder.git'):
            sudo('rm -rf gitbuilder.git.tmp')
            sudo('git clone https://github.com/tv42/gitbuilder.git gitbuilder.git.tmp')
            with cd('gitbuilder.git.tmp'):
                sudo('git checkout 4c26550e018bcfe397275153a3b66bf30cb53a84')
                sudo('ln -s ../build.sh ./')
                sudo('ln -s ../branches-local ./')
                sudo('git clone {git_repo} build'.format(git_repo=git_repo))
                sudo('chown -R autobuild-ceph:autobuild-ceph build out')
            sudo('mv gitbuilder.git.tmp gitbuilder.git')
        with cd('gitbuilder.git/build'):
            for name, url in extra_remotes.items():
                sudo(
                    'git remote set-url {name} {url} || git remote add {name} {url}'.format(
                        name=name,
                        url=url,
                        ),
                    user='autobuild-ceph',
                    )
        if ignore:
            sudo('install -d -m0755 --owner=autobuild-ceph --group=autobuild-ceph gitbuilder.git/out/ignore')
            for sha in ignore:
                sudo('touch gitbuilder.git/out/ignore/{sha}'.format(sha=sha))
        sudo('install -d -m0755 --owner=autobuild-ceph --group=autobuild-ceph ccache')
        sudo('install -d -m0755 logs')

        sudo('install --owner=root --group=root -m0644 autobuild-ceph.conf /etc/init/autobuild-ceph.conf')
    sudo('start autobuild-ceph')
    run('rm bundle')

@roles('gitbuilder_kernel')
def gitbuilder_kernel():
    _gitbuilder(
        flavor='kernel',
        git_repo='git://ceph.newdream.net/git/ceph-client.git',
        extra_remotes=dict(
            linus='git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux-2.6.git',
            ),
        extra_packages=[
            'fakeroot',
            ],
        ignore=[
            'fbeb94b65cf784ed8bf852131e28c9fb5c4c760f',
            ],
        )

@roles('gitbuilder_ceph')
def gitbuilder_ceph():
    _gitbuilder(
        flavor='ceph',
        git_repo='git://ceph.newdream.net/git/ceph.git',
        extra_packages=[
            'automake',
            'libtool',
            'pkg-config',
            'libboost-dev',
            'libedit-dev',
            'libssl-dev',
            'libcrypto++-dev',
            'libgtkmm-2.4-dev',
            'libfuse-dev',
            'libexpat1-dev',
            'libfcgi-dev',
            'libcurl4-gnutls-dev',
            'libatomic-ops-dev',
            'libgoogle-perftools-dev',
            'libkeyutils-dev',
            'python-pip',
            'python-virtualenv',
            ],
        )

@roles('gitbuilder_ceph_gcov')
def gitbuilder_ceph_gcov():
    _gitbuilder(
        flavor='ceph-gcov',
        git_repo='git://ceph.newdream.net/git/ceph.git',
        extra_packages=[
            'automake',
            'libtool',
            'pkg-config',
            'libboost-dev',
            'libedit-dev',
            'libssl-dev',
            'libcrypto++-dev',
            'libgtkmm-2.4-dev',
            'libfuse-dev',
            'libexpat1-dev',
            'libfcgi-dev',
            'libcurl4-gnutls-dev',
            'libatomic-ops-dev',
            'libgoogle-perftools-dev',
            'libkeyutils-dev',
            'python-pip',
            'python-virtualenv',
            ],
        )

@roles('gitbuilder_ceph', 'gitbuilder_ceph_gcov', 'gitbuilder_kernel')
def gitbuilder_serve():
    _apt_install(
        'thttpd',
        )
    # TODO $ signs in the regexps seem to get passed in as \$, and
    # just don't work the right way; avoid for now, even if that means
    # we could end up doing something very wrong
    sed(
        filename='/etc/default/thttpd',
        before='^ENABLED=no',
        after='ENABLED=yes',
        use_sudo=True,
        )
    sed(
        filename='/etc/thttpd/thttpd.conf',
        before='^user=www-data',
        after='user=autobuild-ceph',
        use_sudo=True,
        )
    sed(
        filename='/etc/thttpd/thttpd.conf',
        before='^dir=/var/www',
        after='dir=/srv/autobuild-ceph/gitbuilder.git/out',
        use_sudo=True,
        )
    sed(
        filename='/etc/thttpd/thttpd.conf',
        before='^cgipat=/cgi-bin/\*',
        after='cgipat=**.cgi',
        use_sudo=True,
        )
    sed(
        filename='/etc/thttpd/thttpd.conf',
        before='^chroot',
        after='#chroot',
        use_sudo=True,
        )
    sudo('/etc/init.d/thttpd restart')
