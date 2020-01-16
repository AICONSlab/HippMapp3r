#!/bin/bash

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
echo "Adding external dependencies to ${SCRIPTPATH}"

# create depends dir
mkdir -p "${SCRIPTPATH}/depends/"

# find out if the user has ANTS
antspath=$( command -v antsRegistration )
if [[ -z "${antspath}" ]]; then
	echo "Environment variable ANTSPATH does not exist. Downloading and installing software to ${SCRIPTPATH}/depends/ANTs"
    export ANTSPATH="$ANTSPATH:${SCRIPTPATH}/depends/ANTs"
    export PATH="$PATH:$ANTSPATH"
    mkdir -p "${SCRIPTPATH}/depends/ANTs" && \
    curl -sSL "https://dl.dropbox.com/s/2f4sui1z6lcgyek/ANTs-Linux-centos5_x86_64-v2.2.0-0740f91.tar.gz" \
    | tar -xzC "${SCRIPTPATH}/depends/ANTs" --strip-components 1
fi


# find out if user has c3d installed
c3dpath=$( command -v c3d )
if [[ -z "${c3dpath}" ]]; then
	echo "Command c3d was not found. Downloading and installing software to ${SCRIPTPATH}/depends/c3d. Path will be added to PATH environment variable."
    mkdir -p "${SCRIPTPATH}/depends/c3d/"
    wget https://downloads.sourceforge.net/project/c3d/c3d/Nightly/c3d-nightly-Linux-x86_64.tar.gz && \
    tar -xzvf c3d-nightly-Linux-x86_64.tar.gz && mv c3d-1.1.0-Linux-x86_64/* "${SCRIPTPATH}/depends/c3d/" && \
    rm c3d-nightly-Linux-x86_64.tar.gz
    export PATH="${SCRIPTPATH}/depends/c3d/c3d-1.1.0-Linux-x86_64/bin/:$PATH"
fi
