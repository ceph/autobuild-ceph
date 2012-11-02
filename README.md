# Autobuilds for the Ceph Project

This is a set of build scripts and a fabric file (fabfile.py)
that allows remote deployment and setup of autobuilds for the
ceph project.

## Quick Start

To get started quickly, the following commands will allow you to setup
and start a ceph autobuild on a given host:

	> git clone git@github.com:ceph/autobuild-ceph.git
	> cd autobuild-ceph
	> sudo apt-get install fabric
	> fab gitbuilder_ceph:host=<username>@<hostname>

That performs the appropriate setup on the host to run ceph builds
continuously.

An upstart service named autobuild-ceph gets created on the host that runs
the autobuilder. Use ``sudo stop autobuild-ceph``, ``sudo start
autobuild-ceph`` on the autobuilder host to manage the autobuilder.

To get a list of other available commands, run ``fab -l``.  Note
that fabric expects to be able to ssh to the host you specify, so you 
should already have ssh keys setup for that host.  If
no host is specified, fabric will deploy to the set of hosts for the role associated with
that command.  Also note that the gitbuilder\_ceph command sets up the
autobuilder to deploy the binary packages to the package server.  This
requires the rsync keys (rsync-key and rsync-key.pub) for the package
server be located in your current directory (fabric copies them to the deployment
host).  You can get the keys from someone who already has access.

## Deploying autobuilders with fabric

Fabric allows you to run commands to deploy a specific autobuilder
build script on a node, setup ssh keys, and start the web server
for displaying gitbuilder results.

Fabric uses the fabfile.py file in your current working directory.
The fabfile.py is essentially a set of roles and commands.  The
``gitbuilder\_ceph`` command runs the defined gitbuilder\_ceph
function, sending remote commands to each of the hosts defined by
the role(s) associated with that function.
A role defines a list of hosts where a command will be run, for example,
the ``gitbuilder\_ceph`` role (happens to share the same name as the
command) runs the gitbuilder\_ceph command on all all the VMs defined
in that role.

## Implementing your own autobuild

### Create a build script

For your project called __foo__, create a build script ``build-foo.sh``
in the top-level directory that executes the steps to build the foo project.
The script should assume that the current working directory is the top-level
checkout of the __foo__ repository.  Gitbuilder controls cloning the foo repository
and checking out to the desired branch.  Gitbuilder checks the output of this
script for lines that have "error:" or "warning:" messages, and reports those
as such.  If you need to ignore some warnings in the output of your build script,
you can add the following echo statements around your build commands:

	echo --START-IGNORE-WARNINGS
	# build commands here...
	./configure whatever
	echo --STOP-IGNORE-WARNINGS

To limit which branches are built by gitbuilder, a branches-local script should
be installed by the fabfile.py function/command for ``gitbuilder\_foo`` that outputs
only the branches that gitbuilder should build.  See the branches-local script
in this repo for an example that outputs the branches to build for the ceph autobuilder.

### Modify the fabfile.py

First add a role definition called 'gitbuilder\_foo' to include a new function with a set of roles.
The set of roles should include all the roles where you want to deploy your foo autobuilder.  A
basic gitbuilder function and role definition looks like this:

	@roles('gitbuilder_foo')
	def gitbuilder_foo():
		_apt_install(
			'make'
			'libfoodep-dev',
		)
		_gitbuilder(
			flavor='foo',
			git_repo='http://github.com/ceph/foo.git',
			extra_packages=[
				'fakeroot',
				'reprepro',
				],
		)
	_sync_to_gitbuilder('foo', 'deb', 'basic')
	sudo('start autobuild-ceph || /etc/init.d/autobuild-ceph start')

Note that the flavor you specify to the \_gitbuilder() function determines how your build script
is chosen as the build script to run by the gitbuilder tool.  The extra\_packages specify packages
that need to be installed in order to create a deb repository for your autobuilt packages, and
the \_sync\_to\_gitbuilder() function performs setup to rsync the binary packages created by the build
to the repo hosting server.  In order to perform the sync, rsync keys are required.  You can get the
keys from another user and place them in your checkout directory.

As a final step, define a role that lists the hosts you want to deploy the foo autobuilder onto.  By
convention, the role shares the same name as the command, i.e. gitbuilder\_foo.  See the other env.roledef
lists at the top of the fabfile for examples.

### Deploying your autobuild

Once you've created your build script and modified the fabfile.py to include your gitbuilder command
and roles, you should be able to deploy your autobuild with:

	fab gitbuilder_foo

### Setting up the Autobuild web server

A command to setup lighttpd and point it at the autobuild results exists in the fabfile.py.  To start the web
server, you can simply do:

	fab gitbuilder_serve:role=gitbuilder_foo

### How autobuilder works

Running fabric with the autobuild-ceph fabfile.py does a clone of the autobuild-ceph repo into /srv/ on the host(s), installs
other needed packages and creates a user to run autobuilder.  It then sets up gitbuilder, checking out that
repo into /srv/autobuild-ceph/gitbuilder.git, and
creates a symlink from the build script you specified (build-foo.sh for example) to build.sh, and another symlink
in gitbuilder.git/build.sh that points back to the build.sh in /srv/autobuild-ceph.  It then clones the build repo (i.e. foo) into
the build directory within gitbuilder.git/, and creates an upstart script in /etc/init/autobuild-ceph.  The upstart script
simply runs the ``run`` script in the /srv/autobuild-ceph directory, which in turn runs the gitbuilder autobuild.sh script.
The script checks that new commits exist in the repository before attempting another build, and exits otherwise.  The upstart
script is configured to respawn once the previous process exits, so the script continuously checks for new commits to the repository.

