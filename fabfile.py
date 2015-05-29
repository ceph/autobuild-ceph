from fabric.context_managers import cd, hide, settings
from fabric.api import *
from fabric.contrib.files import exists, append, sed
import os
import sys

env.roledefs['gitbuilder_auto'] = [
    'ubuntu@gitbuilder-ceph-deb-trusty-amd64-blkin.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-deb-precise-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-deb-precise-amd64-notcmalloc.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-deb-trusty-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-deb-trusty-amd64-notcmalloc.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-deb-trusty-i386-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-deb-wheezy-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-tarball-precise-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-tarball-precise-i386-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-tarball-trusty-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-tarball-trusty-i386-basic.front.sepia.ceph.com',
    ]

env.roledefs['gitbuilder_ceph_rpm'] = [
    'ubuntu@gitbuilder-ceph-rpm-centos6-5-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-rpm-centos7-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-rpm-fedora20-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-rpm-rhel6-5-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-ceph-rpm-rhel6-5-amd64-notcmalloc.front.sepia.ceph.com',
#    'ubuntu@gitbuilder-ceph-rpm-rhel7-amd64-basic.front.sepia.ceph.com',
#    'ubuntu@gitbuilder-ceph-rpm-rhel7-amd64-notcmalloc.front.sepia.ceph.com',
    ]

# kernels
env.roledefs['gitbuilder_kernel'] = [
    'ubuntu@gitbuilder-kernel-deb-precise-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-kernel-deb-precise-amd64-debug.front.sepia.ceph.com',
#    'ubuntu@gitbuilder-kernel-deb-quantal-armv7l-basic.front.sepia.ceph.com',
    ]
env.roledefs['gitbuilder_kernel_rpm'] = [
    'ubuntu@gitbuilder-kernel-rpm-centos6-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-kernel-rpm-fedora20-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-kernel-rpm-rhel6-amd64-basic.front.sepia.ceph.com',
    'ubuntu@gitbuilder-kernel-rpm-rhel7-amd64-basic.front.sepia.ceph.com',
    ]

# special
env.roledefs['gitbuilder_doc'] = [
    'ubuntu@ursula.front.sepia.ceph.com',
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


#################


def _rpm_install(*packages):
    lsb = sudo("lsb_release -d")
    if '7.' in lsb:
        sudo("rpm -qa | grep epel-release || rpm -Uvh http://apt-mirror.front.sepia.ceph.com/non-repo-rpms/epel-release-7-0.2.noarch.rpm")
    if '6.' in lsb:
        sudo("rpm -qa | grep epel-release || rpm -Uvh http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm")
    # This will update to the newest release of the distro IE centos 6.3 to centos 6.5, etc...
    # sudo("yum --assumeyes --quiet update")
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
    _ceph_extras()
    sudo("apt-get update")
    sudo(' '.join(
            [
                'env DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical',
                'apt-get',
                '-q',
                '-y',
                '-o', 'Dpkg::Options::=--force-confnew',
                'install',
#                '--no-install-recommends',
#                '--assume-yes',
                '--',
                ]
            + list(packages)))

def _apt_reinstall_for_backports(*packages):
    if 'x86_64' not in env.host_string:
        return
    sudo("mkdir -p /srv/extras-backports")
    sudo("rm -f /srv/extras-backports/*")
    sudo("apt-get clean")
    sudo(' '.join(
            [
                'env DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical',
                'apt-get',
                '-q',
                '-y',
                '-o', 'Dpkg::Options::=--force-confnew',
                'install',
                '--reinstall',
#                '--no-install-recommends',
#                '--assume-yes',
                '--',
            ]
            + list(packages)))
    debcache = []
    for package in (list(packages)):
        debcache.append('/var/cache/apt/archives/{package}*'.format(package=package))

    sudo(' '.join(
            [
                'cp',
                '-avf'
            ]
            + debcache +
            [
                '/srv/extras-backports'
            ]))


def _gem_install(*packages):
    sudo('gem install ' + ' '.join(list(packages)))

def _rh_gitbuilder(flavor, git_repo, extra_remotes={}, extra_packages=[], ignore=[], branches_local_name='branches-local',branch_to_bundle='master'): 
    """
    extra_remotes will be fetch but not autobuilt. useful for tags.
    """
    gitbuilder_commit='master'
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
                '--home', '/home/autobuild-ceph',
                '--comment', '"Ceph autobuild"',
                '--user-group',
                #'--disabled-password',
                #'--disabled-login',
                'autobuild-ceph',
                ]),
            )
        with cd('/home/autobuild-ceph'):
            sudo('lsb_release -d -s | grep CentOS | grep -q release\ 7 && echo "%dist .el7" > .rpmmacros')

    sudo('install -d -m0755 --owner=root --group=root /srv/autobuild-ceph')
    local('git bundle create bundle refs/heads/{branch_to_bundle}'.format(branch_to_bundle=branch_to_bundle))
    put('bundle', 'bundle')
    local('rm -f bundle')
    with cd('/srv/autobuild-ceph'):
        sudo('git init')
        sudo('test -d /home/ubuntu || ln -sf /home/centos /home/ubuntu')
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
                sudo('chown -R autobuild-ceph:autobuild-ceph out')
            sudo('mv gitbuilder.git.tmp gitbuilder.git')
        with cd('gitbuilder.git'):
            if not exists('build'):
                sudo('git clone {git_repo} build'.format(git_repo=git_repo))
                sudo('chown -R autobuild-ceph:autobuild-ceph build')
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
                with cd('/srv'):
                    if not exists('gnupg'):
                        sudo('mkdir gnupg')
                    sudo('chown autobuild-ceph:autobuild-ceph gnupg ; chmod 700 gnupg')
                    with cd('gnupg'):
                        if not exists('pubring.gpg'):
                            # put doesn't honor cd() for some reason
                            put('gnupg/pubring.gpg')
                            put('gnupg/secring.gpg')
                            put('trustdb.gpg')
                            sudo("mv /home/ubuntu/*.gpg ./")
                            sudo('chown autobuild-ceph:autobuild-ceph pubring.gpg secring.gpg trustdb.gpg')
                            sudo('chmod 600 pubring.gpg secring.gpg trustdb.gpg')
        with cd('/srv/autobuild-ceph'):
            if ignore:
                sudo('install -d -m0755 --owner=autobuild-ceph --group=autobuild-ceph gitbuilder.git/out/ignore')
                for sha in ignore:
                    sudo('touch gitbuilder.git/out/ignore/{sha}'.format(sha=sha))
            sudo('install -d -m0755 --owner=autobuild-ceph --group=autobuild-ceph ccache')
            sudo('install -d -m0755 logs')

            sudo('install --owner=root --group=root -m0755 autobuild-ceph.init /etc/init.d/autobuild-ceph')
    run('rm bundle')
    sudo('chown -R autobuild-ceph:autobuild-ceph /srv/autobuild-ceph')
    install_git()

