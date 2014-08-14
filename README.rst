Mopidy-Local-SQLite
========================================================================

Mopidy-Local-SQLite is a Mopidy_ local library extension that uses an
SQLite_ database for keeping track of your local media.  This
extension lets you browse your music collection by artist and album,
and notices updates via ``mopidy local scan`` without a server
restart.


Installation
------------------------------------------------------------------------

Install by running::

    pip install Mopidy-Local-SQLite


Configuration
------------------------------------------------------------------------

Before starting Mopidy, you must change your configuration to switch
to using Mopidy-Local-SQLite as your preferred local library::

    [local]
    library = sqlite


Once this has been set you need to re-scan your library to populate
the database::

    mopidy local scan


Project Resources
------------------------------------------------------------------------

.. image:: http://img.shields.io/pypi/v/Mopidy-Local-SQLite.svg
    :target: https://pypi.python.org/pypi/Mopidy-Local-SQLite/
    :alt: Latest PyPI version

.. image:: http://img.shields.io/pypi/dm/Mopidy-Local-SQLite.svg
    :target: https://pypi.python.org/pypi/Mopidy-Local-SQLite/
    :alt: Number of PyPI downloads

- `Issue Tracker`_
- `Source Code`_
- `Change Log`_


License
------------------------------------------------------------------------

Copyright (c) 2014 Thomas Kemmer.

Licensed under the `Apache License, Version 2.0`_.


Known Bugs and Limitations
------------------------------------------------------------------------

This extension does not support searching (yet).

The database schema does not support multiple artists, composers or
performers for a single track or album.  Look out for "Ignoring
multiple artists" warnings during a local scan to see if you are
affected by this.


.. _Mopidy: http://www.mopidy.com/
.. _SQLite: http://www.sqlite.org/

.. _Issue Tracker: https://github.com/tkem/mopidy-local-sqlite/issues/
.. _Source Code: https://github.com/tkem/mopidy-local-sqlite
.. _Change Log: https://raw.github.com/tkem/mopidy-local-sqlite/master/Changes

.. _Apache License, Version 2.0: http://www.apache.org/licenses/LICENSE-2.0
