import argparse
import os
import struct
import subprocess
import urllib.error
from collections import namedtuple
from io import BytesIO, SEEK_CUR, SEEK_SET
from struct import calcsize, unpack
from urllib.parse import urljoin
from urllib.request import urlopen
from zlib import decompress

HpkgRepoHeader = namedtuple('HpkgRepoHeader', [
    'magic', 'header_size', 'version', 'total_size', 'minor_version',
    'heap_compression', 'heap_chunk_size', 'heap_size_compressed', 'heap_size_uncompressed',
    'info_length', 'reserved1',
    'packages_length', 'packages_strings_length', 'packages_strings_count'
])

REPO_HEADER_FORMAT = '>4sHHQHHIQQIIQQQ'


#
# Repo file parsing
#
class ParseError(Exception):
    pass


class NullTag(Exception):
    pass


def read_unsigned_LEB128(f):
    result = 0
    shift = 0
    while True:
        b = int.from_bytes(f.read(1), "big")
        result |= (b & 0x7f) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return result


def attribute_tag_type(tag: int) -> int:
    return ((tag - 1) >> 7) & 0x7


def attribute_tag_id(tag: int) -> int:
    return (tag - 1) & 0x7f


def attribute_tag_encoding(tag: int) -> int:
    return ((tag - 1) >> 11) & 0x3


def attribute_tag_has_children(tag: int) -> bool:
    return (((tag - 1) >> 10) & 0x1) != 0


B_HPKG_ATTRIBUTE_TYPE_INVALID = 0
B_HPKG_ATTRIBUTE_TYPE_INT = 1
B_HPKG_ATTRIBUTE_TYPE_UINT = 2
B_HPKG_ATTRIBUTE_TYPE_STRING = 3
B_HPKG_ATTRIBUTE_TYPE_RAW = 4

B_HPKG_ATTRIBUTE_ENCODING_INT_8_BIT = 0
B_HPKG_ATTRIBUTE_ENCODING_INT_16_BIT = 1
B_HPKG_ATTRIBUTE_ENCODING_INT_32_BIT = 2
B_HPKG_ATTRIBUTE_ENCODING_INT_64_BIT = 3

B_HPKG_ATTRIBUTE_ENCODING_STRING_INLINE = 0
B_HPKG_ATTRIBUTE_ENCODING_STRING_TABLE = 1

B_HPKG_ATTRIBUTE_ENCODING_RAW_INLINE = 0
B_HPKG_ATTRIBUTE_ENCODING_RAW_HEAP = 1

B_PACKAGE_ARCHITECTURE_ENUM = [
	"any",
	"x86",
	"x86_gcc2",
	"source",
	"x86_64",
	"ppc",
	"arm",
	"m68k",
	"sparc",
	"arm64",
	"riscv64"
]


class Attribute:
    def __init__(self, id_, value):
        self.id = id_
        self.value = value
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def __repr__(self):
        return "id: %i value: %s" % (self.id, str(self.value))


class PackageVersion:
    def __init__(self, major: bytes):
        if not isinstance(major, bytes) or len(major) == 0:
            raise ValueError()
        self._major = major
        self._minor = None
        self._micro = None
        self._pre_release = None
        self._revision = None

    @property
    def minor(self) -> bytes:
        return self._minor

    @minor.setter
    def minor(self, value: bytes):
        if not isinstance(value, bytes) or len(value) == 0:
            raise ValueError()
        self._minor = value

    @property
    def micro(self) -> bytes:
        return self._micro

    @micro.setter
    def micro(self, value: bytes):
        if not isinstance(value, bytes) or len(value) == 0:
            raise ValueError()
        self._micro = value

    @property
    def pre_release(self) -> bytes:
        return self._pre_release

    @pre_release.setter
    def pre_release(self, value: bytes):
        if not isinstance(value, bytes) or len(value) == 0:
            raise ValueError()
        self._pre_release = value

    @property
    def revision(self) -> int:
        return self._revision

    @revision.setter
    def revision(self, value: int):
        if not isinstance(value, int) or value < 0:
            raise ValueError()
        self._revision = value

    def __str__(self):
        output = self._major.decode("utf-8")
        if self._minor:
            output += "."
            output += self._minor.decode("utf-8")
            if self._micro:
                output += "."
                output += self._micro.decode("utf-8")
        if self._pre_release:
            output += "~"
            output += self._pre_release.decode("utf-8")
        if self._revision and self._revision > 0:
            output += "-"
            output += str(self._revision)
        return output


