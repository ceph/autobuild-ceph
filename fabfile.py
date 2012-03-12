from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists, append, sed
import os

env.roledefs['gitbuilder_ceph'] = [
    'ubuntu@gitbuilder-i386.ceph.newdream.net',
    'ubuntu@gitbuilder.ceph.newdream.net',
    'ubuntu@gitbuilder-oneiric-amd64.ceph.newdream.net',
    'ubuntu@gitbuilder-precise-amd64.ceph.newdream.net',
    ]

env.roledefs['gitbuilder_ceph_gcov'] = [
#    'ubuntu@gitbuilder-gcov-amd64.ceph.newdream.net',
    'ubuntu@gitbuilder-oneiric-gcov-amd64.ceph.newdream.net',
    ]

env.roledefs['gitbuilder_ceph_notcmalloc'] = [
#    'ubuntu@10.3.14.76',
    'ubuntu@gitbuilder-oneiric-notcmalloc-amd64.ceph.newdream.net',
    ]

env.roledefs['gitbuilder_kernel'] = [
    'ubuntu@gitbuilder-kernel-amd64.ceph.newdream.net',
    ]

env.roledefs['gitbuilder_ceph_deb'] = [
    'ubuntu@10.3.14.67',
    ]

env.roledefs['gitbuilder_ceph_deb_native'] = [
    'ubuntu@10.3.14.85',
    'ubuntu@10.3.14.86',
    ]

env.roledefs['gitbuilder_ceph_deb_ndn'] = [
    'ubuntu@10.3.14.65',
    ]
env.roledefs['gitbuilder_ceph_deb_oneiric_ndn'] = [
    'ubuntu@10.3.14.87',
    ]
env.roledefs['gitbuilder_ceph_deb_precise_ndn'] = [
    'ubuntu@10.3.14.88',
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

env.roledefs['gitbuilder_kernel_ndn'] = [
    'ubuntu@10.3.14.75',
    ]

env.roledefs['gitbuilder_doc'] = [
    'ubuntu@10.3.14.91',
    ]

def _apt_install(*packages):
    
    sudo("apt-get update")
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

    # sun-java6 is in partner repo.  accept license.
    sudo("echo 'deb http://archive.canonical.com/ubuntu maverick partner' > /etc/apt/sources.list.d/partner.list")
    sudo("echo 'sun-java5-jdk shared/accepted-sun-dlj-v1-1 boolean true' | debconf-set-selections")

    _apt_install(
        'ntp',
        'build-essential',
        'ccache',
        'git',
        'logrotate',
#        'sun-java6-jdk',
        'default-jdk',
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
                sudo('git checkout 65a6317dd153d1c7074527718f1c49ee2858c741')
                sudo('ln -s ../build.sh ./')
                sudo('ln -s ../branches-local ./')
                sudo('git clone {git_repo} build'.format(git_repo=git_repo))
                sudo('chown -R autobuild-ceph:autobuild-ceph build out')
            sudo('mv gitbuilder.git.tmp gitbuilder.git')
        with cd('gitbuilder.git/build'):
            sudo(
                'git remote set-url origin {url}'.format(
                    url=git_repo,
                    ),
                user='autobuild-ceph',
                )
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
        git_repo='https://github.com/ceph/ceph-client.git',
        extra_remotes=dict(
            # linus='git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux-2.6.git',
            linus='https://github.com/torvalds/linux.git',
            korg='git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux-2.6.git',
            ),
        extra_packages=[
            'fakeroot',
            'reprepro',
            ],
        ignore=[
            'fbeb94b65cf784ed8bf852131e28c9fb5c4c760f',
            ],
        )
    sudo('start autobuild-ceph')

@roles('gitbuilder_ceph')
def gitbuilder_ceph():
    _gitbuilder_ceph('https://github.com/ceph/ceph.git','ceph')

def _gitbuilder_ceph(url, flavor):
    _gitbuilder(
        flavor=flavor,
        git_repo=url,
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
            'uuid-dev',
            'python-pip',
            'python-virtualenv',
            'uuid-dev',
            'libaio-dev',
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
            'uuid-dev',
            'libaio-dev',
            'python-pip',
            'python-virtualenv',
            'python-support',
            'pbuilder',
            'gnupg',
            'devscripts',
            'lintian',
            'flex', 'byacc', # collectd
            'debhelper',
            'reprepro',
            'fakeroot',
            ],
        )
    with cd('/srv'):
        if not exists('gnupg'):
            sudo('mkdir gnupg')
        if not exists('aptcache'):
            sudo('mkdir aptcache ; chown autobuild-ceph:autobuild-ceph aptcache')
            
        sudo('chown autobuild-ceph:autobuild-ceph gnupg ; chmod 700 gnupg')
        with cd('gnupg'):
            for file in ['pubring.gpg','secring.gpg']:
                if not exists(file):
                    sudo('wget -q -nc http://cephbooter.ceph.dreamhost.com/autobuild-keyring/%s' % (file))
                    sudo('chown autobuild-ceph:autobuild-ceph %s' % (file))
                    sudo('chmod 600 %s' % (file))
        if not exists('ceph-build'):
            sudo('git clone https://github.com/ceph/ceph-build.git')
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
    _deb_builder('https://github.com/ceph/ceph.git', 'ceph-deb')
    with cd('/srv/autobuild-ceph'):
        sudo('echo squeeze natty > dists')
    sudo('start autobuild-ceph')

