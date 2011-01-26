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
        if not exists('gitbuilder.git'):
            sudo('rm -rf gitbuilder.git.tmp')
            sudo('git clone https://github.com/tv42/gitbuilder.git gitbuilder.git.tmp')
            with cd('gitbuilder.git.tmp'):
                sudo('git checkout 4c26550e018bcfe397275153a3b66bf30cb53a84')
                sudo('ln -s ../build.sh ./')
                sudo('ln -s ../branches-local ./')
                sudo('git clone git://ceph.newdream.net/git/ceph.git build')
                sudo('chown -R autobuild-ceph:autobuild-ceph build out')
            sudo('mv gitbuilder.git.tmp gitbuilder.git')
        sudo('install -d -m0755 logs')
        sudo('install -m0644 /dev/null logs/stdout.log')
        sudo('install -m0644 /dev/null logs/stderr.log')

        sudo('install --owner=root --group=root -m0644 autobuild-ceph.conf /etc/init/autobuild-ceph.conf')
    sudo('start autobuild-ceph')
    run('rm bundle')