def read_attribute(f, strings):
    tag = read_unsigned_LEB128(f)
    if tag == 0:
        raise NullTag()
    type_ = attribute_tag_type(tag)
    if type_ > 4:
        raise ParseError()

    id_ = attribute_tag_id(tag)
    if id_ > 55:
        raise ParseError()

    encoding = attribute_tag_encoding(tag)

    if type_ == B_HPKG_ATTRIBUTE_TYPE_INVALID:
        raise ParseError()
    elif type_ == B_HPKG_ATTRIBUTE_TYPE_INT:
        if encoding == B_HPKG_ATTRIBUTE_ENCODING_INT_8_BIT:
            value = unpack('>b', f.read(1))[0]
        elif encoding == B_HPKG_ATTRIBUTE_ENCODING_INT_16_BIT:
            value = unpack('>h', f.read(2))[0]
        elif encoding == B_HPKG_ATTRIBUTE_ENCODING_INT_32_BIT:
            value = unpack('>i', f.read(4))[0]
        elif encoding == B_HPKG_ATTRIBUTE_ENCODING_INT_64_BIT:
            value = unpack('>q', f.read(8))[0]
        else:
            raise ParseError()
    elif type_ == B_HPKG_ATTRIBUTE_TYPE_UINT:
        if encoding == B_HPKG_ATTRIBUTE_ENCODING_INT_8_BIT:
            value = unpack('>B', f.read(1))[0]
        elif encoding == B_HPKG_ATTRIBUTE_ENCODING_INT_16_BIT:
            value = unpack('>H', f.read(2))[0]
        elif encoding == B_HPKG_ATTRIBUTE_ENCODING_INT_32_BIT:
            value = unpack('>I', f.read(4))[0]
        elif encoding == B_HPKG_ATTRIBUTE_ENCODING_INT_64_BIT:
            value = unpack('>Q', f.read(8))[0]
        else:
            raise ParseError()
    elif type_ == B_HPKG_ATTRIBUTE_TYPE_STRING:
        if encoding == B_HPKG_ATTRIBUTE_ENCODING_STRING_TABLE:
            index = read_unsigned_LEB128(f)
            if index > len(strings):
                raise ParseError()
            value = strings[index]
        elif encoding == B_HPKG_ATTRIBUTE_ENCODING_STRING_INLINE:
            data = []
            while True:
                b = f.read(1)
                if b is None or b == b'\0':
                    break
                data.append(b)
            value = b''.join(data)
        else:
            raise ParseError()
    else:
        raise ParseError()

    return id_, attribute_tag_has_children(tag), value


def get_repository_attributes(filename: str):
    with open(filename, "rb") as f:
        # read the repo header from the beginning of the file
        header = HpkgRepoHeader._make(unpack(REPO_HEADER_FORMAT, f.read(calcsize(REPO_HEADER_FORMAT))))
        if header.magic != b'hpkr' or header.version != 2 or header.minor_version != 1:
            raise ParseError()

        # get the heap
        heap = BytesIO()
        if header.heap_compression == 0:
            heap.write(f.read(header.heap_size_uncompressed))
        elif header.heap_compression == 1:
            offsets = []
            current_pos = f.tell()
            num_offsets = int((header.heap_size_uncompressed + header.heap_chunk_size - 1) / header.heap_chunk_size) - 1

            f.seek(header.heap_size_compressed - num_offsets * 2, SEEK_CUR)
            data = f.read(num_offsets * 2)
            offsets = list(struct.unpack(">%iH" % num_offsets, data))
            # calculate final offset
            final_offset = header.heap_size_compressed - num_offsets * 2 - sum(map(lambda x: x + 1, offsets)) - 1
            assert(final_offset > 0)
            offsets.append(final_offset)
            f.seek(current_pos, SEEK_SET)
            for offset in offsets:
                data = f.read(offset + 1)
                assert(len(data) == offset + 1)
                heap.write(decompress(data))
        else:
            raise ParseError()
        heap.seek(0)

        if len(heap.getvalue()) != header.heap_size_uncompressed:
            raise ParseError()

        # skip the repo info part of the heap
        heap.seek(0)
        heap.seek(header.info_length)

        # parse the package strings - the strings are null-terminated, and after the section, there is another null.
        strings = heap.read(header.packages_strings_length - 2).split(b'\0')
        heap.read(2)  # discard trailing null-characters of the strings section

        # parse attribute lists
        def build_attribute_tree(parent_node):
            while True:
                try:
                    id_, children, value = read_attribute(heap, strings)
                except NullTag:
                    break
                current_node = Attribute(id_, value)
                if children:
                    build_attribute_tree(current_node)
                parent_node.add_child(current_node)

        attributes = []
        while True:
            # get the first list
            try:
                id_, children, value = read_attribute(heap, strings)
                if children is not True or id_ != 54:
                    raise ParseError()
                attribute = Attribute(id_, value)

                build_attribute_tree(attribute)
                attributes.append(attribute)
            except NullTag:
                break

    return attributes


