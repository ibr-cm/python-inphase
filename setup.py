from setuptools import setup, find_packages

setup(name='inphase',
      version='0.1',
      description='InPhase library functions and classes',
      url='https://gitlab.ibr.cs.tu-bs.de/inphase/inphase-software',
      author='Yannic Schröder',
      author_email='schroeder@ibr.cs.tu-bs.de',
      license='MIT',
      packages=find_packages(),
      install_requires=[
          'numpy',
          'pyserial',
          'PyYAML',
          'scipy'
      ],
      zip_safe=False,
      test_suite='nose.collector',
      tests_require=['nose'])
