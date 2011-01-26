from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists, append

env.roledefs['gitbuilder'] = [
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

@roles('gitbuilder')
def gitbuilder():
    _apt_install(
        'build-essential',
        'git',
        'logrotate',
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
    with cd('/srv/autobuild-ceph'):
        sudo('git init')
        sudo('git pull ~ubuntu/bundle master')
        sudo('./setup autobuild-ceph')
    run('rm bundle')