def add_packages_to_map(repo_info_path: str, baseurl: str, package_map: dict[str, (str, str)]):
    attributes = get_repository_attributes(repo_info_path)
    for package in attributes:
        if package.id != 54:
            raise ValueError()
        # A package filename is "%s-%s-%s.hpkg" (see BPackageInfo::CanonicalFileName()) with:
            # package name (at id 15)
            # package version (major id 22, children are minor id 23, micro id 24, revision id 25, prerelease id 36)
            # package arch (at id 21)
        basename = None
        version = None
        arch = None
        checksum = None
        for child in package.children:
            if child.id == 15: # package name
                if not isinstance(child.value, bytes) or len(child.value) == 0:
                    raise ValueError()
                basename = child.value.decode("utf-8")
            elif child.id == 22: # version; PackageVersion does checks on input
                version = PackageVersion(child.value)
                for version_component in child.children:
                    if version_component.id == 23:
                        version.minor = version_component.value
                    elif version_component.id == 24:
                        version.micro = version_component.value
                    elif version_component.id == 36:
                        version.pre_release = version_component.value
                    elif version_component.id == 25:
                        version.revision = version_component.value
                    else:
                        raise ValueError()
            elif child.id == 21: # architecture
                if not isinstance(child.value, int) or child.value < 0 or child.value >= len(B_PACKAGE_ARCHITECTURE_ENUM):
                    raise ValueError()
                arch = B_PACKAGE_ARCHITECTURE_ENUM[child.value]
            elif child.id == 35: # checksum
                if not isinstance(child.value, bytes) or len(child.value) == 0:
                    raise ValueError()
                checksum = child.value.decode("utf-8")

        if basename is None or version is None or arch is None or checksum is None:
            raise ValueError()

        package_url = "%s/packages/%s-%s-%s.hpkg" % (baseurl, basename, str(version), arch)
        package_map[basename] = (package_url, checksum)


#
# Repo info parsing
#


def parse_repository_info(info_file: bytes) -> dict[str, str]:
    lines = info_file.split(b'\n')
    info = {}
    for line in lines:
        if line == b'':
            continue
        elements = line.split(b' ', 1)
        if len(elements) != 2:
            raise ParseError()
        if elements[1][0] == b'"' and elements[1][-1] == b'"':
            info[elements[0].decode("utf-8")] = elements[1][1:-1].decode("utf-8")
        else:
            info[elements[0].decode("utf-8")] = elements[1].decode("utf-8")
    return info


#
# Fetch repo data
#

def fetch_repo_file(system_path, repo_name, repo_url):
    repo_dir_path = os.path.join(system_path, "cache", "package-repositories")
    os.makedirs(repo_dir_path, exist_ok=True)
    repo_file_path = os.path.join(repo_dir_path, repo_name)
    try:
        if repo_url[-1] != '/':
            repo_url = repo_url + '/'
        repo_info_url = urljoin(repo_url, "repo")
        result = urlopen(repo_info_url)
        if result.getcode() != 200:
            raise ValueError()
        with open(repo_file_path, "wb") as f:
            f.write(result.read())
        print("INFO: Retrieved package information for %s [%s]" % (repo_name, repo_url))
    except urllib.error.HTTPError as e:
        print("ERROR: Cannot fetch package information for url %s" % repo_url)
        print(str(e))
    except ValueError:
        print("ERROR: Cannot fetch package information for url %s" % repo_url)


#
# Repo Config Parsing and Writing
#

REPO_CONFIG_TEMPLATE="""
cfgversion=2
baseurl={baseurl}
identifier={identifier}
priority={priority}
"""


