"""
    The guts that actually do the work. This is available here for the
    'qtfaststart' script and for your application's direct use.
"""

import logging
import os
import struct

from StringIO import StringIO

from qtfaststart.exceptions import FastStartException

CHUNK_SIZE = 8192

log = logging.getLogger("qtfaststart")

# Older versions of Python require this to be defined
if not hasattr(os, 'SEEK_CUR'):
    os.SEEK_CUR = 1

def read_atom(datastream):
    """
        Read an atom and return a tuple of (size, type) where size is the size
        in bytes (including the 8 bytes already read) and type is a "fourcc"
        like "ftyp" or "moov".
    """
    return struct.unpack(">L4s", datastream.read(8))


def get_index(datastream):
    """
        Return an index of top level atoms, their absolute byte-position in the
        file and their size in a list:

        index = [
            ("ftyp", 0, 24),
            ("moov", 25, 2658),
            ("free", 2683, 8),
            ...
        ]

        The tuple elements will be in the order that they appear in the file.
    """
    index = []

    log.debug("Getting index of top level atoms...")

    # Read atoms until we catch an error
    while(datastream):
        try:
            skip = 8
            atom_size, atom_type = read_atom(datastream)
            if atom_size == 1:
                atom_size = struct.unpack(">Q", datastream.read(8))[0]
                skip = 16
            log.debug("%s: %s" % (atom_type, atom_size))
        except:
            break

        index.append((atom_type, datastream.tell() - skip, atom_size))

        if atom_size == 0:
            # Some files may end in mdat with no size set, which generally
            # means to seek to the end of the file. We can just stop indexing
            # as no more entries will be found!
            break

        datastream.seek(atom_size - skip, os.SEEK_CUR)

    # Make sure the atoms we need exist
    top_level_atoms = set([item[0] for item in index])
    for key in ["moov", "mdat"]:
        if key not in top_level_atoms:
            log.error("%s atom not found, is this a valid MOV/MP4 file?" % key)
            raise FastStartException()

    return index


def find_atoms(size, datastream):
    """
        This function is a generator that will yield either "stco" or "co64"
        when either atom is found. datastream can be assumed to be 8 bytes
        into the stco or co64 atom when the value is yielded.

        It is assumed that datastream will be at the end of the atom after
        the value has been yielded and processed.

        size is the number of bytes to the end of the atom in the datastream.
    """
    stop = datastream.tell() + size

    while datastream.tell() < stop:
        try:
            atom_size, atom_type = read_atom(datastream)
        except:
            log.exception("Error reading next atom!")
            raise FastStartException()

        if atom_type in ["trak", "mdia", "minf", "stbl"]:
            # Known ancestor atom of stco or co64, search within it!
            for atype in find_atoms(atom_size - 8, datastream):
                yield atype
        elif atom_type in ["stco", "co64"]:
            yield atom_type
        else:
            # Ignore this atom, seek to the end of it.
            datastream.seek(atom_size - 8, os.SEEK_CUR)


def process(infilename, outfilename, limit=0):
    """
        Convert a Quicktime/MP4 file for streaming by moving the metadata to
        the front of the file. This method writes a new file.

        If limit is set to something other than zero it will be used as the
        number of bytes to write of the atoms following the moov atom. This
        is very useful to create a small sample of a file with full headers,
        which can then be used in bug reports and such.
    """
    datastream = open(infilename, "rb")

    # Get the top level atom index
    index = get_index(datastream)

    mdat_pos = 999999
    free_size = 0

    # Make sure moov occurs AFTER mdat, otherwise no need to run!
    for atom, pos, size in index:
        # The atoms are guaranteed to exist from get_index above!
        if atom == "moov":
            moov_pos = pos
            moov_size = size
        elif atom == "mdat":
            mdat_pos = pos
        elif atom == "free" and pos < mdat_pos:
            # This free atom is before the mdat!
            free_size += size
            log.info("Removing free atom at %d (%d bytes)" % (pos, size))

    # Offset to shift positions
    offset = moov_size - free_size

    if moov_pos < mdat_pos:
        # moov appears to be in the proper place, don't shift by moov size
        offset -= moov_size
        if not free_size:
            # No free atoms and moov is correct, we are done!
            log.error("This file appears to already be setup for streaming!")
            raise FastStartException()

    # Read and fix moov
    datastream.seek(moov_pos)
    moov = StringIO(datastream.read(moov_size))

    # Ignore moov identifier and size, start reading children
    moov.seek(8)

    for atom_type in find_atoms(moov_size - 8, moov):
        # Read either 32-bit or 64-bit offsets
        ctype, csize = atom_type == "stco" and ("L", 4) or ("Q", 8)

        # Get number of entries
        version, entry_count = struct.unpack(">2L", moov.read(8))

        log.info("Patching %s with %d entries" % (atom_type, entry_count))

        # Read entries
        entries = struct.unpack(">" + ctype * entry_count,
                                moov.read(csize * entry_count))

        # Patch and write entries
        moov.seek(-csize * entry_count, os.SEEK_CUR)
        moov.write(struct.pack(">" + ctype * entry_count,
                               *[entry + offset for entry in entries]))

    log.info("Writing output...")
    outfile = open(outfilename, "wb")

    # Write ftype
    for atom, pos, size in index:
        if atom == "ftyp":
            datastream.seek(pos)
            outfile.write(datastream.read(size))

    # Write moov
    moov.seek(0)
    outfile.write(moov.read())

    # Write the rest
    written = 0
    atoms = [item for item in index if item[0] not in ["ftyp", "moov", "free"]]
    for atom, pos, size in atoms:
        datastream.seek(pos)

        # Write in chunks to not use too much memory
        for x in range(size / CHUNK_SIZE):
            outfile.write(datastream.read(CHUNK_SIZE))
            written += CHUNK_SIZE
            if limit and written >= limit:
                # A limit was set and we've just passed it, stop writing!
                break

        if size % CHUNK_SIZE:
            outfile.write(datastream.read(size % CHUNK_SIZE))
            written += (size % CHUNK_SIZE)
            if limit and written >= limit:
                # A limit was set and we've just passed it, stop writing!
                break