@roles('gitbuilder_ceph_deb_native')
def gitbuilder_ceph_deb_native():
    _deb_builder('https://github.com/ceph/ceph.git', 'ceph-deb-native')
    sudo('start autobuild-ceph')

@roles('gitbuilder_ceph_gcov')
def gitbuilder_ceph_gcov():
    _gitbuilder_ceph('https://github.com/ceph/ceph.git', 'ceph-gcov')

@roles('gitbuilder_ceph_notcmalloc')
def gitbuilder_ceph_notcmalloc():
    _gitbuilder_ceph('https://github.com/ceph/ceph.git', 'ceph-notcmalloc')

@roles('gitbuilder_doc')
def gitbuilder_doc():
    _apt_install(
        'libxml2-dev',
        'libxslt-dev',
        'python-dev',
        'python-pip',
        'python-virtualenv',
        'doxygen',
        'ditaa',
        )
    _gitbuilder_ceph('https://github.com/ceph/ceph.git', 'ceph-docs')
    with cd('/srv/autobuild-ceph'):
        if not exists('rsync-target'):
            sudo("echo cephdocs@ceph.newdream.net:/home/sage/ceph.newdream.net/docs.raw >> rsync-target")
        if not exists('rsync-key'):
            sudo("wget -q http://cephbooter.ceph.dreamhost.com/dhodeploy.key ; mv dhodeploy.key rsync-key")
            sudo("wget -q http://cephbooter.ceph.dreamhost.com/dhodeploy.key.pub ; mv dhodeploy.key.pub rsync-key.pub")
            sudo("chmod 600 rsync-key* ; chown autobuild-ceph.autobuild-ceph rsync-key*")


#
# build ndn debs for dho
#
def _sync_out_to_dho(package):
    with cd('/srv/autobuild-ceph'):
        if not exists('rsync-target'):
            sudo("echo dhodeploy@deploy.benjamin.dhobjects.net:out/%s >> rsync-target" % package)
        if not exists('rsync-key'):
            sudo("wget -q http://cephbooter.ceph.dreamhost.com/dhodeploy.key ; mv dhodeploy.key rsync-key")
            sudo("wget -q http://cephbooter.ceph.dreamhost.com/dhodeploy.key.pub ; mv dhodeploy.key.pub rsync-key.pub")
            sudo("chmod 600 rsync-key* ; chown autobuild-ceph.autobuild-ceph rsync-key*")
        sudo("echo emerging@hq.newdream.net > notify-email")

