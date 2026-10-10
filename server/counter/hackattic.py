"""Conservative trusted-log evidence checks. Never execute uploaded code."""
import json
import re
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
    endpoint = re.compile(r'https://hackattic\.com/challenges/' + re.escape(problem) + r'/')
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
                if name == 'write' and isinstance(path, str):
                    files[path] = args.get('content', '')
                if name == 'edit' and path in files:
                    old, new = args.get('oldText'), args.get('newText')
                    if isinstance(old, str) and isinstance(new, str):
                        files[path] = files[path].replace(old, new)
                    else:
                        files.pop(path, None)
                command = args.get('command', '')
                if name == 'bash' and isinstance(command, str):
                    source = command + '\n' + '\n'.join(
                        value for path, value in files.items()
                        if isinstance(value, str) and path in command)
                    calls[block.get('id')] = bool(endpoint.search(source) and 'solve' in source)
        elif message.get('role') == 'toolResult' and not message.get('isError'):
            if calls.get(message.get('toolCallId')):
                if any(obj.get('result') == 'passed' for obj in json_objects(text_content(message))):
                    return True
    return False


def answer_matches(entries):
    """Recheck only explicit JSON input/answer pairs printed in tool output.

    Missing evidence is not a match. Never infer a submitted answer from AI prose.
    """
    import base64
    import math
    import struct
    expected = None
    for entry in entries:
        message = entry.get('message', {})
        if message.get('role') != 'toolResult' or message.get('isError'):
            continue
        for obj in json_objects(text_content(message)):
            if isinstance(obj.get('bytes'), str):
                try:
                    data = base64.b64decode(obj['bytes'], validate=True)
                    if len(data) != 32:
                        expected = None
                        continue
                    values = struct.unpack('<iIh', data[:10]) + (struct.unpack('<f', data[12:16])[0],) + (struct.unpack('<d', data[16:24])[0], struct.unpack('>d', data[24:32])[0])
                    expected = dict(zip(('int', 'uint', 'short', 'float', 'double', 'big_endian_double'), values))
                except (ValueError, struct.error):
                    expected = None
            elif expected and all(key in obj for key in expected):
                if all(isinstance(obj[key], (int, float)) and not isinstance(obj[key], bool)
                       and math.isclose(obj[key], value, rel_tol=1e-6, abs_tol=1e-7)
                       for key, value in expected.items()):
                    return True
    return False
