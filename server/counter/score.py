"""Pure Pi scoring. No database, network requests, or code execution."""
from datetime import datetime
from .pi_reader import read_session, text_content
from .hackattic import solved

NOT_SOLVED = 'not_solved'
MODEL_MISMATCH = 'model_mismatch'
THINKING_LEVEL_MISMATCH = 'thinking_level_mismatch'
FOLDER_REUSED = 'folder_reused'
CUSTOM_SETUP = 'custom_setup'
INCONSISTENT_LOG = 'inconsistent_log'
MISSING_USAGE = 'missing_usage'
USAGE_NOT_RECORDED = 'usage_not_recorded'
UNRANKING_REASONS = frozenset({NOT_SOLVED, MODEL_MISMATCH,
                             THINKING_LEVEL_MISMATCH, FOLDER_REUSED, MISSING_USAGE})
WARNING_REASONS = frozenset({CUSTOM_SETUP, INCONSISTENT_LOG, USAGE_NOT_RECORDED})


def score(session_text: str, problem: str, agreed: dict, prior_folders: set[str]) -> dict:
    header, entries = read_session(session_text)
    metrics = dict(total_tokens=0, prompts=0, chars_typed=0, tool_calls=0,
                   models=[], thinking_levels=[], solved=False)
    reasons = set()
    models, levels, seen = set(), set(), set()
    states = {}
    last_time = None
    assistant_count = 0

    def usage(value, required=False, errored=False):
        if value is None and not required:
            return
        total = value.get('totalTokens') if isinstance(value, dict) else None
        if errored and (total is None or total == 0) and not isinstance(total, bool):
            reasons.add(USAGE_NOT_RECORDED)
            return
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            reasons.add(MISSING_USAGE)
        else:
            metrics['total_tokens'] += total

    for entry in entries:
        kind = entry['type']
        eid, parent = entry.get('id'), entry.get('parentId')
        if not isinstance(eid, str) or eid in seen or (parent is not None and parent not in seen):
            reasons.add(INCONSISTENT_LOG)
        if isinstance(eid, str):
            seen.add(eid)
        try:
            stamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            if last_time is not None and stamp < last_time:
                reasons.add(INCONSISTENT_LOG)
            last_time = stamp
        except (KeyError, ValueError, TypeError, AttributeError):
            reasons.add(INCONSISTENT_LOG)
        model, level = states.get(parent, (None, None))
        if kind == 'model_change':
            model = f"{entry.get('provider', '')}/{entry.get('modelId', '')}"
            models.add(model)
        elif kind == 'thinking_level_change':
            level = entry.get('thinkingLevel')
            if isinstance(level, str):
                levels.add(level)
        message = entry.get('message', {})
        role = message.get('role')
        if role == 'user':
            metrics['prompts'] += 1
            metrics['chars_typed'] += len(text_content(message).replace('\r\n', '\n').replace('\r', '\n'))
            if any(b.get('type') == 'image' for b in message.get('content', []) if isinstance(b, dict)):
                reasons.add(INCONSISTENT_LOG)
        elif role == 'assistant':
            assistant_count += 1
            usage(message.get('usage'), required=True, errored=message.get('stopReason') in ('error', 'aborted'))
            actual_model = f"{message.get('provider', '')}/{message.get('model', '')}"
            models.add(actual_model)
            actual_level = message.get('thinkingLevel', level)
            if isinstance(actual_level, str):
                levels.add(actual_level)
            else:
                reasons.add(THINKING_LEVEL_MISMATCH)
            content = message.get('content', [])
            if isinstance(content, list):
                metrics['tool_calls'] += sum(b.get('type') == 'toolCall' for b in content)
        elif role == 'toolResult':
            usage(message.get('usage'))
        elif role == 'system':
            sections = message.get('sections', {})
            if isinstance(sections, dict) and any(sections.get(k) for k in ('skills', 'contextFiles', 'agents', 'rules')):
                reasons.add(CUSTOM_SETUP)
        if kind in ('usage', 'compaction', 'branch_summary'):
            usage(entry.get('usage'), required=True)
            if entry.get('model'):
                models.add(f"{entry.get('provider', '')}/{entry['model']}")
        if isinstance(eid, str):
            states[eid] = (model, level)
    if not assistant_count:
        reasons.add(MISSING_USAGE)
    if not models or models != {agreed.get('model')}:
        reasons.add(MODEL_MISMATCH)
    if not levels or levels != {agreed.get('thinking_level')}:
        reasons.add(THINKING_LEVEL_MISMATCH)
    if header['cwd'] in prior_folders:
        reasons.add(FOLDER_REUSED)
    if header.get('parentSession'):
        reasons.add(INCONSISTENT_LOG)
        reasons.add(MISSING_USAGE)
    metrics['models'], metrics['thinking_levels'] = sorted(models), sorted(levels)
    metrics['solved'] = solved([header, *entries], problem)
    if not metrics['solved']:
        reasons.add(NOT_SOLVED)
    if MISSING_USAGE in reasons:
        metrics['total_tokens'] = None
    return dict(session_id=header['id'], cwd=header['cwd'], metrics=metrics, reasons=sorted(reasons))