def _ndn_deb_gitbuilder(package, flavor):
    _deb_builder('git://deploy.benjamin.dhobjects.net/%s.git' % package, flavor)
    with cd('/srv/autobuild-ceph'):
        sudo('echo squeeze > dists')
        sudo('echo %s > pkgname' % package)
    sudo('start autobuild-ceph')

@roles('gitbuilder_ceph_deb_ndn')
def gitbuilder_ceph_deb_ndn():
    _ndn_deb_gitbuilder('ceph', 'ceph-deb')
    _sync_out_to_dho('ceph')

@roles('gitbuilder_ceph_deb_oneiric_ndn')
def gitbuilder_ceph_deb_oneiric_ndn():
    _ndn_deb_gitbuilder('ceph', 'ceph-deb-native')
    _sync_out_to_dho('ceph-oneiric')

@roles('gitbuilder_ceph_deb_precise_ndn')
def gitbuilder_ceph_deb_precise_ndn():
    _ndn_deb_gitbuilder('ceph', 'ceph-deb-native')
    _sync_out_to_dho('ceph-precise')

@roles('gitbuilder_apache2_deb_ndn')
def gitbuilder_apache2_deb_ndn():
    _ndn_deb_gitbuilder('apache2', 'deb')

@roles('gitbuilder_modfastcgi_deb_ndn')
def gitbuilder_modfastcgi_deb_ndn():
    _ndn_deb_gitbuilder('libapache-mod-fastcgi', 'deb')

@roles('gitbuilder_collectd_deb_ndn')
def gitbuilder_collectd_deb_ndn():
    _ndn_deb_gitbuilder('collectd', 'deb')

@roles('gitbuilder_kernel_ndn')
def gitbuilder_kernel_ndn():
    _gitbuilder(
        flavor='kernel-raw',
        git_repo='git://deploy.benjamin.dhobjects.net/kernel.git',
        extra_remotes=dict(
            # linus='git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux-2.6.git',
            linus='https://github.com/torvalds/linux.git',
            korg='git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux-2.6.git',
            ),
        extra_packages=[
            'fakeroot',
            ],
        ignore=[
            'fbeb94b65cf784ed8bf852131e28c9fb5c4c760f',
            ],
        )
    _sync_out_to_dho('kernel')
    sudo('start autobuild-ceph')

@roles('gitbuilder_ceph',
       'gitbuilder_ceph_deb',
       'gitbuilder_ceph_deb_native',
       'gitbuilder_ceph_gcov',
       'gitbuilder_kernel',
       # dhodeploy
       'gitbuilder_ceph_deb_ndn',
       'gitbuilder_apache2_deb_ndn',
       'gitbuilder_modfastcgi_deb_ndn',
       'gitbuilder_collectd_deb_ndn',
       'gitbuilder_kernel_ndn',
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


@roles('gitbuilder_ceph',
       'gitbuilder_ceph_deb',
       'gitbuilder_ceph_deb_native',
       'gitbuilder_ceph_gcov',
       'gitbuilder_kernel',
       # dhodeploy
       'gitbuilder_ceph_deb_ndn',
       'gitbuilder_ceph_deb_oneiric_ndn',
       'gitbuilder_ceph_deb_precise_ndn',
       'gitbuilder_apache2_deb_ndn',
       'gitbuilder_modfastcgi_deb_ndn',
       'gitbuilder_collectd_deb_ndn',
       'gitbuilder_kernel_ndn',
       'gitbuilder_doc',
       )
def authorize_ssh_keys():
    keyfile = '.ssh/authorized_keys'
    keydir = os.path.join(
        os.path.dirname(__file__),
        'ssh-keys',
        )
    keys = []
    for filename in os.listdir(keydir):
        if filename.startswith('.'):
            continue
        if not filename.endswith('.pub'):
            continue
        keys.extend(line.rstrip('\n') for line in file(os.path.join(keydir, filename)))
    with hide('running'):
        for key in keys:
            run('grep -q "%s" %s || echo "%s" >> %s' % (key, keyfile, key, keyfile))
