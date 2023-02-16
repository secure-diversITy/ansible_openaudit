#!/bin/bash

name=$(grep name: galaxy.yml | cut -d ":" -f2 | tr -d " ")
namespace=$(grep namespace: galaxy.yml | cut -d ":" -f2 | tr -d " ")
version=$(grep version: galaxy.yml | cut -d ":" -f2 | tr -d " ")

[ -z "$gpgid" ] && echo "ERROR: you have to specify the env var 'gpgid=mailaddr|gpg id'" && exit 3

echo "$@" | grep -q force && rm -f ${namespace}-${name}-${version}.*

ansible-galaxy collection build "$@" \
    && echo "... build OK" \
    && tar -Oxzf "${namespace}-${name}-${version}.tar.gz" MANIFEST.json | gpg --output "${namespace}-${name}-${version}.asc" --detach-sign --armor --local-user "${gpgid}" - \
    && echo "... signing OK" \
    && tar -Oxzf "${namespace}-${name}-${version}.tar.gz" MANIFEST.json | gpg --verify "${namespace}-${name}-${version}.asc" - >> /dev/null 2>&1\
    && echo "... signature check OK" \
    && cd ../doc

[ -d ../../../secure-diversity.github.io/openaudit/static ] && rm -rf ../../../secure-diversity.github.io/openaudit/static
./build.sh >> /dev/null

if [ $? -eq 0 ];then
    for f in $(find build/html -type f -exec grep -q _static {} \; -print); do
        sed 's#_static#static#g' -i $f
    done \
    && cp -a build/html/. ../../../secure-diversity.github.io/openaudit/ && cd ../openaudit \
    && mv ../../../secure-diversity.github.io/openaudit/_static ../../../secure-diversity.github.io/openaudit/static \
    && echo "... documentation OK" \
    && echo "OK: all went well :)" && echo "Do not forget to push secure-diversity.github.io repo if changed.. " && exit
else
    echo "ERROR occured during build or signing.."
fi
