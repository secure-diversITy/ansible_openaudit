#!/bin/bash

name=$(grep name: galaxy.yml | cut -d ":" -f2 | tr -d " ")
namespace=$(grep namespace: galaxy.yml | cut -d ":" -f2 | tr -d " ")
version=$(grep version: galaxy.yml | cut -d ":" -f2 | tr -d " ")

[ -z "$gpgid" ] && echo "ERROR: you have to specify the env var 'gpgid=mailaddr|gpg id'" && exit 3

ansible-galaxy collection build $@ \
    && echo "... build OK" \
    && tar -Oxzf ${namespace}-${name}-${version}.tar.gz MANIFEST.json | gpg --output ${namespace}-${name}-${version}.asc --detach-sign --armor --local-user ${gpgid} - \
    && echo "... signing OK" \
    && tar -Oxzf ${namespace}-${name}-${version}.tar.gz MANIFEST.json | gpg --verify ${namespace}-${name}-${version}.asc - >> /dev/null 2>&1\
    && echo "... signature check OK" \
    && echo "OK: all went well :)" && exit

echo "ERROR occured during build or signing.."
