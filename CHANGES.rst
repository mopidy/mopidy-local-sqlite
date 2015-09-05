v1.0.0 (2015-09-05)
-------------------

- Require Mopidy >= 1.1.

- The data directory provided by Mopidy v1.1 to each extension is now
  used to store the SQLite database containing the music metadata.
  If we can find the old data dir, all files are automatically moved to the new
  data dir.

- Add support for ordering artist browse results based on their
  ``sortname`` fields.  Set ``use_artist_sortname = true`` to enable
  this, but be aware this may give confusing results if not all
  artists in the library have proper sortnames.

- Return browse results in case-insensitive sort order.  Note that
  this will only work for ASCII characters due to SQLite's ``NOCASE``
  limitations.

- Remove file system ("Folders") browsing, since this is already
  handled by the ``file`` backend in Mopidy v1.1.

- Deprecate ``search_limit`` config value.


v0.10.3 (2015-08-18)
--------------------

- Update links to GitHub repository.


v0.10.2 (2015-06-27)
--------------------

- Fix data directory path.


v0.10.1 (2015-06-17)
--------------------

- Update ``local.translator`` imports for Mopidy v1.1.

- Update build/test environment.


v0.10.0 (2015-03-25)
--------------------

- Require Mopidy v1.0.

- Implement ``Library.get_distinct``.

- Lookup album and artist URIs.

- ``Track.last_modified`` changed to milliseconds.

- Return ``Ref.ARTIST`` for artists when browsing.


v0.9.3 (2015-03-06)
-------------------

- Fix URI handling when browsing albums via track artists.


v0.9.2 (2015-01-14)
-------------------

- Return file URIs when browsing directories.

- Add `search_limit` config value (default `-1`).


v0.9.1 (2014-12-15)
-------------------

- Skip invalid search URIs.

- Use file system encoding when browsing `Folders`.


v0.9.0 (2014-12-05)
-------------------

- Move image extraction to `Mopidy-Local-Images`.

- Add `max-age` URI parameter.


v0.8.1 (2014-12-01)
-------------------

- Fix track sort order when browsing non-album URIs.


v0.8.0 (2014-10-22)
-------------------

- Support file system browsing.

- Deprecate ``encodings`` configuration setting.

- Add database indexes for `date` and `track_no`.

- Refactor browsing implementation and image directory.


v0.7.3 (2014-10-15)
-------------------

- Improve browse performance.


v0.7.2 (2014-10-12)
-------------------

- Do not raise exceptions from ``http:app`` factory.

- Fix file URI for scanning images.


v0.7.1 (2014-10-09)
-------------------

- Fix handling of `uris` search parameter.


v0.7.0 (2014-10-08)
-------------------

- Support for external album art.

- Support for browsing by genre and date.

- Unified browsing: return albums for composers, genres, etc.

- Configurable root directories with refactored URI scheme.

- Deprecate ``foreign_keys``, ``hash`` and ``default_image_extension``
  confvals.

- Depend on Mopidy >= 0.19.4 for ``mopidy.local.ROOT_DIRECTORY_URI``.


v0.6.4 (2014-09-11)
-------------------

- Fix packaging issue.


v0.6.3 (2014-09-11)
-------------------

- Add index page for HTTP handler.


v0.6.2 (2014-09-09)
-------------------

- Catch all exceptions within ``SQLiteLibrary.add()``.

- Configurable encoding(s) for generated track names.


v0.6.1 (2014-09-06)
-------------------

- Handle empty queries in ``schema.search()``.


v0.6.0 (2014-09-02)
-------------------

- Add HTTP handler for accessing local images.


v0.5.0 (2014-08-26)
-------------------

- Create `albums`, `artists`, etc. views.

_ Support browsing by composer and performer.

- Perform ``ANALYZE`` after local scan.


v0.4.0 (2014-08-24)
-------------------

- Add `uris` parameter to schema.search_tracks().


v0.3.2 (2014-08-22)
-------------------

- Fixed exception handling when extracting images.


v0.3.1 (2014-08-22)
-------------------

- Delete unreferenced image files after local scan.


v0.3.0 (2014-08-21)
-------------------

- Extract images from local media files (experimental).


v0.2.0 (2014-08-20)
-------------------

- Support for indexed and full-text search.

- Support for local album images (Mopidy v0.20).

- Missing track names are generated from the track's URI.

- New configuration options for album/artist URI generation.


v0.1.1 (2014-08-14)
-------------------

- Browsing artists no longer returns composers and performers.

- Clean up artists/albums after import.


v0.1.0 (2014-08-13)
-------------------

- Initial release.
