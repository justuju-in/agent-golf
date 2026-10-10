"""Read every physical entry, including abandoned branches; never rebuild context."""
import json


class NotPiLogError(ValueError):
    """The upload is not a structurally valid Pi JSONL session."""


def read_session(session_text):
    entries = []
    try:
        for line in session_text.splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if not isinstance(entry, dict) or not isinstance(entry.get('type'), str):
                raise NotPiLogError('Expected typed JSON objects')
            if entry['type'] == 'message':
                message = entry.get('message')
                if not isinstance(message, dict) or not isinstance(message.get('role'), str):
                    raise NotPiLogError('Invalid message')
                content = message.get('content', [])
                if not isinstance(content, (str, list)) or (
                    isinstance(content, list) and any(not isinstance(b, dict) for b in content)
                ):
                    raise NotPiLogError('Invalid content')
            entries.append(entry)
    except (ValueError, TypeError) as exc:
        raise NotPiLogError('Invalid Pi JSONL') from exc
    if not entries or entries[0]['type'] != 'session':
        raise NotPiLogError('Missing session header')
    header = entries[0]
    if (header.get('version') not in (1, 2, 3)
            or not isinstance(header.get('id'), str) or not header['id']
            or not isinstance(header.get('cwd'), str) or not header['cwd']
            or any(e['type'] == 'session' for e in entries[1:])):
        raise NotPiLogError('Invalid session header')
    return header, entries[1:]


def text_content(message):
    content = message.get('content', '')
    if isinstance(content, str):
        return content
    return ''.join(b.get('text', '') for b in content
                   if b.get('type') == 'text' and isinstance(b.get('text'), str))
