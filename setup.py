from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pnemu',
    version='1.0',
    description='An extensible python library to emulate P/T nets using High-Level Petri nets',
    long_description=long_description,
    url='https://pnemu.github.io',
    author='Matteo Camilli',
    author_email='matteo.camilli@unimi.it',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='PetriNets reflection simulation evolution edaptation',
    packages=find_packages(exclude=['contrib', 'docs', 'examples', 'tests']),
    install_requires=[
        'SNAKES',
        'graphviz',
    ],
    extras_require={
        'test': ['pytest']
    },
    project_urls={
        'Bug Reports': 'https://github.com/SELab-unimi/pyrpn/issues',
        'Source': 'https://github.com/SELab-unimi/pyrpn',
    },
)
