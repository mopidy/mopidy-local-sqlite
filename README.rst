Mopidy-Local-SQLite
========================================================================

Mopidy-Local-SQLite is a Mopidy_ local library extension that uses an
SQLite_ database for keeping track of your local media.  This
extension lets you browse your music collection by album, artist,
composer and performer, and provides full-text search capabilities
based on SQLite's FTS_ modules.  It also notices updates via ``mopidy
local scan`` while Mopidy is running, so you can scan your media
library periodically from a cron job, for example.

This extension also features *experimental* support for using album
art embedded in local media files.  If ``extract_images`` is set to
``true``, images will be extracted from media files and stored
seperately in Mopidy's ``local/data_dir``.  Corresponding image URIs
will be provided for albums, so Web clients can access these images
through Mopidy's integrated Web server.  Note, however, that `some
clients`_ will still ignore album images provided by
Mopidy-Local-SQLite.


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
but beware that these are still subject to change::

    [local-sqlite]
    enabled = true

    # top-level directories for browsing, format is <name> <uri>
    directories =
        Albums      local:directory?type=album
        Artists     local:directory?type=artist&role=artist
        Composers   local:directory?type=artist&role=composer
        Performers  local:directory?type=artist&role=performer
        Genres      local:directory?type=genre
        Years       local:directory?type=date&format=%25Y
        Tracks      local:directory?type=track

    # encodings (in order of preference) to try when generating track
    # names from file URIs
    encodings = utf-8, latin-1

    # database connection timeout in seconds
    timeout = 10

    # whether to use an album's musicbrainz_id for generating its URI
    use_album_mbid_uri = true

    # whether to use an artist's musicbrainz_id for generating its URI;
    # disabled by default, since some taggers do not handle this well for
    # multi-artist tracks [https://github.com/sampsyo/beets/issues/907]
    use_artist_mbid_uri = false

    # whether to extract images from local media files (experimental)
    extract_images = false

    # directory where extracted images are stored; if a relative path is
    # given, names a subdirectory of <local/data_dir>/sqlite
    image_dir = images

    # base URI for images; if blank, the local file URI will be used
    image_base_uri = /sqlite/images/

    # file names to check for in the current directory when no embedded
    # album art can be found; items may contain UNIX shell patterns
    album_art_files = *.jpg, *.jpeg, *.png


Project Resources
------------------------------------------------------------------------

.. image:: http://img.shields.io/pypi/v/Mopidy-Local-SQLite.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Local-SQLite/
    :alt: Latest PyPI version

.. image:: http://img.shields.io/pypi/dm/Mopidy-Local-SQLite.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Local-SQLite/
    :alt: Number of PyPI downloads

.. image:: http://img.shields.io/travis/tkem/mopidy-local-sqlite.svg?style=flat
    :target: https://travis-ci.org/tkem/mopidy-local-sqlite/
    :alt: Travis CI build status

- `Issue Tracker`_
- `Source Code`_
- `Change Log`_


License
------------------------------------------------------------------------

Copyright (c) 2014 Thomas Kemmer.

Licensed under the `Apache License, Version 2.0`_.


Known Bugs and Limitations
------------------------------------------------------------------------

The database schema does not support multiple artists, composers or
performers for a single track or album (yet).  Look out for "Ignoring
multiple artists" warnings during a local scan to see if you are
affected by this.


.. _Mopidy: http://www.mopidy.com/
.. _SQLite: http://www.sqlite.org/
.. _FTS: http://www.sqlite.org/fts3.html
.. _some clients: https://github.com/martijnboland/moped/issues/17

.. _pip: https://pip.pypa.io/en/latest/

.. _Issue Tracker: https://github.com/tkem/mopidy-local-sqlite/issues/
.. _Source Code: https://github.com/tkem/mopidy-local-sqlite/
.. _Change Log: https://raw.github.com/tkem/mopidy-local-sqlite/master/Changes

.. _Apache License, Version 2.0: http://www.apache.org/licenses/LICENSE-2.0
