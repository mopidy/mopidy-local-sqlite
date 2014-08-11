CREATE TABLE artist (
    uri             TEXT PRIMARY KEY,           -- artist URI
    name            TEXT NOT NULL,              -- artist name
    musicbrainz_id  TEXT                        -- MusicBrainz ID
);

CREATE TABLE album (
    uri             TEXT PRIMARY KEY,           -- album URI
    name            TEXT NOT NULL,              -- album name
    artists         TEXT,                       -- (list of Artist) album artists
    num_tracks      INTEGER,                    -- number of tracks in album
    num_discs       INTEGER,                    -- number of discs in album
    date            TEXT,                       -- album release date (YYYY or YYYY-MM-DD)
    musicbrainz_id  TEXT,                       -- MusicBrainz ID
    images          TEXT,                       -- (list of strings) album image URIs
    FOREIGN KEY (artists) REFERENCES artist(uri)
);

CREATE TABLE track (
    uri             TEXT PRIMARY KEY,           -- track URI
    name            TEXT NOT NULL,              -- track name
    album           TEXT,                       -- track album
    artists         TEXT,                       -- (list of Artist) – track artists
    composers       TEXT,                       -- (list of Artist) – track composers
    performers      TEXT,                       -- (list of Artist) – track performers
    genre           TEXT,                       -- track genre
    track_no        INTEGER,                    -- track number in album
    disc_no         INTEGER,                    -- disc number in album
    date            TEXT,                       -- track release date (YYYY or YYYY-MM-DD)
    length          INTEGER,                    -- track length in milliseconds
    bitrate         INTEGER,                    -- bitrate in kbit/s
    comment         TEXT,                       -- track comment
    musicbrainz_id  TEXT,                       -- MusicBrainz ID
    last_modified   INTEGER,                    -- Represents last modification time
    FOREIGN KEY (album) REFERENCES album(uri),
    FOREIGN KEY (artists) REFERENCES artist(uri),
    FOREIGN KEY (composers) REFERENCES artist(uri),
    FOREIGN KEY (performers) REFERENCES artist(uri)
);

PRAGMA user_version = 1;                        -- schema version for upgrade
