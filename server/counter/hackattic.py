"""Conservative trusted-log evidence checks. Never execute uploaded code."""
import json
import re
from .pi_reader import text_content

PASSED_RESULTS = frozenset({'passed', 'passed (playground mode)'})


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
            # Hackattic replies "passed (playground mode)" to a re-solve sent with
            # &playground=1, which a student needs once they have solved it before.
            passed = passed or any(obj.get('result') in PASSED_RESULTS
                                   for obj in json_objects(text_content(message)))
    if not passed:
        return False
    # One command or file must name both Hackattic and the problem, however the URL
    # is assembled (base + path, f-strings, a slug variable). The slug must stand
    # alone, so help_me_unpack does not match help_me_unpack_extra.
    slug = re.compile(r'(?<![a-z0-9_])' + re.escape(problem) + r'(?![a-z0-9_])')
    return any('hackattic.com' in source and slug.search(source) for source in sources)
