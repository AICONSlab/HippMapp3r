# Local Install

## Python
For the main required Python packages (numpy, scipy, etc.) we recommend using
[Anaconda for Python 3.6](https://www.continuum.io/downloads)

## Installing package and dependencies for HippMapp3r locally

1. Clone repository

        git clone https://github.com/mgoubran/HippMapp3r.git dasher

        (or install zip file and uncompress)

        cd dasher

    If you want to create a virtual environment where HippMapp3r can be run,

        conda create -n dasher python=3.6 anaconda
        source activate dasher
    
    To end the session,
    
        source deactivate
    
    To remove the environment
    
        conda env remove --name dasher

2. Install dependencies

        pip install -e .[{option}] -process-dependency-links

    If the computer you are using has a GPU, replace "option" with "hippmapper_gpu". Otherwise, replace it with "hippmapper"

3. Test the installation by running

        hippmapper --help
        
   To confirm that the command line function works, and
   
        hippmapper
        
   To launch the interactive GUI.

## Download deep models

Download the models from [this link](https://drive.google.com/open?id=10aVCDurd_mcB49mJfwm658IZg33u0pd2) and place them in the "models" directory

## For tab completion
    pip3 install argcomplete
    activate-global-python-argcomplete

## Updating HippMapp3r
To update HippMapp3r, navigate to the directory where HippMapp3r was cloned and run

    git pull
    pip install -e .[{option}] -process-dependency-links
    
where "option" is dependent on whether or not you have a GPU (see package installation steps above)
