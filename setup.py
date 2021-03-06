from setuptools import setup
import sys
import os

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

setup(
    name='appurl',
    version='0.2.4',
    url='https://github.com/Metatab/appurl',
    license='MIT',
    author='Eric Busboom',
    author_email='eric@busboom.org',
    description='Url manipulation for extended application urls',
    packages=['appurl','appurl.archive','appurl.file','appurl.web', 'appurl.test','appurl.test.test_data'],
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.csv'],
    },
    zip_safe=True,
    #test_suite='appurl.test.test_suite',
    test_suite='nose.collector',
    tests_require=['nose','rowgenerators','tabulate'],
    install_requires=[
        'fs >= 2',
        'boto',
        'requests',
        'filelock',
        'tabulate'
        ],
    entry_points = {
        'appurl.urls' : [
            "* = appurl.url:Url",

            # Web Urls
            "http: = appurl.web.web:WebUrl",
            "https: = appurl.web.web:WebUrl",
            "s3: = appurl.web.s3:S3Url",
            "socrata+ = appurl.web.socrata:SocrataUrl",
            #
            # Archive Urls
            ".zip = appurl.archive.zip:ZipUrl",
            #
            # File Urls
            ".csv = appurl.file.csv:CsvFileUrl",
            ".xlsx = appurl.file.excel:ExcelFileUrl",
            ".xls = appurl.file.excel:ExcelFileUrl",
            "file: = appurl.file.file:FileUrl",
            "program+ = appurl.file.program:ProgramUrl",
            "python: = appurl.file.python:PythonUrl",
        ],
        'console_scripts': [
            'appurl=appurl.cli:appurl'
        ]
    }
)