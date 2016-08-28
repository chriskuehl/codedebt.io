from setuptools import find_packages
from setuptools import setup


setup(
    name='codedebt-io',
    version='0.0.0',
    author='Chris Kuehl',
    author_email='ckuehl@ocf.berkeley.edu',
    packages=find_packages(exclude='test*'),
    include_package_data=True,
    install_requires={
        'pymysql',
    },
    classifiers={
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    },
)
