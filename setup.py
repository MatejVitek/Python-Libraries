from setuptools import setup, find_packages

setup(
	name="matej-libs",
	version="1.0",
	author="Matej Vitek",
	author_email="matej.vitek.business@gmail.com",
	url="https://github.com/MatejVitek/Python-Libraries",
	packages=find_packages(),
	python_requires='>=3.5',
	install_requires=['joblib', 'tqdm', 'numpy']
)
