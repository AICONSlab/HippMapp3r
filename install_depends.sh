#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
echo $SCRIPTPATH

# create depends dir
mkdir -p "${SCRIPTPATH}/depends/"

# find out if the user has ANTS
antspath=$( command -v antsRegistration )

if [[ -z "${antspath}" ]]; then
    export ANTSPATH="$ANTSPATH:${SCRIPTPATH}/depends/ANTs"
    mkdir -p "${SCRIPTPATH}/depends/ANTs" && \
    curl -sSL "https://dl.dropbox.com/s/2f4sui1z6lcgyek/ANTs-Linux-centos5_x86_64-v2.2.0-0740f91.tar.gz" \
    | tar -xzC "${SCRIPTPATH}/depends/ANTs" --strip-components 1
fi


# find out if user has c3d installed
c3dpath=$( command -v c3d )
if [[ -z "${c3dpath}" ]]; then
    mkdir -p "${SCRIPTPATH}/depends/c3d/"
    wget https://downloads.sourceforge.net/project/c3d/c3d/Nightly/c3d-nightly-Linux-x86_64.tar.gz && \
    tar -xzvf c3d-nightly-Linux-x86_64.tar.gz && mv c3d-1.1.0-Linux-x86_64 "${SCRIPTPATH}/depends/c3d/" && \
    rm c3d-nightly-Linux-x86_64.tar.gz
    export PATH="${SCRIPTPATH}/depends/c3d/bin/:$PATH"
fi
