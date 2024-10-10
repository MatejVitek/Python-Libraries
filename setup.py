# Uploading to PyPI:
# python setup.py sdist
# twine upload dist/*
# KeePass AutoType for API Token
from setuptools import setup, find_packages

# Version number just follows the major python version requirement, so 0.12 requires python 3.12
version = "0.12"

setup(
	name='matej-libs',
	version=version,
	author="Matej Vitek",
	author_email="matej.vitek.business@gmail.com",
	description="Collection of Python utility libraries.",
	long_description=open('README.md', encoding='utf-8').read(),
	url='https://github.com/MatejVitek/Python-Libraries',
	packages=find_packages(),
	python_requires='>=3.12',
	install_requires=['numpy'],
	extras_require={
		'google-drive': ['requests'],
		'config': ['ruamel.yaml'],
		'parallel': ['joblib']
	}
)
