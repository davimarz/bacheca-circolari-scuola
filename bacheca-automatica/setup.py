from setuptools import setup, find_packages

setup(
    name="bacheca-circolari",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'selenium>=4.15.0',
        'psycopg2-binary>=2.9.9',
        'chromedriver-autoinstaller>=0.6.0',
    ],
)
