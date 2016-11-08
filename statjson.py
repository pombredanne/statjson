#!/usr/bin/python
# TODO:
# - Add an option for not following symlinks
# - Add an option for just outputting the `stat` structure directly as a dict
# - Add an option for displaying timestamps in ISO8601 format
# - Add a "(file)type" field
# - Include unknown `stat` entries in output
# - Include device name?
# - Include user & group name (or `None`)
# - Use `stat` module to deconstruct flags
# - Calling `st_ctime` "change_time" is inaccurate on Windows.  Change this?
#  - Should I even bother with Windows support?
# - Include ACLs
# - Include extended attributes
# - Include SELinux properties?
# - Include capabilities?
# - Handle file names composed of undecodeable bytes
# - Support Python 3.5's `st_[amc]time_ns` fields
# - Use the `st_*` names for all fields?
# - Add an option for including a dict of broken-out boolean permission fields
#   (`IXOTH`, `IRUSR`, etc.)

from   collections import OrderedDict, defaultdict
import grp
import json
import os
import os.path
import pwd
import stat
import sys

extra_fields = [
    # Linux:
    ('st_blocks', 'blocks'),
    ('st_blksize', 'block_size'),
    ('st_rdev', 'rdev'),  # "type of device if an inode device"/"device ID (if special file)"
    ('st_flags', 'flags'),
    # FreeBSD:
    ('st_gen', 'generation'),  # file generation number
    ('st_birthtime', 'creation_time'),
    # RISCOS:
    ('st_ftype', 'ftype'),
    ('st_attrs', 'attributes'),
    ('st_obtype', 'object_type'),
    # Mac OS:
    ('st_rsize', 'real_size'),
    ('st_creator', 'creator'),
    ('st_type', 'st_type'),
    # Windows:
    ('st_file_attributes', 'file_attributes'),
]

file_types = defaultdict(lambda: ('?', 'unknown'), {
    stat.S_IFBLK: ('b', 'block_device'),
    stat.S_IFCHR: ('c', 'char_device'),
    stat.S_IFDIR: ('d', 'directory'),
    stat.S_IFIFO: ('p', 'FIFO'),
    stat.S_IFLNK: ('l', 'symlink'),
    stat.S_IFREG: ('-', 'regular_file'),
    stat.S_IFSOCK: ('s', 'socket'),
})

if sys.version_info[:2] >= (3,4):
    ### These constants are 0 when the platform doesn't support them; should
    ### something be done in that case?
    file_types[stat.S_IFDOOR] = ('D', 'door')
    file_types[stat.S_IFPORT] = ('P', 'event_port')
    file_types[stat.S_IFWHT] = ('w', 'whiteout')

def strmode(mode):  # cf. BSD's `strmode(3)`
    return file_types[stat.S_IFMT(mode)][0] \
            + ('r' if mode & stat.S_IRUSR else '-') \
            + ('w' if mode & stat.S_IWUSR else '-') \
            + ('Ss' if mode&stat.S_ISUID else '-x')[bool(mode&stat.S_IXUSR)] \
            + ('r' if mode & stat.S_IRGRP else '-') \
            + ('w' if mode & stat.S_IWGRP else '-') \
            + ('Ss' if mode&stat.S_ISGID else '-x')[bool(mode&stat.S_IXGRP)] \
            + ('r' if mode & stat.S_IROTH else '-') \
            + ('w' if mode & stat.S_IWOTH else '-') \
            + ('Tt' if mode&stat.S_ISVTX else '-x')[bool(mode&stat.S_IXOTH)] \
            + ' '
            ### TODO: Set the last character as follows:
            # extended attributes -> '@' (Mac OS X)
            # security context, no ACLs -> '.' (GNU ls)
            # ACLs -> '+'
            # none of the above: ' '

def main():
    stats = []
    ok = True
    for filename in sys.argv[1:]:
        about = OrderedDict()
        about["filename"] = filename
        try:
            st = os.stat(filename)
        except Exception as e:
            about["success"] = False
            about["error"] = OrderedDict([
                ("class", e.__class__.__name__),
                ("message", str(e)),
            ])
            ok = False
        else:
            about["success"] = True
            about["followed_symlink"] = os.path.islink(filename)
            about["filetype"] = file_types[stat.S_IFMT(st.st_mode)][1]
            about["mode"] = st.st_mode
            about["mode_octal"] = '0{0:0o}'.format(st.st_mode)
            about["mode_str"] = strmode(st.st_mode)
            about["inode"] = st.st_ino
            about["device"] = st.st_dev
            about["links"] = st.st_nlink

            about["owner"] = OrderedDict()
            about["owner"]["uid"] = st.st_uid
            try:
                about["owner"]["name"] = pwd.getpwuid(st.st_uid).pw_name
            except KeyError:
                about["owner"]["name"] = None

            about["group"] = OrderedDict()
            about["group"]["gid"] = st.st_gid
            try:
                about["group"]["name"] = grp.getgrgid(st.st_gid).gr_name
            except KeyError:
                about["group"]["name"] = None

            about["size"] = st.st_size
            about["access_time"] = st.st_atime
            about["modify_time"] = st.st_mtime
            about["change_time"] = st.st_ctime
            for attr, name in extra_fields:
                try:
                    about[name] = getattr(st, attr)
                except AttributeError:
                    pass
        stats.append(about)
    print(json.dumps(stats, indent=4, separators=(',', ': ')))
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()