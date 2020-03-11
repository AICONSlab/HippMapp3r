# Local Install

## Python
For the main required Python packages (numpy, scipy, etc.) we recommend using
[Anaconda for Python 3.6](https://www.continuum.io/downloads)


## ANTs & Convert3D (c3d)

If either ANTs or c3d are not installed on your machine, run `install_depends.sh`, located in the project directory. The required software will be installed in the `depends` directory

## Installing package and dependencies for HippMapp3r locally

1. Clone repository

        git clone https://github.com/mgoubran/HippMapp3r.git HippMapp3r

        (or install zip file and uncompress)

        cd HippMapp3r

    If you want to create a virtual environment where HippMapp3r can be run,

        conda create -n hippmapper python=3.6 anaconda
        source activate hippmapper
    
    To end the session, deactivate the environment
    
        source deactivate
    
    To delete the environment,
    
        conda env remove --name hippmapper

2. Install dependencies
    
        pip install git+https://www.github.com/keras-team/keras-contrib.git
    
    If the computer you are using has a GPU:
        
        pip install -e .[hippmapper_gpu]

    If not:
    
        pip install -e .[hippmapper]

3. Test the installation by running

        hippmapper --help
        
   To confirm that the command line function works, and
   
        hippmapper
        
   To launch the interactive GUI.

## Download deep models

Download the models from [this link](https://drive.google.com/open?id=10aVCDurd_mcB49mJfwm658IZg33u0pd2) and place them in the `models` directory

## For tab completion
    pip3 install argcomplete
    activate-global-python-argcomplete

## Updating HippMapp3r
To update HippMapp3r, navigate to the directory where HippMapp3r was cloned and run

    git pull
    pip install -e .[{option}] -process-dependency-links
    
where "option" is dependent on whether or not you have a GPU (see package installation steps above)
