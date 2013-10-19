from fabric.context_managers import cd, hide, settings
from fabric.api import *
from fabric.contrib.files import exists, append, sed
import os
import sys

env.roledefs['gitbuilder_ceph'] = [
#    'ubuntu@gitbuilder-i386.ceph.newdream.net',
#    'ubuntu@gitbuilder.ceph.newdream.net',
    'ubuntu@gitbuilder-oneiric-amd64.front.sepia.ceph.com',
    'ubuntu@gitbuilder-precise-amd64.front.sepia.ceph.com',
    'ubuntu@gitbuilder-precise-i386.front.sepia.ceph.com',
    'ubuntu@gitbuilder-squeeze-amd64.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_ceph_gcov'] = [
#    'ubuntu@gitbuilder-gcov-amd64.ceph.newdream.net',
#    'ubuntu@gitbuilder-oneiric-gcov-amd64.ceph.newdream.net',
    'ubuntu@gitbuilder-precise-gcov-amd64.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_ceph_notcmalloc'] = [
#    'ubuntu@10.3.14.76',
#    'ubuntu@gitbuilder-oneiric-notcmalloc-amd64.ceph.newdream.net',
    'ubuntu@gitbuilder-precise-notcmalloc-amd64.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_kernel'] = [
#    'ubuntu@gitbuilder-kernel-amd64.ceph.newdream.net',
#    'ubuntu@gitbuilder-precise-kernel-amd64.front.sepia.ceph.com',
    'ubuntu@gitbuilder-kernel-deb-precise-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-kernel-deb-precise-amd64-debug.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_ceph_deb'] = [
#    'ubuntu@10.3.14.67',
    ]

env.roledefs['gitbuilder_ceph_rpm'] = [
    ]

env.roledefs['gitbuilder_ceph_deb_native'] = [
    'ubuntu@gitbuilder-oneiric-deb-amd64.front.sepia.ceph.com',
    'ubuntu@gitbuilder-precise-deb-amd64.front.sepia.ceph.com',
    'ubuntu@gitbuilder-natty-deb-amd64.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-deb-wheezy-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-squeeze-deb-amd64.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_auto'] = [
    'ubuntu@gitbuilder-ceph-deb-precise-amd64-notcmalloc.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-deb-raring-amd64.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-tarball-raring-amd64.front.sepia.ceph.com',
    ]

#env.roledefs['gitbuilder_ceph_deb_ndn'] = [
#    'ubuntu@10.3.14.65',
#    ]
#env.roledefs['gitbuilder_ceph_deb_oneiric_ndn'] = [
#    'ubuntu@10.3.14.87',
#    ]
env.roledefs['gitbuilder_ceph_deb_precise_ndn'] = [
    'ubuntu@gitbuilder-precise-ceph-deb-ndn.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_doc'] = [
    'ubuntu@gitbuilder-doc.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_samba'] = [
    'ubuntu@gitbuilder-samba-deb-precise-amd64.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_hadoop'] = [
    'ubuntu@gitbuilder-precise-hadoop-amd64.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_apache_hadoop'] = [
    'ubuntu@gitbuilder-precise-apache-hadoop-amd64.front.sepia.ceph.com',
    ]

#env.roledefs['gitbuilder_apache2_deb_oneiric'] = [
#    'ubuntu@10.3.14.92',
#    ]
#env.roledefs['gitbuilder_modfastcgi_deb_oneiric'] = [
#    'ubuntu@10.3.14.93',
#    ]
#env.roledefs['gitbuilder_apache2_deb_precise'] = [
#    'ubuntu@10.3.14.94',
#    ]
#env.roledefs['gitbuilder_modfastcgi_deb_precise'] = [
#    'ubuntu@10.3.14.95',
#    ]


## ndn
#env.roledefs['gitbuilder_apache2_deb_ndn'] = [
#    'ubuntu@10.3.14.71',
#    ]

#env.roledefs['gitbuilder_modfastcgi_deb_ndn'] = [
#    'ubuntu@10.3.14.73',
#    ]

