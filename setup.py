from setuptools import setup

__version="1.0.1"

spec = {
    "name": "oc-connections",
    "version": __version,
    "license": "Apache License 2.0",
    "description": "Connection Manages",
    "long_description": "",
    "long_description_content_type": "text/plain",
    "packages": ["oc_connections"],
    "install_requires": [
      'oc-cdtapi', 
      'oc-pyfs',
      'pysmb'
    ],
    "package_data": {},
    "python_requires": ">=3.6",
}

setup(**spec)
