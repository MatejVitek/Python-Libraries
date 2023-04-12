from setuptools import setup, find_packages

version = "0.1.1"

setup(
	name='matej-libs',
	version=version,
	author="Matej Vitek",
	author_email="matej.vitek.business@gmail.com",
	description="Collection of Python utility libraries.",
	long_description=open('README.md', encoding='utf-8').read(),
	url='https://github.com/MatejVitek/Python-Libraries',
	packages=find_packages(),
	python_requires='>=3.8',
	install_requires=['numpy'],
	extras_require={
		'google-drive': ['requests'],
		'config': ['ruamel.yaml'],
		'parallel': ['joblib']
	}
)