#env.roledefs['gitbuilder_collectd_deb_ndn'] = [
#    'ubuntu@10.3.14.74',
#    ]

#env.roledefs['gitbuilder_kernel_ndn'] = [
#    'ubuntu@10.3.14.75',
#    ]

def _rpm_install(*packages):
    
    sudo("rpm -qa | grep epel-release ||rpm -Uvh http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-7.noarch.rpm")
    sudo("yum --assumeyes --quiet update")
    sudo(' '.join(
            [
                'yum',
                '--quiet',
                '--assumeyes',
                'install',
                '--',
                ]
            + list(packages)))


def _apt_add_testing_repo(branch):
    sudo('wget -q -O- https://raw.github.com/ceph/ceph/master/keys/autobuild.asc | sudo apt-key add -')
    sudo('echo deb http://gitbuilder.ceph.com/ceph-deb-$(lsb_release -sc)-x86_64-basic/ref/{branch} $(lsb_release -sc) main | sudo tee /etc/apt/sources.list.d/ceph.list'.format(branch=branch))

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

def _gem_install(*packages):
    sudo('gem install ' + ' '.join(list(packages)))

def _rh_gitbuilder(flavor, git_repo, extra_remotes={}, extra_packages=[], ignore=[], branches_local_name='branches-local',branch_to_bundle='master'): 
    """
    extra_remotes will be fetch but not autobuilt. useful for tags.
    """
    gitbuilder_commit='113df5c1be9564c7dc6a5cbc5a70eb61f0c28216'
    gitbuilder_origin='git://github.com/ceph/gitbuilder.git'

    sudo("initctl list|grep -q '^autobuild-ceph\s' && stop autobuild-ceph || /etc/init.d/autobuild-ceph stop || :")
    #
    #  Install needed packages
    _rpm_install(
        'ntp',
        'ccache',
        'git',
        'logrotate',
        'rsync',
        'pkgconfig',
        'tar',
        *extra_packages
        )
    #
    #  Create autobuild-ceph user
    with settings(warn_only=True):
        sudo(
            ' '.join([
                'adduser',
                '--system',
                '--home', '/nonexistent',
                '--no-create-home',
                '--comment', '"Ceph autobuild"',
                '--user-group',
                #'--disabled-password',
                #'--disabled-login',
                'autobuild-ceph',
                ]),
            )

    sudo('install -d -m0755 --owner=root --group=root /srv/autobuild-ceph')
    local('git bundle create bundle refs/heads/{branch_to_bundle}'.format(branch_to_bundle=branch_to_bundle))
    put('bundle', 'bundle')
    local('rm -f bundle')
    with cd('/srv/autobuild-ceph'):
        sudo('git init')
        sudo('test -d /home/ubuntu || ln -sf /home/centos /home/ubuntu')
        sudo('git pull /home/ubuntu/bundle {branch_to_bundle}'.format(branch_to_bundle=branch_to_bundle))
        sudo('ln -sf build-{flavor}.sh build.sh'.format(flavor=flavor))
        if not exists('gitbuilder.git'):
            sudo('rm -rf gitbuilder.git.tmp')
            sudo('git clone %s gitbuilder.git.tmp' % gitbuilder_origin)
            with cd('gitbuilder.git.tmp'):
                sudo('git checkout %s' % gitbuilder_commit)
                sudo('ln -s ../build.sh ./')
                if branches_local_name != 'branches-local':
                    sudo('mv ./branches-local ./branches-local-orig')
                sudo('ln -s ../{branches_local_name} ./branches-local'.format(branches_local_name=branches_local_name))
                sudo('git clone {git_repo} build'.format(git_repo=git_repo))
                sudo('chown -R autobuild-ceph:autobuild-ceph build out')
            sudo('mv gitbuilder.git.tmp gitbuilder.git')
        else:
            with cd('gitbuilder.git'):
                sudo('git remote set-url origin %s' % gitbuilder_origin)
                sudo('git fetch origin')
                sudo('git reset --hard %s' % gitbuilder_commit)
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

        sudo('install --owner=root --group=root -m0644 autobuild-ceph.conf /etc/init/autobuild-ceph.conf || install --owner=root --group=root -m0755 autobuild-ceph.init /etc/init.d/autobuild-ceph')
    run('rm bundle')

