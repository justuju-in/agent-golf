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
    """Trusted session evidence: requested challenge mentioned and a passed result.

    Commands may create/run files in different calls or directories. A later shell
    error does not invalidate an already printed Hackattic acceptance response.
    No uploaded code is executed and no shell/filesystem dataflow is inferred.
    """
    if not re.fullmatch(r'[a-z0-9_]+', problem):
        return False
    sources = []
    passed = False
    for entry in entries:
        message = entry.get('message', {})
        role = message.get('role')
        if role == 'assistant':
            content = message.get('content', [])
            for block in content if isinstance(content, list) else []:
                if block.get('type') != 'toolCall':
                    continue
                args = block.get('arguments', {})
                if not isinstance(args, dict):
                    continue
                fields = {'bash': ('command',), 'write': ('content',),
                          'edit': ('newText',)}.get(block.get('name'), ())
                sources.extend(args[key] for key in fields if isinstance(args.get(key), str))
        elif role == 'bashExecution' and isinstance(message.get('command'), str):
            sources.append(message['command'])
        elif role == 'toolResult':
            passed = passed or any(obj.get('result') == 'passed'
                                   for obj in json_objects(text_content(message)))
    if not passed:
        return False
    endpoint = re.compile(r'hackattic\.com/challenges/' + re.escape(problem) + r'(?![a-z0-9_])')
    if any(endpoint.search(source) for source in sources):
        return True
    # Retain support for explicitly named slugs in script-built URLs.
    # Host-only evidence cannot distinguish the submitted problem.
    for source in sources:
        slugs = re.findall(r"(?:slug|problem|challenge)\s*=\s*['\"]([a-z0-9_]+)['\"]", source)
        if 'hackattic.com' in source and problem in slugs:
            return True
    return False
