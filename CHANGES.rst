0.10.1 2015-06-17
-----------------

- Update ``local.translator`` imports for Mopidy v1.1.

- Update build/test environment.


0.10.0 2015-03-25
-----------------

- Require Mopidy v1.0.

- Implement ``Library.get_distinct``.

- Lookup album and artist URIs.

- ``Track.last_modified`` changed to milliseconds.

- Return ``Ref.ARTIST`` for artists when browsing.


0.9.3 2015-03-06
----------------

- Fix URI handling when browsing albums via track artists.


0.9.2 2015-01-14
----------------

- Return file URIs when browsing directories.

- Add `search_limit` config value (default `-1`).


0.9.1 2014-12-15
----------------

- Skip invalid search URIs.

- Use file system encoding when browsing `Folders`.


0.9.0 2014-12-05
----------------

- Move image extraction to `Mopidy-Local-Images`.

- Add `max-age` URI parameter.


0.8.1 2014-12-01
----------------

- Fix track sort order when browsing non-album URIs.


0.8.0 2014-10-22
----------------

- Support file system browsing.

- Deprecate ``encodings`` configuration setting.

- Add database indexes for `date` and `track_no`.

- Refactor browsing implementation and image directory.


0.7.3 2014-10-15
----------------

- Improve browse performance.


0.7.2 2014-10-12
----------------

- Do not raise exceptions from ``http:app`` factory.

- Fix file URI for scanning images.


0.7.1 2014-10-09
----------------

- Fix handling of `uris` search parameter.


0.7.0 2014-10-08
----------------

- Support for external album art.

- Support for browsing by genre and date.

- Unified browsing: return albums for composers, genres, etc.

- Configurable root directories with refactored URI scheme.

- Deprecate ``foreign_keys``, ``hash`` and ``default_image_extension``
  confvals.

- Depend on Mopidy >= 0.19.4 for ``mopidy.local.ROOT_DIRECTORY_URI``.


0.6.4 2014-09-11
----------------

- Fix packaging issue.


0.6.3 2014-09-11
----------------

- Add index page for HTTP handler.


0.6.2 2014-09-09
----------------

- Catch all exceptions within ``SQLiteLibrary.add()``.

- Configurable encoding(s) for generated track names.


0.6.1 2014-09-06
----------------

- Handle empty queries in ``schema.search()``.


0.6.0 2014-09-02
----------------

- Add HTTP handler for accessing local images.


0.5.0 2014-08-26
----------------

- Create `albums`, `artists`, etc. views.

_ Support browsing by composer and performer.

- Perform ``ANALYZE`` after local scan.


0.4.0 2014-08-24
----------------

- Add `uris` parameter to schema.search_tracks().


0.3.2 2014-08-22
----------------

- Fixed exception handling when extracting images.


0.3.1 2014-08-22
----------------

- Delete unreferenced image files after local scan.


0.3.0 2014-08-21
----------------

- Extract images from local media files (experimental).


0.2.0 2014-08-20
----------------

- Support for indexed and full-text search.

- Support for local album images (Mopidy v0.20).

- Missing track names are generated from the track's URI.

- New configuration options for album/artist URI generation.


0.1.1 2014-08-14
----------------

- Browsing artists no longer returns composers and performers.

- Clean up artists/albums after import.


0.1.0 2014-08-13
----------------

- Initial release.
