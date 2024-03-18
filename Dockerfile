# syntax=docker/dockerfile:1

# Ubuntu version codename (focal, jammy)
ARG UBUNTU_CODENAME=focal

# NeuroDebian image to copy configuration from
# http://neuro.debian.net/
FROM neurodebian:${UBUNTU_CODENAME}-non-free AS neurodebian

# Micromamba base image
# https://mamba.readthedocs.io/
# https://micromamba-docker.readthedocs.io/
FROM mambaorg/micromamba:${UBUNTU_CODENAME}

# >> BEGIN NeuroDebian setup
# Adapted from the official Dockerfile
# https://github.com/neurodebian/dockerfiles/blob/master/dockerfiles/jammy-non-free/Dockerfile

# Micromamba runs as `${MAMBA_USER}`; we need root privileges for the next bit
USER root

ARG DEBIAN_FRONTEND=noninteractive

# Install prerequisites for package authentication
# https://www.debian.org/doc/manuals/debian-handbook/sect.package-authentication.html
RUN set -x \
	&& apt-get update \
	&& apt-get install -y --no-install-recommends \
        gnupg2 \
        dirmngr \
	&& rm -rf /var/lib/apt/lists/*

# Copy APT repository key from the official image
# - Could also install from keyserver; this is less code to maintain,
#   will match the reference image in case it is updated
COPY --from=neurodebian /etc/apt/trusted.gpg.d/neurodebian.gpg /etc/apt/trusted.gpg.d/
COPY --from=neurodebian /etc/apt/sources.list.d/neurodebian.sources.list /etc/apt/sources.list.d/

# Freeze APT configuration; speed up Docker builds
RUN set -x \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        neurodebian-freeze \
        eatmydata \
    && ln -s /usr/bin/eatmydata /usr/local/bin/apt-get \
    && rm -rf /var/lib/apt/lists/*

# << END NeuroDebian setup

# >> BEGIN installing for HippMapper
# Install system packages
# - Installing HippMapp3r prereqs
# - Installing FSL from NeuroDebian is not recommended.
#   https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation/Faq
# - NeuroDebian does not appear to include a full FSL distribution for 
#   Ubuntu 22.04 (jammy). For Ubuntu 20.04 (focal), the most recent FSL
#   version available is 5.0.8 (2014-12-04).
#   https://neuro.debian.net/pkgs/fsl-core.html
#   https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/WhatsNew#anchor1
# - The current version of FSL is 6.0.x (2018-2023/present).
#   https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/WhatsNew
#   https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/WhatsNew#anchor2
RUN set -x \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        git wget build-essential g++ gcc cmake curl clang \
  	libfreetype6-dev apt-utils pkg-config vim gfortran \
  	binutils make linux-source unzip \
  	libsm6 libxext6 libfontconfig1 libxrender1 libgl1-mesa-glx \
        fsl-core \
        '^libxcb.*-dev' \
        libx11-xcb-dev \
        libglu1-mesa-dev \
        libxrender-dev \
        libxi-dev \
        libxkbcommon-dev \
        libxkbcommon-x11-dev \
        libxinerama-dev \
    && rm -rf /var/lib/apt/lists/*

 
    
# fsl already installed, just set params
ENV FSLDIR="/usr/share/fsl/5.0" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLMULTIFILEQUIT="TRUE"



# hippmapper here, have to do as root
RUN wget --no-check-certificate https://downloads.sourceforge.net/project/c3d/c3d/Nightly/c3d-nightly-Linux-x86_64.tar.gz && \
    tar -xzvf c3d-nightly-Linux-x86_64.tar.gz && mv c3d-1.1.0-Linux-x86_64 /opt/c3d && \
    rm c3d-nightly-Linux-x86_64.tar.gz
ENV PATH /opt/c3d/bin:${PATH}

    
ENV ANTSPATH /opt/ANTs
RUN mkdir -p /opt/ANTs && \
    curl -sSL "https://dl.dropbox.com/s/2f4sui1z6lcgyek/ANTs-Linux-centos5_x86_64-v2.2.0-0740f91.tar.gz" \
    | tar -xzC $ANTSPATH --strip-components 1
ENV PATH=${ANTSPATH}:${PATH}

#COPY . /src/hippmapp3r

#RUN python -m pip install /src/hippmapp3r

# >> BEGIN micromamba installations
# Install Conda packages into the default "base" environment
#USER ${MAMBA_USER}
# # Setup host user as container user\n\
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USER=$USER_ID:$GROUP_ID
#ARG USER=$(id -u):$(id -g)
# RUN addgroup --gid 1000 jacqueline
# RUN adduser --disabled-password --gecos '' --uid 1000 --gid 1000 jacqueline

# Change owner of /code directory\n\
# Change to \$USER\n\
#RUN mkdir -p /home/hippUser/.cache/pip
#RUN chmod 777 /home/hippUser/.cache/pip

#WORKDIR /home/hippUser
#WORKDIR /tmp
# Sample inline Conda environment definition; to use a file instead:
COPY requirements.txt ./
COPY data .
# in line env, minimal environment, will install all requirements.txt
COPY <<EOF environment.yml
name: hippmapper
channels:
  - conda-forge
dependencies:
  - python >=3.6,<3.7.0a0
  - pip
  - pip:
    - -rrequirements.txt
    #- -e /src/hippmapp3r # this is already included in the requirements
EOF

# installs all packages
RUN : \
  && micromamba install --yes --name "base" --file environment.yml \
  && micromamba clean --all --yes


# Download models, store in directory
RUN mkdir -p /tmp/src/hippmapp3r/models && \
    wget --no-check-certificate --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1RUE3Cw_rpKnKfwlu75kLbkcr9hde9nV4' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1RUE3Cw_rpKnKfwlu75kLbkcr9hde9nV4" -O /tmp/src/hippmapp3r/models/hipp_model.json && \
    rm -rf /tmp/cookies.txt && \
    wget --no-check-certificate --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1_VEOScLGyr1qV-t-zggq8Lxwgf_z-IpQ' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1_VEOScLGyr1qV-t-zggq8Lxwgf_z-IpQ" -O /tmp/src/hippmapp3r/models/hipp_model_weights.h5 && \
    rm -rf /tmp/cookies.txt && \
    wget --no-check-certificate --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1VN4XoFEH3PiykwXVxo-W1If7ksdIWakm' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1VN4XoFEH3PiykwXVxo-W1If7ksdIWakm" -O /tmp/src/hippmapp3r/models/hipp_zoom_full_mcdp_model.json && \
    rm -rf /tmp/cookies.txt && \
    wget --no-check-certificate --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=11im69_c78zQsx4EyShDmeSrGCzFJewJ6' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=11im69_c78zQsx4EyShDmeSrGCzFJewJ6" -O /tmp/src/hippmapp3r/models/hipp_zoom_full_mcdp_model_weights.h5 && \
    rm -rf /tmp/cookies.txt
# << END hippmapper specific stuff
#RUN ln -s /usr/bin/fsl5.0-fslmaths /usr/local/bin/fslmaths

# replace the version prefix of the fsl command so that they can be called as programmed in hippmapper
# fsl_app_wrapper contains all the commands fsl uses, it's what they link to originally, we link directly to it instead of linking to the link
# $1 refers to the element of the array/loop that we're going through
RUN find /usr/bin/ -name 'fsl5.0-*' -exec bash -c 'ln -s "/usr/lib/fsl/5.0/fsl_app_wrapper" "/usr/local/bin/${1/\/usr\/bin\/fsl5.0-/}"' _ {} \;

   
# Run a few quick smoke tests
ARG MAMBA_DOCKERFILE_ACTIVATE=1

RUN : \
  && which fsl5.0-fslstats \
  && python --version \
  && python -c "import hippmapper; print(hippmapper.__version__)"
  
#USER hippUser


