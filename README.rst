Mopidy-Local-SQLite
========================================================================

Mopidy-Local-SQLite is a Mopidy_ local library extension that uses an
SQLite_ database for keeping track of your local media.  This
extension lets you browse your music collection by album, artist,
composer and performer, and provides full-text search capabilities
based on SQLite's FTS_ modules.  It also notices updates via ``mopidy
local scan`` while Mopidy is running, so you can scan your media
library periodically from a cron job, for example.

This extension also features experimental support for extracting and
using album art embedded in local media files.  At this point,
however, this will be mostly of interest to developers, so it is
disabled by default.


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

This extension also provides some configuration settings of its own,
but beware that these are still subject to change::

    [local-sqlite]
    enabled = true

    # hash algorithm used for generating local URIs and image file names
    hash = md5

    # whether to use an album's musicbrainz_id for generating its URI
    use_album_mbid_uri = true

    # whether to use an artist's musicbrainz_id for generating its URI;
    # disabled by default, since some taggers do not handle this well for
    # multi-artist tracks [https://github.com/sampsyo/beets/issues/907]
    use_artist_mbid_uri = false

    # set to "off" to disable enforcement of foreign key constraints
    foreign_keys = on

    # database connection timeout in seconds
    timeout = 10

    # whether to extract images from local media files (experimental)
    extract_images = false

    # directory where extracted images are stored; if relative, names a
    # subdirectory of local/data_dir
    image_dir = images

    # base URI for images; if blank, the local file URI will be used; if
    # using the Mopidy-HTTP-Images extension for serving local images to
    # Web clients, this should be set to "/images/"
    image_base_uri =

    # default extension for image files if the image type cannot be
    # determined; leave blank to skip such images
    default_image_extension =


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

The database schema does not support multiple artists, composers or
performers for a single track or album (yet).  Look out for "Ignoring
multiple artists" warnings during a local scan to see if you are
affected by this.


.. _Mopidy: http://www.mopidy.com/
.. _SQLite: http://www.sqlite.org/
.. _FTS: http://www.sqlite.org/fts3.html

.. _Issue Tracker: https://github.com/tkem/mopidy-local-sqlite/issues/
.. _Source Code: https://github.com/tkem/mopidy-local-sqlite
.. _Change Log: https://raw.github.com/tkem/mopidy-local-sqlite/master/Changes

.. _Apache License, Version 2.0: http://www.apache.org/licenses/LICENSE-2.0
