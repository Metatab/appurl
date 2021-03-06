
# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# MIT, included in this distribution as LICENSE

""" """

import re
from os import makedirs
from os.path import isdir, dirname, splitext, exists
from urllib.parse import unquote_plus, ParseResult, urlparse, quote_plus, parse_qs, urlencode, unquote

from six import text_type

# From http://stackoverflow.com/a/295466
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.type(
    """
    import re
    import unicodedata
    from six import text_type
    value = text_type(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('utf8').strip().lower()
    value = re.sub(r'[^\w\s\-\.]', '', value)
    value = re.sub(r'[-\s]+', '-', value)
    return value

def fs_join(*args):
    """Like os.path.join, but never returns '\' chars"""
    from os.path import join
    return join(*args).replace('\\','/')

def path2url(path):
    "Convert a pathname to a file URL"
    try:
        # Python 3
        # http://stackoverflow.com/a/30702300
        from urllib.parse import urljoin
        from urllib.request import pathname2url
    except ImportError:
        # Python 2
        from urllib.parse import urljoin
        from urllib import pathname2url

    return urljoin('file:', pathname2url(path))

def parse_url_to_dict(url, assume_localhost=False):
    """Parse a url and return a dict with keys for all of the parts.

    The urlparse function() returns a wacky combination of a namedtuple
    with properties.

    """

    assert url is not None

    url = text_type(url)

    if re.match(r'^[a-zA-Z]:', url):
        url = path2url(url)

        p = urlparse(unquote_plus(url))

        # urlparse leaves a '/' before the drive letter.
        p = ParseResult(p.scheme, p.netloc, p.path.lstrip('/'), p.params, p.query, p.fragment)

    else:
        p = urlparse(url)

    #  '+' indicates that the scheme has a scheme extension
    if '+' in p.scheme:
        scheme_extension, scheme = p.scheme.split('+')
    else:
        scheme = p.scheme
        scheme_extension = None

    if scheme is '':
        scheme = 'file'

    frag_whole = unquote_plus(p.fragment) if p.fragment else ''

    frag_parts = frag_whole.split('&', 1)

    if frag_parts and '=' not in frag_parts[0]:
        frag = frag_parts.pop(0)
    else:
        frag = None

    frag_rem = frag_parts.pop(0) if frag_parts else None

    # parse_qs returns lists for values, since queries can have multiple keys with different values,
    # but we expect unique values
    frag_query = { k:v[0] for k, v in  (parse_qs(frag_rem) if p.fragment else {}).items()  }

    if frag:
        frag_sub_parts = frag.split(';')

        if len(frag_sub_parts) < 2:
            frag_sub_parts = [frag_sub_parts[0], None]

    else:
        frag_sub_parts = [None, None]

    return {
        'scheme': scheme,
        'scheme_extension': scheme_extension,
        'netloc': p.netloc,
        'hostname': p.hostname,
        'path': p.path,
        'params': p.params,
        'query': p.query,
        'fragment':  frag_sub_parts,
        'fragment_query': frag_query,
        'username': p.username,
        'password': p.password,
        'port': p.port
    }

def unparse_url_dict(d, **kwargs):

    d = dict(d.items())

    d.update(kwargs)

    if '_fragment' in d and 'fragment' not in d:
        d['fragment'] = d['_fragment']

    if 'netloc' in d and d['netloc']:
        host_port = d['netloc']
    else:
        host_port = ''

    if 'port' in d and d['port']:
        host_port += ':' + str(d['port'])

    user_pass = ''
    if 'username' in d and d['username']:
        user_pass += d['username']

    if 'password' in d and d['password']:
        user_pass += ':' + d['password']

    if user_pass:
        host_port = '{}@{}'.format(user_pass, host_port)

    if d.get('scheme') and host_port:
        url = '{}://{}/{}'.format(d['scheme'],host_port, d.get('path', '').lstrip('/'))
    elif d.get('scheme') in ('mailto', 'file'):
        url = '{}:{}'.format(d['scheme'], d.get('path', ''))
    elif d.get('scheme'):
        url = '{}://{}'.format(d['scheme'], d.get('path', '').lstrip('/'))
    elif d.get('path'):
        # It's possible just a local file url.
        # This isn't the standard file: url form, which is specified to have a :// and a host part,
        # like 'file://localhost/etc/config', but that form can't handle relative URLs ( which don't start with '/')
        url = 'file:'+d['path'].lstrip('/')
    else:
        url = ''

    if d.get('scheme_extension'):
        url = d['scheme_extension']+'+'+url

    if 'query' in d and d['query']:
        url += '?' + d['query']

    if d.get('fragment') or d.get('fragment_query'):

        if isinstance(d.get('fragment'),(list, tuple)):

            seg = ';'.join(quote_plus(str(e)) for e in [ e for e in d.get('fragment') if e])
        else:
            seg = quote_plus(d.get('fragment'))

        if d.get('fragment_query'):
            fqt = sorted(d.get('fragment_query').items())
            query = '&' + urlencode(fqt,doseq=True)
        else:
            query = ''


        if seg or query:
            url += "#"+seg+unquote(query)

    return url

def reparse_url(url, **kwargs):

    assume_localhost = kwargs.get('assume_localhost', False)

    return unparse_url_dict(parse_url_to_dict(url,assume_localhost),**kwargs)

def join_url_path(url, *paths):
    """Like path.os.join, but operates on the url path, ignoring the query and fragments."""

    parts = parse_url_to_dict(url)

    return reparse_url(url, path=os.path.join(parts['path']))

def file_ext(v):
    """Split of the extension of a filename, without throwing an exception of there is no extension. Does not
    return the leading '.'
    :param v: """

    try:
        v = splitext(v)[1][1:]

        if v == '*':  # Not a file name, probably a fragment regex
            return None

        return v.lower() if v else None
    except IndexError:
        return None



def copy_file_or_flo(input_, output, buffer_size=64 * 1024, cb=None):
    """ Copy a file name or file-like-object to another file name or file-like object"""

    assert bool(input_)
    assert bool(output)

    input_opened = False
    output_opened = False

    try:
        if isinstance(input_, str):

            if not isdir(dirname(input_)):
                makedirs(dirname(input_))

            input_ = open(input_, 'r')
            input_opened = True

        if isinstance(output, str):

            if not isdir(dirname(output)):
                makedirs(dirname(output))

            output = open(output, 'wb')
            output_opened = True

        # shutil.copyfileobj(input_,  output, buffer_size)

        def copyfileobj(fsrc, fdst, length=buffer_size):
            cumulative = 0
            while True:
                buf = fsrc.read(length)
                if not buf:
                    break
                fdst.write(buf)
                if cb:
                    cumulative += len(buf)
                    cb(len(buf), cumulative)

        copyfileobj(input_, output)

    finally:
        if input_opened:
            input_.close()

        if output_opened:
            output.close()


DEFAULT_CACHE_NAME = 'appurl'

def get_cache(cache_name=DEFAULT_CACHE_NAME, clean=False):
    """Return the path to a file cache"""

    from fs.osfs import OSFS
    from fs.appfs import UserDataFS
    from fs.errors import CreateFailed
    import os

    env_var = (cache_name+'_cache').upper()

    cache_dir = os.getenv(env_var, None)


    if cache_dir:
        try:
            return OSFS(cache_dir)
        except CreateFailed as e:
            raise CreateFailed("Failed to create '{}': {} ".format(cache_dir, e))
    else:

        try:
            return UserDataFS(cache_name.lower())
        except CreateFailed as e:
            raise CreateFailed("Failed to create '{}': {} ".format(cache_name.lower(), e))


def clean_cache(cache = None, cache_name=DEFAULT_CACHE_NAME):
    """Delete items in the cache older than 4 hours"""
    import datetime

    cache = cache if cache else get_cache(cache_name)

    for step in cache.walk.info():
        details = cache.getdetails(step[0])
        mod = details.modified
        now = datetime.datetime.now(tz=mod.tzinfo)
        age = (now - mod).total_seconds()
        if age > (60 * 60 * 4) and details.is_file:
            cache.remove(step[0])

def nuke_cache(cache = None, cache_name=DEFAULT_CACHE_NAME):
    """Delete Everythong in the cache"""

    cache = cache if cache else get_cache(cache_name)

    for step in cache.walk.info():
        if not step[1].is_dir:
            cache.remove(step[0])

def ensure_dir(path):

    if path and not exists(path):
            makedirs(path)


def import_name_or_class(name):
    " Import an obect as either a fully qualified, dotted name, "

    if isinstance(name, str):

        # for "a.b.c.d" -> [ 'a.b.c', 'd' ]
        module_name, object_name = name.rsplit('.',1)
        # __import__ loads the multi-level of module, but returns
        # the top level, which we have to descend into
        mod = __import__(module_name)

        components = name.split('.')

        for comp in components[1:]: # Already got the top level, so start at 1

            mod = getattr(mod, comp)
        return mod
    else:
        return name # Assume it is already the thing we want to import
