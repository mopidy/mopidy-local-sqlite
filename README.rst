Mopidy-Local-SQLite
========================================================================

Mopidy-Local-SQLite is a Mopidy_ local library extension that uses an
SQLite_ database for keeping track of your local media.  This
extension lets you browse your music collection by album, artist,
composer and performer, and provides full-text search capabilities
based on SQLite's FTS_ modules.  It also notices updates via ``mopidy
local scan`` while Mopidy is running, so you can scan your media
library periodically from a cron job, for example.


Installation
------------------------------------------------------------------------

Mopidy-Local-SQLite can be installed using pip_ by running::

    pip install Mopidy-Local-SQLite


Configuration
------------------------------------------------------------------------

Before starting Mopidy, you must change your configuration to switch
to using Mopidy-Local-SQLite as your preferred local library.  It is
also recommended to change the default ``scan_flush_threshold``, to
improve database access during a local scan::

    [local]
    library = sqlite
    scan_flush_threshold = 100

Once this has been set you need to re-scan your library to populate
the database::

    mopidy local scan

This extension also provides some configuration settings of its own,
but be aware that these are still subject to change::

  [local-sqlite]
  enabled = true

  # top-level directories for browsing, as <name> <uri>
  directories =
      Albums                  local:directory?type=album
      Artists                 local:directory?type=artist
      Composers               local:directory?type=artist&role=composer
      Folders                 local:directory:
      Genres                  local:directory?type=genre
      Performers              local:directory?type=artist&role=performer
      Release Years           local:directory?type=date&format=%25Y
      Tracks                  local:directory?type=track
      Last Week's Updates     local:directory?max-age=604800
      Last Month's Updates    local:directory?max-age=2592000

  # database connection timeout in seconds
  timeout = 10

  # whether to use an album's musicbrainz_id for generating its URI
  use_album_mbid_uri = true

  # whether to use an artist's musicbrainz_id for generating its URI;
  # disabled by default, since some taggers do not handle this well for
  # multi-artist tracks [https://github.com/sampsyo/beets/issues/907]
  use_artist_mbid_uri = false

  # override search limit provided by Mopidy core; set to -1 (no limit)
  # to emulate current behavior of json library
  # [https://github.com/mopidy/mopidy/issues/917]
  search_limit = -1


Project Resources
------------------------------------------------------------------------

.. image:: http://img.shields.io/pypi/v/Mopidy-Local-SQLite.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Local-SQLite/
    :alt: Latest PyPI version

.. image:: http://img.shields.io/pypi/dm/Mopidy-Local-SQLite.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Local-SQLite/
    :alt: Number of PyPI downloads

.. image:: http://img.shields.io/travis/tkem/mopidy-local-sqlite/master.svg?style=flat
    :target: https://travis-ci.org/tkem/mopidy-local-sqlite/
    :alt: Travis CI build status

.. image:: http://img.shields.io/coveralls/tkem/mopidy-local-sqlite/master.svg?style=flat
   :target: https://coveralls.io/r/tkem/mopidy-local-sqlite/
   :alt: Test coverage

- `Issue Tracker`_
- `Source Code`_
- `Change Log`_


License
------------------------------------------------------------------------

Copyright (c) 2014, 2015 Thomas Kemmer.

Licensed under the `Apache License, Version 2.0`_.


Known Bugs and Limitations
------------------------------------------------------------------------

The database schema does not support multiple artists, composers or
performers for a single track or album.  Look out for "Ignoring
multiple artists" warnings during a local scan to see if you are
affected by this.


.. _Mopidy: http://www.mopidy.com/
.. _SQLite: http://www.sqlite.org/
.. _FTS: http://www.sqlite.org/fts3.html

.. _pip: https://pip.pypa.io/en/latest/

.. _Issue Tracker: https://github.com/tkem/mopidy-local-sqlite/issues/
.. _Source Code: https://github.com/tkem/mopidy-local-sqlite/
.. _Change Log: https://github.com/tkem/mopidy-local-sqlite/blob/master/CHANGES.rst

.. _Apache License, Version 2.0: http://www.apache.org/licenses/LICENSE-2.0
