"""Conservative trusted-log evidence checks. Never execute uploaded code."""
import json
import re
import posixpath
import shlex
from .pi_reader import text_content


def json_objects(text):
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\{', text):
        try:
            obj, _ = decoder.raw_decode(text[match.start():])
        except ValueError:
            continue
        if isinstance(obj, dict):
            yield obj


def solved(entries, problem):
    if not re.fullmatch(r'[a-z0-9_]+', problem):
        return False
    cwd = next((e.get('cwd', '/') for e in entries if e.get('type') == 'session'), '/')
    files = {}
    calls = {}
    for entry in entries:
        message = entry.get('message', {})
        if message.get('role') == 'assistant':
            content = message.get('content', [])
            for block in content if isinstance(content, list) else []:
                if block.get('type') != 'toolCall':
                    continue
                args = block.get('arguments', {})
                if not isinstance(args, dict):
                    continue
                name = block.get('name')
                path = args.get('path', args.get('file_path'))
                if isinstance(path, str):
                    path = posixpath.normpath(posixpath.join(cwd, path))
                if name == 'write' and isinstance(path, str):
                    files[path] = args.get('content', '')
                if name == 'edit' and isinstance(path, str) and path in files:
                    old, new = args.get('oldText'), args.get('newText')
                    if isinstance(old, str) and isinstance(new, str):
                        files[path] = files[path].replace(old, new)
                    else:
                        files.pop(path, None)
                command = args.get('command', '')
                if name == 'bash' and isinstance(command, str):
                    try:
                        words = shlex.split(command)
                    except ValueError:
                        words = []
                    references = {posixpath.normpath(posixpath.join(cwd, word)) for word in words}
                    source = command + '\n' + '\n'.join(
                        value for path, value in files.items()
                        if isinstance(value, str) and path in references)
                    explicit_slugs = re.findall(r'/challenges/([a-z0-9_]+)', source)
                    explicit_slugs += re.findall(
                        r"(?:slug|problem|challenge)\s*=\s*['\"]([a-z0-9_]+)['\"]", source)
                    # The requested problem is used when the script does not expose a slug.
                    # Reject explicit evidence for a different challenge.
                    calls[block.get('id')] = bool(
                        'hackattic.com' in source
                        and (not explicit_slugs or problem in explicit_slugs))
        elif message.get('role') == 'toolResult' and not message.get('isError'):
            if calls.get(message.get('toolCallId')):
                if any(obj.get('result') == 'passed' for obj in json_objects(text_content(message))):
                    return True
    return False
