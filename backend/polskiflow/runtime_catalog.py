"""Conservative browser catalogue projection; gettext remains authoritative.

Keep every key mentioned anywhere in templates/JS, including non-translation
string tables, not only calls to a specific helper. Keep every interpolation
key and explicit dynamic manifest entry even if its source is assembled.
Do not try to prune individual routes or defer the synchronous dictionary.
"""
import json
import re


def runtime_catalog(translations, sources, dynamic_messages):
    if not isinstance(dynamic_messages, list) or any(not isinstance(key, str) for key in dynamic_messages):
        raise ValueError('Invalid dynamic browser manifest.')
    if any(key not in translations for key in dynamic_messages):
        raise ValueError('Dynamic browser messages missing from gettext.')
    source = '\n'.join(sources)
    # Add a conservative decoded view, never replace the original: escaped
    # literals, line continuations and string tables must not disappear.
    escapes = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f',
               'v': '\v', '0': '\0', '/': '/', "'": "'", '"': '"', '\\': '\\'}
    def decode(match):
        token = match.group(1)
        if token.startswith(('u', 'x')):
            return chr(int(token[1:], 16))
        return escapes.get(token, '')
    source += '\n' + re.sub(r'\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|\r?\n|[nrtbfv0/\'"\\])', decode, source)
    dynamic = set(dynamic_messages)
    def referenced(key):
        single_quoted = (key.replace('\\', '\\\\').replace("'", "\\'")
                         .replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t'))
        variants = (key, json.dumps(key, ensure_ascii=False)[1:-1],
                    json.dumps(key, ensure_ascii=True)[1:-1], single_quoted)
        return key in dynamic or '%(v' in key or any(value in source for value in variants)
    return {key: value for key, value in translations.items() if referenced(key)}


def browser_sources(backend):
    paths = sorted((backend / 'templates').rglob('*.html'))
    paths += sorted(path for path in (backend / 'polskiflow/learning/static').rglob('*.js')
                    if not path.name.startswith('i18n-'))
    return [path.read_text() for path in paths]
