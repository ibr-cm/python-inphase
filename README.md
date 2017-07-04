# InPhase Python Module
This python module contains all helper functions and classes that are helpful to run experiments with the InPhase system.


## Installation
This copies the module to `/usr/...` so you can use it system-wide in Python 3 via `import inphase`:

* Clone this repository
* Change directory into the cloned repository
* `sudo python3 setup.py install`

## Installation for development
If you want to develop this module you can instruct the setup not to copy the module to `/usr/...` but just link it there. Any changes inside this repository are then available system-wide instantly:

* `sudo python3 setup.py develop` (instead of `install`)

## Check test coverage
1. Run `nosetests --with-coverage` to run unit tests and generate a coverage report
2. Run `coverage -report -m inphase/*` to display test coverage of the inphase module