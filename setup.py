import os
import re
from setuptools import setup, find_packages
import sys

cwd = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(cwd, "README.md")) as f:
    long_description = f.read()

with open(os.path.join(cwd, "hummingbird/__init__.py")) as f:
    content = f.read()
    match = re.search(r'^__version__ = "(\d+\.\d+(a|b|rc\d+))"', content, re.M)
    if match is None:
        raise RuntimeError("Unable to find version string.")
    version = match.group(1)


if sys.version_info >= (3, 0):
    install_requires = [
        'h5py',
        'h5writer',
        'mpi4py',
        'numpy',
        'pexpect',
        'Pint',
        'PyQt5',                                                                                                                                                       
        'pyqtgraph',
        'pytz',                                                                                                                                                        
        'pyzmq',
        'scipy',
        'tornado',
   ]
else:
    install_requires = [
        "h5py<3",
        "h5writer",
        "mpi4py",
        "numpy<1.17",
        "pexpect",
        "Pint<=0.9",
        "PySide",
        "pyqtgraph",
        "pytz",
        "pyzmq<20",
        "scipy<1.3",
        "tornado<6",
        "msgpack<=1.0.2",
    ]
    

setup(
    name="Hummingbird-XFEL",
    version=version,
    author="Filipe R. N. C. Maia",
    author_email="filipe.c.maia@gmail.com",
    url="https://github.com/FXIhub/hummingbird",
    description="Monitoring and Analysing FXI experiments",
    long_description=long_description,
    long_description_content_type='text/markdown',
    license="BSD-2-Clause",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "hummingbird = hummingbird:main",
        ],
    },
    install_requires=install_requires,
    extras_require={
        "docs": [
            "sphinx",
            "sphinx_rtd_theme",
        ],
        "test": [
            "pytest",
            "subprocess32;python_version<'3.0'",
        ],
        "euxfel": [
            "karabo-bridge",
        ]
    },
    python_requires='>=2.7',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Scientific/Engineering :: Visualization',
    ],
)
