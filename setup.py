from setuptools import setup, find_packages

version = "0.1"

setup(
	name='matej-libs',
	version=version,
	author="Matej Vitek",
	author_email="matej.vitek.business@gmail.com",
	url='https://github.com/MatejVitek/Python-Libraries',
	download_url=f'https://github.com/MatejVitek/Python-Libraries/archive/refs/tags/v{version}.tar.gz',
	packages=find_packages(),
	python_requires='>=3.8',
	install_requires=['numpy'],
	extras_require={
		'google-drive': ['requests'],
		'config': ['ruamel.yaml'],
		'parallel': ['joblib']
	}
)
