from setuptools import setup, find_packages

setup(
	name="matej-libs",
	version="0.1",
	author="Matej Vitek",
	author_email="matej.vitek.business@gmail.com",
	url="https://github.com/MatejVitek/Python-Libraries",
	packages=find_packages(),
	python_requires='>=3.8',
	install_requires=['numpy'],
	extras_require={
		'google-drive': ['requests'],
		'config': ['ruamel.yaml'],
		'parallel': ['joblib']
	}
)
