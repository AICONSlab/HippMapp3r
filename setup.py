from setuptools import setup, find_packages
from hippmapper import __version__

setup(
    name='HippMapp3r',
    version=__version__,
    description='A CNN-based segmentation technique using MRI images from BrainLab',
    author=['Maged Goubran', 'Hassan Akhavein', 'Edward Ntiri'],
    author_email='maged.goubran@sri.utoronto.ca',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    license='GNU GENERAL PUBLIC LICENSE v3',
    url='https://github.com/mgoubran/HippMapp3r',  # change later
    download_url='https://github.com/mgoubran/HippMapp3r',
    long_description=open('README.md').read(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU  General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Unix Shell',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Image Recognition',
    ],
    dependency_links=[
        'git+https://github.com/keras-team/keras-contrib.git'
    ],
    install_requires=[
        'nibabel', 'nipype', 'argparse', 'argcomplete', 'joblib', 'keras', 'nilearn', 'scikit-learn',
        'keras-contrib', 'pandas', 'numpy', 'plotly', 'PyQt5'
    ],
    extras_require={
        "hippmapper": ["tensorflow>=1.4.0"],
        "hippmapper_gpu": ["tensorflow-gpu>=1.4.0"],
    },
    entry_points={'console_scripts': ['hippmapper=hippmapper.cli:main']},
    keywords=[
        'neuroscience dementia lesion stroke white-matter-hyperintensity brain-atlas mri neuroimaging',
        'medical-imaging biomedical image-processing image-registration image-segmentation',
    ],
)