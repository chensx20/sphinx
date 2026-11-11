import os
import sys
import zlib

sys.path.insert(0, os.path.abspath('.'))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
nitpicky = True

inventory = (b'# Sphinx inventory version 2\n'
             b'# Project: remote\n'
             b'# Version: 1.0\n'
             b'# The remainder of this file is compressed with zlib.\n' +
             zlib.compress(b'remote.value py:data 1 remote.html#remote.value -\n'))
with open('remote.inv', 'wb') as stream:
    stream.write(inventory)
intersphinx_mapping = {'remote': ('https://example.invalid/api', 'remote.inv')}