def write_repo_config(system_path, repo_info: dict[str, str]):
    repo_config = REPO_CONFIG_TEMPLATE.format(**repo_info)
    repo_dir_path = os.path.join(system_path, 'settings', 'package-repositories')
    os.makedirs(repo_dir_path, exist_ok=True)
    repo_file_path = os.path.join(repo_dir_path, repo_info['name'])
    with open(repo_file_path, "w") as f:
        f.write(repo_config)


def read_repo_config(repo_config_file):
    with open(repo_config_file, "r") as f:
        lines = f.readlines()
        repo_info = {}
        for line in lines:
            line = line.strip()
            if line == "":
                continue
            key, value = line.split('=', 1)
            repo_info[key] = value

        repo_info['name'] = os.path.split(repo_config_file)[-1]
        return repo_info


#
# Command: `add_repo`
#


def add_repo_command(system_path, urls):
    for url in urls:
        # try to get the repo.info for this URL
        try:
            if url[-1] != '/':
                url = url + '/'
            repo_info_url = urljoin(url, "repo.info")
            result = urlopen(repo_info_url)
            if result.getcode() != 200:
                raise ValueError()
            repo_info = parse_repository_info(result.read())
            write_repo_config(system_path, repo_info)
            print("INFO: Added/Updated repository %s" % url)
            fetch_repo_file(system_path, repo_info["name"], repo_info["baseurl"])
        except ValueError:
            print ("ERROR: Cannot add the repository at url %s" % url)
    pass


#
# Command: `refresh`
#


def refresh_command(system_path):
    repo_dir_path = os.path.join(system_path, 'settings', 'package-repositories')
    repo_config_files = os.listdir(repo_dir_path)
    for repo_config_file in repo_config_files:
        repo_info = read_repo_config(os.path.join(repo_dir_path, repo_config_file))
        print("INFO: Refreshing %s [%s]" % (repo_config_file, repo_info['baseurl']))
        fetch_repo_file(system_path, repo_info['name'], repo_info['baseurl'])


#
# Command: `install`
#


def install_command(system_path, packages):
    repo_dir_path = os.path.join(system_path, 'settings', 'package-repositories')
    repo_info_path = os.path.join(system_path, 'cache', 'package-repositories')
    repo_config_files = os.listdir(repo_dir_path)
    package_map = {}
    for repo_config_file in repo_config_files:
        repo_info = read_repo_config(os.path.join(repo_dir_path, repo_config_file))
        add_packages_to_map(os.path.join(repo_info_path, repo_config_file), repo_info['baseurl'], package_map)

    # process packages
    found_packages = []
    for package in packages:
        if package not in package_map.keys():
            print ("ERROR: Cannot find the package %s in the repositories" % package)
        print("INFO: Found package %s at url %s" % (package, package_map[package][0]))
        found_packages.append(package_map[package])

    # download and install packages one by one
    for package in found_packages:
        local_filename = None
        url = package[0]

        try:
            local_filename, headers = urllib.request.urlretrieve(url, filename=urllib.parse.urlsplit(url)[-1])
            # TODO: Check hash
            print ("INFO: Downloaded package %s" % local_filename)
            subprocess.run(["package", "extract", "-C", system_path, local_filename])
        except urllib.error.ContentTooShortError:
            print("ERROR: Premature end of file for package at %s" % url)
        except urllib.error.HTTPError:
            print("ERROR: Cannot fetch package for url %s" % url)
        finally:
            urllib.request.urlcleanup()


#
# __main__
#

parser = argparse.ArgumentParser(
    prog='pkgman',
    description='Interact with Haiku Package Repositories and install packages in a cross-compile environment'
)
parser.add_argument(
    '--system_path', type=str, default="/system/", help='The location of Haiku\'s system folder',
    metavar='/system/'
)
subparsers = parser.add_subparsers(dest='command')
add_repo_parser = subparsers.add_parser('add-repo')
add_repo_parser.add_argument('url', nargs='+')
subparsers.add_parser('refresh', help="Refresh all repositories on this system")
install_parser = subparsers.add_parser('install', help="Install one or more packages")
install_parser.add_argument('package', nargs='+')
if __name__ == '__main__':
    args = parser.parse_args()
    if args.command == 'add-repo':
        add_repo_command(args.system_path, args.url)
    elif args.command == 'refresh':
        refresh_command(args.system_path)
    elif args.command == 'install':
        install_command(args.system_path, args.package)