def _gitbuilder(flavor, git_repo, extra_remotes={}, extra_packages=[], ignore=[], branches_local_name='branches-local', branch_to_bundle='master'):
    """
    extra_remotes will be fetch but not autobuilt. useful for tags.
    """
    gitbuilder_commit='master'
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

    #  Reinstall for packport deps.
    _apt_reinstall_for_backports(
        'libleveldb1',
        'libcurl3-gnutls'
        )

    sudo(
        ' '.join([
                'adduser',
                '--system',
                '--home', '/nonexistent',
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
                sudo('chown -R autobuild-ceph:autobuild-ceph out')
            sudo('mv gitbuilder.git.tmp gitbuilder.git')
        with cd('gitbuilder.git'):
            if not exists('build'):
                sudo('git clone {git_repo} build'.format(git_repo=git_repo))
                sudo('chown -R autobuild-ceph:autobuild-ceph build')
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

        sudo('install --owner=root --group=root -m0644 autobuild-ceph.conf /etc/init/autobuild-ceph.conf ; install --owner=root --group=root -m0755 autobuild-ceph.init /etc/init.d/autobuild-ceph ; exit 0')
    run('rm bundle')
    sudo('chown -R autobuild-ceph:autobuild-ceph /srv/autobuild-ceph')
    install_git()

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

def _kernel_rpm_deps():
    _rpm_install(
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
        'libblkid',
        'libblkid-devel',
        'gcc-c++',
        'expat',
        'expat-devel',
        'sharutils',
        'gnupg',
        'expect',
        'yasm',
        'rpm-sign',
        'createrepo',
        'rpmdevtools',
        'yum-utils',
        'bc',
        'zlib-devel'
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



@roles('gitbuilder_kernel_rpm')
def gitbuilder_kernel_rpm():
    _kernel_rpm_deps()
    _rh_gitbuilder(
        flavor='kernel-rpm',
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
    _sync_to_gitbuilder('kernel','rpm','basic')
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
        git_repo='git://apt-mirror.front.sepia.ceph.com/samba.git',
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
    _gitbuilder_ceph('ceph')
    _sync_to_gitbuilder('ceph', 'tarball', 'basic')

def _gitbuilder_ceph(flavor):
    _gitbuilder(
        flavor=flavor,
        git_repo='https://github.com/ceph/ceph.git',
        extra_remotes=dict(
            ci='https://github.com/ceph/ceph-ci.git',
        ),
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
            'xfslibs-dev',
            'libfuse-dev',
            'libexpat1-dev',
            'libfcgi-dev',
            'libcurl4-gnutls-dev',
            'libatomic-ops-dev',
            'libgoogle-perftools-dev',
            'libkeyutils-dev',
            'uuid-dev',
            'libblkid-dev',
            'libbz2-dev',
            'libudev-dev',
            'python-pip',
            'python-requests',
            'python-virtualenv',
            'python-argparse',
            'libaio-dev',
            'libxml2-dev',
            'libnss3-dev',
            'junit4',
            'xmlstarlet',
            'yasm',
            'python-nose',
            'cryptsetup-bin',
            # for kernel build, perf etc
            'flex',
            'bison',
            'libdw-dev',
            'binutils-dev',
            'libnewt-dev',
            'libsnappy-dev',
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
            'xfslibs-dev',
            'libfuse-dev',
            'libexpat1-dev',
            'libfcgi-dev',
            'libcurl4-gnutls-dev',
            'libatomic-ops-dev',
            'libgoogle-perftools-dev',
            'libkeyutils-dev',
            'uuid-dev',
            'uuid-runtime',
            'libblkid-dev',
            'libbz2-dev',
            'libudev-dev',
            'libaio-dev',
            'libxml2-dev',
            'libnss3-dev',
            'xmlstarlet',
            'python-pip',
            'python-requests',
            'python-virtualenv',
            'python-support',
            'python-argparse',
            'python-sphinx',
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
            'libsnappy-dev',
            ],
        )
    _deb_install_extras()

@roles('gitbuilder_auto')
def gitbuilder_auto():
    _deb_builder('https://github.com/ceph/ceph.git', 'auto')
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')
    _sync_to_gitbuilder_from_hostname()

@roles('gitbuilder_ceph_rpm')
def gitbuilder_ceph_rpm():
    _gitbuilder_ceph_rpm('https://github.com/ceph/ceph.git', 'auto')
    hostname = run('hostname -s')
    flavor = hostname.split('-')[-1]
    _sync_to_gitbuilder('ceph', 'rpm', flavor)

def _gitbuilder_ceph_rpm(url, flavor):
    if '6-' in run('hostname -s'):
        sphinx = 'python-sphinx10'
    else:
        sphinx = 'python-sphinx'
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
            'libblkid',
            'libblkid-devel',
            'libudev',
            'libudev-devel',
            'bzip2-devel',
            'fcgi',
            'fcgi-devel',
            'xfsprogs',
            'xfsprogs-devel',
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
            'xmlstarlet',
            'nss-devel',
            'gtkmm24',
            'gtkmm24-devel',
            'junit4',
            'sharutils',
            'gnupg',
            'expect',
            'yasm',
            'python-nose',
            'hdparm',
            'rpm-sign',
            'createrepo',
            'leveldb-devel',
            'snappy-devel',
            'zlib-devel',
            'python-requests',
            'python-virtualenv',
            'python-argparse',
            sphinx,
            'lttng-ust-devel',
            'libbabeltrace-devel',
            'cryptsetup',
            ]
        )
    with cd('/srv/autobuild-ceph'):
        sudo('echo centos6 > dists')
    sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

@roles('gitbuilder_doc')
def gitbuilder_doc():
    _apt_install(
        'libxml2-dev',
        'libxslt-dev',
        'python-dev',
        'python-pip',
        'python-virtualenv',
        'python-sphinx',
        'doxygen',
        'ditaa',
        'graphviz',
        'ant',
        )
    _gitbuilder_ceph('ceph-docs')
    with cd('/srv/autobuild-ceph'):
        if not exists('rsync-target'):
            sudo("echo ubuntu@ursula.front.sepia.ceph.com:/var/docs.raw > rsync-target")
        if not exists('rsync-key'):
            put("rsync-key")
            put("rsync-key.pub")
            sudo("mv /home/ubuntu/rsync-key* ./")
            sudo("chmod 600 rsync-key* ; chown autobuild-ceph.autobuild-ceph rsync-key*")

def _sync_to_gitbuilder(package, format, flavor):
    dist_or_codename = '`lsb_release -s -c`'
    if format == 'rpm':
        dist_or_codename = '`lsb_release -s -i | tr A-Z a-z``lsb_release -s -r | sed -s "s;\.;_;g"`'
    with cd('/srv/autobuild-ceph'):
        # fugliness
        sudo("echo gitbuilder@gitbuilder.ceph.com:gitbuilder.ceph.com/{package}-{format}-{dist_or_codename}-`uname -m`-{flavor} > rsync-target".format(
            package=package,
            format=format,
            dist_or_codename=dist_or_codename,
            flavor=flavor))
        sudo('sed -i "s;redhatenterpriseserver;rhel;g" rsync-target')
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

@roles('gitbuilder_modfastcgi_deb_oneiric')
def gitbuilder_modfastcgi_deb_oneiric():
    _deb_builder('git://ceph.newdream.net/git/libapache-mod-fastcgi-2.4.7.git', 'deb')
    with cd('/srv/autobuild-ceph'):
        sudo('echo oneiric > dists')
        sudo('echo libapache-mod-fastcgi > pkgname')
    _sync_to_gitbuilder('libapache-mod-fastcgi','deb','basic')

@roles('gitbuilder_modfastcgi_deb_precise')
def gitbuilder_modfastcgi_deb_precise():
    _deb_builder('git://ceph.newdream.net/git/libapache-mod-fastcgi-2.4.7-0910052141.git', 'deb')
    with cd('/srv/autobuild-ceph'):
        sudo('echo precise > dists')
        sudo('echo libapache-mod-fastcgi > pkgname')
    _sync_to_gitbuilder('libapache-mod-fastcgi','deb','basic')

@roles('gitbuilder_ceph_deb',
       'gitbuilder_ceph_gcov',
       'gitbuilder_kernel',
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

def gitbuilder_serve_rpm():
    # kill any remaining thttpd's in favor of lighttpd.  Do this before
    # installing lighttpd so that lighttpd can start without errors
    # (albeit with the default config)

    _rpm_install(
        'lighttpd',
        )

    put('lighttpd.conf', '/tmp/lighttpd.conf')

    with settings(hide('warnings'), warn_only = True):
        same = sudo('diff -q /etc/lighttpd/lighttpd.conf /tmp/lighttpd.conf')
        if same.succeeded == False:
            sudo('/etc/init.d/lighttpd stop')
            sudo('systemctl stop lighttpd')
            sudo('mv /etc/lighttpd/lighttpd.conf /etc/lighttpd.orig')
            sudo('mv /tmp/lighttpd.conf /etc/lighttpd/lighttpd.conf')
            sudo('chown -R autobuild-ceph:autobuild-ceph /var/log/lighttpd')
            sudo('/etc/init.d/lighttpd start')
            sudo('systemctl start lighttpd')
            sudo('systemctl enable lighttpd')
            sudo('chkconfig --add lighttpd')
        else:
            sudo('chown -R autobuild-ceph:autobuild-ceph /var/log/lighttpd')
            sudo('rm /tmp/lighttpd.conf')
            sudo('/etc/init.d/lighttpd start')
            sudo('systemctl start lighttpd')


@roles('gitbuilder_ceph',
       'gitbuilder_ceph_gcov',
       'gitbuilder_ceph_notcmalloc',
       'gitbuilder_kernel',
       'gitbuilder_ceph_deb',
       'gitbuilder_ceph_rpm',
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

def install_git():
    # Install newer git from source
    # for bug fixes.

    git_version = '1.8.5.3'
    if not exists('/srv/git/bin'):
        sudo ('mkdir -p /srv/git/src')    
        with cd('/srv/git/src'):
            sudo('wget -O /srv/git/src/git-{version}.tar.gz http://ceph.com/qa/git-{version}.tar.gz'.format(version=git_version))
            sudo('tar xzf /srv/git/src/git-{version}.tar.gz'.format(version=git_version))
            sudo('rm -f /srv/git/src/git-{version}.tar.gz'.format(version=git_version))
            with cd('/srv/git/src/git-{version}'.format(version=git_version)):
                sudo('./configure --prefix=/srv/git/')
                sudo('make -j8')
                sudo('make install')
                sudo('rm -Rf /srv/src/git-{version}'.format(version=git_version))

def _ceph_extras():
    sudo('lsb_release -c | grep -q -e precise -e quantal -e raring && ' +
    'echo deb http://ceph.com/packages/ceph-extras/debian $(lsb_release -sc) main ' +
    '| sudo tee /etc/apt/sources.list.d/ceph-extras.list || echo Ceph-Extras unsupported')
