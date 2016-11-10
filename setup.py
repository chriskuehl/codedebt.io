from setuptools import find_packages
from setuptools import setup


setup(
    name='codedebt-io',
    version='0.0.0',
    author='Chris Kuehl',
    author_email='ckuehl@ocf.berkeley.edu',
    # TODO: should have install_requires here
    packages=find_packages(exclude=('test*', 'playground*')),
    classifiers={
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    },
    entry_points={
        'console_scripts': [
            'codedebt-makedb = codedebt_io.db.manage:makedb',
            'codedebt-mysql = codedebt_io.db.manage:cli',
            'codedebt-worker = codedebt_io.worker:main',
            'codedebt-addproject = codedebt_io.project:add_cli',
        ],
    },
)
