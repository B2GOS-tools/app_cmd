import os
from setuptools import setup, find_packages
import shutil

# get documentation from the README
try:
    here = os.path.dirname(os.path.abspath(__file__))
    description = file(os.path.join(here, 'README.md')).read()
except (OSError, IOError):
    description = ''

# version number
version = {}
execfile('version.py', version)

# dependencies
with open('requirements.txt') as f:
    deps = f.read().splitlines()

setup(name='autotest',
      version=version['__version__'],
      description="test automation for gaia",
      long_description=description,
      classifiers=[],
      keywords='kaios',
      author='Hermes Cheng',
      author_email='hermes.cheng@kaiostech.com',
      license='MPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      package_data={'gaiatest': [
          'atoms/*.js']},
      include_package_data=True,
      zip_safe=False,
      entry_points={'console_scripts': [
          'gaiatest = app_cmd:main']},
      install_requires=deps)

os.system("adb forward tcp:2828 tcp:2828")
