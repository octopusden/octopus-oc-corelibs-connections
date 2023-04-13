from setuptools import setup

__version="0.0.1"

spec = {
    "name": "oc_connections",
    "version": __version,
    "license": "Apache License 2.0",
    "description": "Connection Manages",
    "packages": ["oc_connections"],
    "install_requires": [
      'oc_cdtapi', 
      'oc_pyfs',
      'pysmb'
    ],
    "package_data": {},
    "python_requires": ">=3.6",
}

setup(**spec)
