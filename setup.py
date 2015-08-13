from distutils.core import setup

setup(name='pyshake',
      version='0.1dev',
      description='Python GMPE library',
      author='Bruce Worden, Mike Hearne',
      author_email='cbworden@usgs.gov,mhearne@usgs.gov',
      url='',
      packages=['pyshake','pyshake.gmpe','pyshake.shakelib','pyshake.oldshakelib'],
      scripts = [],
)