def _gitbuilder(flavor, git_repo, extra_remotes={}, extra_packages=[], ignore=[], branches_local_name='branches-local', branch_to_bundle='master'):
    """
    extra_remotes will be fetch but not autobuilt. useful for tags.
    """
    gitbuilder_commit='7110ef374378abd377d03c0757e3dac4fc314d69'
    gitbuilder_origin='git://github.com/ceph/gitbuilder.git'

    # shut down old instance, it exists
    sudo("initctl list|grep -q '^autobuild-ceph\s' && stop autobuild-ceph || /etc/init.d/autobuild-ceph stop || :")

    # sun-java6 is in partner repo.  accept license.
    #sudo("echo 'deb http://archive.canonical.com/ubuntu maverick partner' > /etc/apt/sources.list.d/partner.list")
    #sudo("echo 'sun-java5-jdk shared/accepted-sun-dlj-v1-1 boolean true' | debconf-set-selections")

    _apt_install(
        'ntp',
        'build-essential',
        'ccache',
        'git',
        'logrotate',
#        'sun-java6-jdk',
        'default-jdk',
        'javahelper',
        'rsync',
        'pbuilder',
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
    local('git bundle create bundle refs/heads/{branch_to_bundle}'.format(branch_to_bundle=branch_to_bundle))
    put('bundle', 'bundle')
    local('rm -f bundle')
    with cd('/srv/autobuild-ceph'):
        sudo('git init')
        # blarg
        sudo('test -d /home/ubuntu || ln -sf /home/debian /home/ubuntu')
        sudo('git pull /home/ubuntu/bundle {branch_to_bundle}'.format(branch_to_bundle=branch_to_bundle))
        sudo('ln -sf build-{flavor}.sh build.sh'.format(flavor=flavor))
        brand_new = False
        if not exists('gitbuilder.git'):
            brand_new = True
            sudo('rm -rf gitbuilder.git.tmp')
            sudo('git clone %s gitbuilder.git.tmp' % gitbuilder_origin)
            with cd('gitbuilder.git.tmp'):
                sudo('git checkout %s' % gitbuilder_commit)
                sudo('ln -s ../build.sh ./')
                if branches_local_name != 'branches-local':
                    sudo('mv ./branches-local ./branches-local-orig')
                sudo('ln -s ../{branches_local_name} ./branches-local'.format(branches_local_name=branches_local_name))
                sudo('git clone {git_repo} build'.format(git_repo=git_repo))
                sudo('chown -R autobuild-ceph:autobuild-ceph build out')
            sudo('mv gitbuilder.git.tmp gitbuilder.git')
        else:
            with cd('gitbuilder.git'):
                sudo('git remote set-url origin %s' % gitbuilder_origin)
                sudo('git fetch origin')
                sudo('git reset --hard %s' % gitbuilder_commit)
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
            if brand_new:
                sudo('/srv/autobuild-ceph/mark_all_as_pass.sh',
                     user='autobuild-ceph')
        if ignore:
            sudo('install -d -m0755 --owner=autobuild-ceph --group=autobuild-ceph gitbuilder.git/out/ignore')
            for sha in ignore:
                sudo('touch gitbuilder.git/out/ignore/{sha}'.format(sha=sha))
        sudo('install -d -m0755 --owner=autobuild-ceph --group=autobuild-ceph ccache')
        sudo('install -d -m0755 logs')

        sudo('install --owner=root --group=root -m0644 autobuild-ceph.conf /etc/init/autobuild-ceph.conf || install --owner=root --group=root -m0755 autobuild-ceph.init /etc/init.d/autobuild-ceph')
    run('rm bundle')

def _deb_install_extras():
    with cd('/srv'):
        if not exists('gnupg'):
            sudo('mkdir gnupg')
        if not exists('aptcache'):
            sudo('mkdir aptcache ; chown autobuild-ceph:autobuild-ceph aptcache')

        sudo('chown autobuild-ceph:autobuild-ceph gnupg ; chmod 700 gnupg')
        with cd('gnupg'):
            if not exists('pubring.gpg'):
                # put doesn't honor cd() for some reason
                put('gnupg/pubring.gpg')
                put('gnupg/secring.gpg')
                sudo("mv /home/ubuntu/*.gpg ./")
                sudo('chown autobuild-ceph:autobuild-ceph pubring.gpg secring.gpg')
                sudo('chmod 600 pubring.gpg secring.gpg')
        if not exists('ceph-build'):
            sudo('git clone https://github.com/ceph/ceph-build.git')
        with cd('ceph-build'):
            sudo('git pull')
        if not exists('debian-base'):
            sudo('mkdir debian-base')
        with cd('debian-base'):
            for dist in ['squeeze','oneiric']:
                if not exists('%s.tgz' % (dist)):
                    sudo('wget -q http://ceph.newdream.net/qa/%s.tgz' % (dist))
        sudo('grep -q autobuild-ceph /etc/sudoers || echo "autobuild-ceph ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers')


def _kernel_deps():
    _apt_install(
        # kernel tools
        'bison',
        'flex',
        'asciidoc',
        'libdw-dev',
        'libnewt-dev',
        'xmlto',
        'libgtk2.0-dev',
	'libunwind-setjmp0-dev',
	'libunwind7-dev',
	'libaudit-dev',
	'binutils-dev',
	'python-dev',
        )

@roles('gitbuilder_kernel')
def gitbuilder_kernel():
    _kernel_deps()
    _gitbuilder(
        flavor='auto',
        git_repo='https://github.com/ceph/ceph-client.git',
        extra_remotes=dict(
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
    _sync_to_gitbuilder_from_hostname()
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

def _hadoop_deps():
    #_apt_add_testing_repo('master')
    _apt_install(
		'openjdk-6-jdk',
        'ant',
        'automake',
        'libtool',
        )

def _samba_deps():
    _apt_add_testing_repo('master')
    _apt_install(
        'build-essential',
        'libacl1-dev',
        'libattr1-dev',
        'libblkid-dev',
        'libgnutls-dev',
        'libreadline-dev',
        'python-dev',
        'python-dnspython',
        'gdb',
        'pkg-config',
        'libpopt-dev',
        'libldap2-dev',
        'dnsutils',
        'libbsd-dev',
        'attr',
        'krb5-user',
        'ruby1.8-dev',
        'rubygems',
        'libcephfs-dev',
        'libncurses-dev',
        'dpkg-sig',
        )

    _gem_install('fpm')

@roles('gitbuilder_samba')
def gitbuilder_samba():
    _samba_deps()
    _gitbuilder(
        flavor='samba',
        git_repo='git://git.samba.org/samba.git',
        extra_packages=[
            'fakeroot',
            'reprepro',
            ],
        branches_local_name='branches-local-samba',
        )
    _deb_install_extras()
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')
    _sync_to_gitbuilder('samba', 'deb', 'basic')

@roles('gitbuilder_hadoop')
def gitbuilder_hadoop():
    _hadoop_deps()
    _gitbuilder(
        flavor='hadoop',
        git_repo='https://github.com/ceph/hadoop-common.git',
        extra_packages=[
            'fakeroot',
            'reprepro',
            ],
        branches_local_name='branches-local-hadoop',
        )
    _sync_to_gitbuilder('hadoop', 'jar', 'basic')
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

@roles('gitbuilder_apache_hadoop')
def gitbuilder_apache_hadoop():
    _hadoop_deps()
    _gitbuilder(
        flavor='apache-hadoop',
        git_repo='git://git.apache.org/hadoop-common.git',
        extra_packages=[
            'fakeroot',
            'reprepro',
            ],
        branches_local_name='branches-local-apache-hadoop',
        )
    _sync_to_gitbuilder('apache-hadoop', 'jar', 'basic')
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

@roles('gitbuilder_ceph')
def gitbuilder_ceph():
    _gitbuilder_ceph('https://github.com/ceph/ceph.git','ceph')
    _sync_to_gitbuilder('ceph', 'tarball', 'basic')

def _gitbuilder_ceph(url, flavor):
    _gitbuilder(
        flavor=flavor,
        git_repo=url,
        extra_packages=[
            'automake',
            'libtool',
            'pkg-config',
            'libboost-dev',
            'libboost-thread-dev',
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
            'libxml2-dev',
            'libnss3-dev',
            'junit4',
            'yasm',
            'python-nose',
            # for kernel build, perf etc
            'flex',
            'bison',
            'libdw-dev',
            'binutils-dev',
            'libnewt-dev',
            ],
        )
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

def _deb_builder(git_url, flavor, extra_remotes={}):
    _gitbuilder(
        flavor=flavor,
        git_repo=git_url,
        extra_remotes=extra_remotes,
        extra_packages=[
            'automake',
            'libtool',
            'pkg-config',
            'libboost-dev',
            'libboost-thread-dev',
            'libboost-program-options-dev',
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
            'libxml2-dev',
            'libnss3-dev',
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
            'junit4',
            'sharutils',
            'libdistro-info-perl',  # needed by raring
            'libboost-system-dev',
            'libleveldb-dev',
            'yasm',
            'python-nose',
            ],
        )
    _deb_install_extras()

@roles('gitbuilder_ceph_deb')
def gitbuilder_ceph_deb():
    _deb_builder('https://github.com/ceph/ceph.git', 'ceph-deb')
    with cd('/srv/autobuild-ceph'):
        sudo('echo squeeze natty > dists')
    _sync_to_gitbuilder('ceph', 'deb', 'basic')
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

@roles('gitbuilder_ceph_deb_native')
def gitbuilder_ceph_deb_native():
    _deb_builder('https://github.com/ceph/ceph.git', 'ceph-deb-native')
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')
    _sync_to_gitbuilder('ceph', 'deb', 'basic')

@roles('gitbuilder_auto')
def gitbuilder_auto():
    _deb_builder('https://github.com/ceph/ceph.git', 'auto')
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')
    _sync_to_gitbuilder_from_hostname()

@roles('gitbuilder_ceph_rpm')
def gitbuilder_ceph_rpm():
    _gitbuilder_ceph_rpm('https://github.com/ceph/ceph.git', 'ceph-rpm')
    _sync_to_gitbuilder('ceph', 'rpm', 'basic')

def _gitbuilder_ceph_rpm(url, flavor):
    _rh_gitbuilder(
        flavor=flavor,
        git_repo=url,
        extra_packages=[
            'pkgconfig',
            'automake',
            'autoconf',
            'make',
            'libtool',
            'libaio',
            'libaio-devel',
            'libedit',
            'libedit-devel',
            'libuuid',
            'libuuid-devel',
            'fcgi',
            'fcgi-devel',
            'fuse',
            'fuse-libs',
            'fuse-devel',
            'gperftools-devel',
            'mod_fcgid',
            'keyutils-libs-devel',
            'cryptopp-devel',
            'gcc-c++',
            'expat',
            'expat-devel',
            'libatomic_ops-devel',
            'boost',
            'boost-devel',
            'boost-program-options',
            'libcurl',
            'libcurl-devel',
            'rpm-build',
            'libxml2-devel',
            'nss-devel',
            'gtkmm24',
            'gtkmm24-devel',
            'junit4',
            'sharutils',
            'gnupg',
            'expect',
            'yasm',
            'python-nose',
            ]
        )
    with cd('/srv/autobuild-ceph'):
        sudo('echo centos6 > dists')
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

@roles('gitbuilder_ceph_gcov')
def gitbuilder_ceph_gcov():
    _gitbuilder_ceph('https://github.com/ceph/ceph.git', 'ceph-gcov')
    _sync_to_gitbuilder('ceph', 'tarball', 'gcov')

@roles('gitbuilder_ceph_notcmalloc')
def gitbuilder_ceph_notcmalloc():
    _gitbuilder_ceph('https://github.com/ceph/ceph.git', 'ceph-notcmalloc')
    _sync_to_gitbuilder('ceph', 'tarball', 'notcmalloc')

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
        'graphviz',
        'ant',
        )
    _gitbuilder_ceph('https://github.com/ceph/ceph.git', 'ceph-docs')
    with cd('/srv/autobuild-ceph'):
        if not exists('rsync-target'):
            sudo("echo cephdocs@ceph.newdream.net:/home/ceph_site/ceph.com/docs.raw > rsync-target")
        if not exists('rsync-key'):
            put("rsync-key")
            put("rsync-key.pub")
            sudo("mv /home/ubuntu/rsync-key* ./")
            sudo("chmod 600 rsync-key* ; chown autobuild-ceph.autobuild-ceph rsync-key*")

def _sync_to_gitbuilder(package, format, flavor):
    with cd('/srv/autobuild-ceph'):
        # fugliness
        sudo("echo gitbuilder@gitbuilder.ceph.com:gitbuilder.ceph.com/%s-%s-`lsb_release -s -c`-`uname -m`-%s > rsync-target" % (package,format,flavor))
        _sync_rsync_keys()

def _sync_rsync_keys():
    if not exists('rsync-key'):
        if not os.path.exists('rsync-key'):
            print >> sys.stderr, 'Required rsync keys to gitbuilder.ceph.com missing!'
            sys.exit(1)
        # for whatever reason, put doesn't seem to honor cd and use_sudo fails
        put("rsync-key")
        put("rsync-key.pub")
        sudo("mv /home/ubuntu/rsync-key* ./")
        sudo("chmod 600 rsync-key* ; chown autobuild-ceph.autobuild-ceph rsync-key*")

def _sync_to_gitbuilder_from_hostname():
    with cd('/srv/autobuild-ceph'):
        # fugliness
        sudo("echo gitbuilder@gitbuilder.ceph.com:gitbuilder.ceph.com/`hostname | cut --delimiter=- -f 2`-`hostname | cut --delimiter=- -f 3`-`lsb_release -s -c`-`uname -m`-`hostname | cut --delimiter=- -f 6` > rsync-target")
        _sync_rsync_keys()

#
# build ndn debs for dho
#
def _sync_out_to_dho(package, notify):
    with cd('/srv/autobuild-ceph'):
        if not exists('rsync-target'):
            sudo("echo dhodeploy@deploy.benjamin.dhobjects.net:out/%s > rsync-target" % package)
        if not exists('rsync-notify'):
            sudo("echo %s > rsync-notify" % notify)
        if not exists('rsync-key'):
            put("rsync-key")
            put("rsync-key.pub")
            sudo("mv /home/ubuntu/rsync-key* ./")
            sudo("chmod 600 rsync-key* ; chown autobuild-ceph.autobuild-ceph rsync-key*")
        sudo("echo emerging@hq.newdream.net > notify-email")

def _ndn_deb_gitbuilder(package, flavor, extra_remotes={}):
    _deb_builder('git://deploy.benjamin.dhobjects.net/%s.git' % package, flavor,
                 extra_remotes=extra_remotes)
    with cd('/srv/autobuild-ceph'):
        sudo('echo squeeze > dists')
        sudo('echo %s > pkgname' % package)
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

@roles('gitbuilder_ceph_deb_ndn')
def gitbuilder_ceph_deb_ndn():
    _ndn_deb_gitbuilder('ceph', 'ceph-deb',
                        extra_remotes={'gh': 'git://github.com/ceph/ceph.git'})
    _sync_out_to_dho('ceph', 'emerging@hq.newdream.net')

@roles('gitbuilder_ceph_deb_oneiric_ndn')
def gitbuilder_ceph_deb_oneiric_ndn():
    _ndn_deb_gitbuilder('ceph', 'ceph-deb-native',
                        extra_remotes={'gh': 'git://github.com/ceph/ceph.git'})
    _sync_out_to_dho('ceph-oneiric', 'emerging@hq.newdream.net')

@roles('gitbuilder_ceph_deb_precise_ndn')
def gitbuilder_ceph_deb_precise_ndn():
    _ndn_deb_gitbuilder('ceph', 'ceph-deb-native',
                        extra_remotes={'gh': 'git://github.com/ceph/ceph.git'})
    _sync_out_to_dho('ceph-precise', 'emerging@hq.newdream.net')

@roles('gitbuilder_apache2_deb_oneiric')
def gitbuilder_apache2_deb_oneiric():
    _deb_builder('git://ceph.newdream.net/git/apache2-2.2.20.git', 'deb')
    with cd('/srv/autobuild-ceph'):
        sudo('echo oneiric > dists')
        sudo('echo apache2 > pkgname')
    _sync_to_gitbuilder('apache2','deb','basic')

@roles('gitbuilder_modfastcgi_deb_oneiric')
def gitbuilder_modfastcgi_deb_oneiric():
    _deb_builder('git://ceph.newdream.net/git/libapache-mod-fastcgi-2.4.7.git', 'deb')
    with cd('/srv/autobuild-ceph'):
        sudo('echo oneiric > dists')
        sudo('echo libapache-mod-fastcgi > pkgname')
    _sync_to_gitbuilder('libapache-mod-fastcgi','deb','basic')

@roles('gitbuilder_apache2_deb_precise')
def gitbuilder_apache2_deb_precise():
    _deb_builder('git://ceph.newdream.net/git/apache2-2.2.22.git', 'deb')
    with cd('/srv/autobuild-ceph'):
        sudo('echo precise > dists')
        sudo('echo apache2 > pkgname')
    _sync_to_gitbuilder('apache2','deb','basic')

@roles('gitbuilder_modfastcgi_deb_precise')
def gitbuilder_modfastcgi_deb_precise():
    _deb_builder('git://ceph.newdream.net/git/libapache-mod-fastcgi-2.4.7-0910052141.git', 'deb')
    with cd('/srv/autobuild-ceph'):
        sudo('echo precise > dists')
        sudo('echo libapache-mod-fastcgi > pkgname')
    _sync_to_gitbuilder('libapache-mod-fastcgi','deb','basic')

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
    _kernel_deps()
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
    _sync_out_to_dho('kernel', 'emerging@hq.newdream.net')
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

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
       'gitbuilder_samba',
       'gitbuilder_hadoop'
       )
def gitbuilder_serve():
    # kill any remaining thttpd's in favor of lighttpd.  Do this before
    # installing lighttpd so that lighttpd can start without errors
    # (albeit with the default config)

    sudo('/etc/init.d/thttpd stop || true')

    _apt_install(
        'lighttpd',
        )

    put('lighttpd.conf', '/tmp/lighttpd.conf')

    with settings(hide('warnings'), warn_only = True):
	same = sudo('diff -q /etc/lighttpd/lighttpd.conf /tmp/lighttpd.conf')
	if same.succeeded == False:
	    sudo('/etc/init.d/lighttpd stop')
	    sudo('mv /etc/lighttpd/lighttpd.conf /etc/lighttpd.orig')
	    sudo('mv /tmp/lighttpd.conf /etc/lighttpd/lighttpd.conf')
	    sudo('chown -R autobuild-ceph:autobuild-ceph /var/log/lighttpd')
	    sudo('/etc/init.d/lighttpd start')
	else:
	    sudo('rm /tmp/lighttpd.conf')
	    sudo('/etc/init.d/lighttpd start')

@roles('gitbuilder_ceph',
       'gitbuilder_ceph_gcov',
       'gitbuilder_ceph_notcmalloc',
       'gitbuilder_kernel',
       'gitbuilder_ceph_deb',
       'gitbuilder_ceph_rpm',
       'gitbuilder_ceph_deb_native',
       'gitbuilder_ceph_deb_precise_ndn',
       'gitbuilder_doc',
       'gitbuilder_samba',
       'gitbuilder_hadoop',
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
