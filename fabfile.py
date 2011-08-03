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

env.roledefs['gitbuilder_ceph_deb'] = [
    'ubuntu@10.3.14.67',
    ]

env.roledefs['gitbuilder_ceph_deb_ndn'] = [
    'ubuntu@10.3.14.65',
    ]

env.roledefs['gitbuilder_apache2_deb_ndn'] = [
    'ubuntu@10.3.14.71',
    ]

env.roledefs['gitbuilder_modfastcgi_deb_ndn'] = [
    'ubuntu@10.3.14.73',
    ]

env.roledefs['gitbuilder_collectd_deb_ndn'] = [
    'ubuntu@10.3.14.74',
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
                sudo('git config remote.{name}.tagopt true'.format(name=name),
                     user='autobuild-ceph')
            sudo('git config remote.origin.tagopt true', user='autobuild-ceph')
        if ignore:
            sudo('install -d -m0755 --owner=autobuild-ceph --group=autobuild-ceph gitbuilder.git/out/ignore')
            for sha in ignore:
                sudo('touch gitbuilder.git/out/ignore/{sha}'.format(sha=sha))
        sudo('install -d -m0755 --owner=autobuild-ceph --group=autobuild-ceph ccache')
        sudo('install -d -m0755 logs')

        sudo('install --owner=root --group=root -m0644 autobuild-ceph.conf /etc/init/autobuild-ceph.conf')
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
    sudo('start autobuild-ceph')

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
    sudo('start autobuild-ceph')

def _deb_builder(git_url, flavor):
    _gitbuilder(
        flavor=flavor,
        git_repo=git_url,
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
            'pbuilder',
            'gnupg',
            'reprepro',
            'devscripts',
            'lintian',
            'flex', 'byacc', # collectd
            ],
        )
    with cd('/srv'):
        if not exists('gnupg'):
            sudo('mkdir gnupg')
        sudo('chown autobuild-ceph:autobuild-ceph gnupg ; chmod 700 gnupg')
        with cd('gnupg'):
            for file in ['pubring.gpg','secring.gpg']:
                if not exists(file):
                    sudo('wget -q -nc http://cephbooter.ceph.dreamhost.com/autobuild-keyring/%s' % (file))
                    sudo('chown autobuild-ceph:autobuild-ceph %s' % (file))
                    sudo('chmod 600 %s' % (file))
        if not exists('ceph-build'):
            sudo('git clone git://ceph.newdream.net/git/ceph-build.git')
        with cd('ceph-build'):
            sudo('git pull')
        if not exists('debian-base'):
            sudo('mkdir debian-base')
        with cd('debian-base'):
            for dist in ['squeeze','natty']:
                if not exists('%s.tgz' % (dist)):
                    sudo('wget -q http://ceph.newdream.net/qa/%s.tgz' % (dist))
        sudo('grep -q autobuild-ceph /etc/sudoers || echo "autobuild-ceph ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers')

@roles('gitbuilder_ceph_deb')
def gitbuilder_ceph_deb():
    _deb_builder('git://ceph.newdream.net/git/ceph.git', 'ceph-deb')
    with cd('/srv/autobuild-ceph'):
        sudo('echo squeeze natty > dists')
    sudo('start autobuild-ceph')

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
    sudo('start autobuild-ceph')

#
# build ndn debs for dho
#
def _ndn_deb_gitbuilder(package, flavor):
    _deb_builder('git://deploy.benjamin.dhobjects.net/%s.git' % package, flavor)
    with cd('/srv/autobuild-ceph'):
        if not exists('rsync-target'):
            sudo("echo dhodeploy@deploy.benjamin.dhobjects.net:out/%s >> rsync-target" % package)
        if not exists('rsync-key'):
            sudo("wget -q http://cephbooter.ceph.dreamhost.com/dhodeploy.key ; mv dhodeploy.key rsync-key")
            sudo("wget -q http://cephbooter.ceph.dreamhost.com/dhodeploy.key.pub ; mv dhodeploy.key.pub rsync-key.pub")
            sudo("chmod 600 rsync-key* ; chown autobuild-ceph.autobuild-ceph rsync-key*")
        sudo('echo squeeze > dists')
        sudo('echo %s > pkgname' % package)
    sudo('start autobuild-ceph')

@roles('gitbuilder_ceph_deb_ndn')
def gitbuilder_ceph_deb_ndn():
    _ndn_deb_gitbuilder('ceph', 'ceph-deb')

@roles('gitbuilder_apache2_deb_ndn')
def gitbuilder_apache2_deb_ndn():
    _ndn_deb_gitbuilder('apache2', 'deb')

@roles('gitbuilder_modfastcgi_deb_ndn')
def gitbuilder_modfastcgi_deb_ndn():
    _ndn_deb_gitbuilder('libapache-mod-fastcgi', 'deb')

@roles('gitbuilder_collectd_deb_ndn')
def gitbuilder_collectd_deb_ndn():
    _ndn_deb_gitbuilder('collectd', 'deb')



@roles('gitbuilder_ceph',
       'gitbuilder_ceph_deb',
       'gitbuilder_ceph_gcov',
       'gitbuilder_kernel',
       # dhodeploy
       'gitbuilder_ceph_deb_ndn',
       'gitbuilder_apache2_deb_ndn',
       'gitbuilder_modfastcgi_deb_ndn',
       'gitbuilder_collectd_deb_ndn',
       )
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
