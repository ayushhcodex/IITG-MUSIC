from setuptools import setup, find_packages

setup(
    name='sonicfold-nmr',
    version='1.0.0',
    description='Protein to Music Sonification Tool based on NMR Chemical Shifts',
    author='IITG Music',
    packages=find_packages(),
    install_requires=[
        'pandas==2.3.3',
        'numpy==2.4.4',
        'MIDIUtil==1.2.1',
        'scipy',
        'matplotlib',
    ],
    entry_points={
        'console_scripts': [
            'sonicfold-nmr=sonicfold_nmr.sonify:main',
            'sonicfold-plot=sonicfold_nmr.plotting:main',
        ],
    },
)
