
#!/bin/sh -x

# Change URL's of submodules.

build=$(pwd)
if [ -e ".gitmodule_mirrors" ]
then
    # Chicken and the egg... Git submodule commands won't work if
    # they are not initialized.
    # Because of this we must use dirty hack to change submodule URLs
    for submodule in $(git config -l | grep submodule | cut -d'.' -f2)
    do
        if [ $(grep -ic ${submodule} ${build}/.gitmodule_mirrors) -gt 0 ]
        then
            giturl=$(grep ${submodule} ${build}/.gitmodule_mirrors | cut -d" " -f2)
            /srv/git/bin/git config --replace-all submodule.${submodule}.url ${giturl}
        fi
    done
fi

