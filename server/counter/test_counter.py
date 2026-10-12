import json
import unittest
from . import score, NotPiLogError

AGREED = {'model': 'openai/test', 'thinking_level': 'low'}


def log(*messages):
    entries = [{'type': 'session', 'version': 3, 'id': 'session', 'cwd': '/attempt'}]
    for i, m in enumerate(messages):
        entries.append({'type': 'message', 'id': str(i), 'parentId': str(i-1) if i else None,
                        'timestamp': '2026-10-10T10:00:00Z', 'message': m})
    return '\n'.join(json.dumps(e) for e in entries)


def assistant(total=10, content=None):
    return {'role': 'assistant', 'provider': 'openai', 'model': 'test',
            'thinkingLevel': 'low', 'usage': {'totalTokens': total}, 'content': content or []}


class CounterTests(unittest.TestCase):
    def test_hand_count_unicode_and_newlines(self):
        result = score(log({'role': 'user', 'content': [{'type': 'text', 'text': 'a\r\n😀\rb'}]},
                           assistant(12), assistant(8)), 'brute_force_zip', AGREED, set())
        self.assertEqual(result['metrics']['total_tokens'], 20)
        self.assertEqual(result['metrics']['chars_typed'], 5)
        self.assertEqual(result['metrics']['prompts'], 1)

    def test_normal_missing_usage_unknown(self):
        for value in (None, {}, {'totalTokens': None}):
            message = assistant()
            message['usage'] = value
            result = score(log(message), 'x', AGREED, set())
            self.assertIsNone(result['metrics']['total_tokens'])
            self.assertIn('missing_usage', result['reasons'])

    def test_error_and_aborted_usage_warning(self):
        from . import WARNING_REASONS, UNRANKING_REASONS
        for stop in ('error', 'aborted'):
            for value in (None, {}, {'totalTokens': None}, {'totalTokens': 0}):
                with self.subTest(stop=stop, value=value):
                    message = dict(assistant(), stopReason=stop, usage=value)
                    result = score(log(assistant(12), message), 'x', AGREED, set())
                    self.assertEqual(result['metrics']['total_tokens'], 12)
                    self.assertIn('usage_not_recorded', result['reasons'])
                    self.assertNotIn('missing_usage', result['reasons'])
        self.assertIn('usage_not_recorded', WARNING_REASONS)
        self.assertNotIn('usage_not_recorded', UNRANKING_REASONS)

    def test_error_with_recorded_usage_counts(self):
        result = score(log(dict(assistant(7), stopReason='error')), 'x', AGREED, set())
        self.assertEqual(result['metrics']['total_tokens'], 7)
        self.assertNotIn('usage_not_recorded', result['reasons'])

    def test_successful_zero_is_known(self):
        result = score(log(assistant(0)), 'x', AGREED, set())
        self.assertEqual(result['metrics']['total_tokens'], 0)
        self.assertNotIn('missing_usage', result['reasons'])

    def test_script_success_and_wrong_problem(self):
        messages = [assistant(content=[{'type': 'toolCall', 'id': 'write', 'name': 'write',
                    'arguments': {'path': '/tmp/solve.py', 'content': "base='https://hackattic.com/challenges/brute_force_zip/'; request(base+'solve')"}}]),
                    assistant(content=[{'type': 'toolCall', 'id': 'run', 'name': 'bash',
                    'arguments': {'command': 'python /tmp/solve.py'}}]),
                    {'role': 'toolResult', 'toolCallId': 'run', 'content': [{'type': 'text', 'text': 'SUBMISSION RESPONSE: {"result":"passed"}'}]}]
        self.assertTrue(score(log(*messages), 'brute_force_zip', AGREED, set())['metrics']['solved'])
        self.assertFalse(score(log(*messages), 'help_me_unpack', AGREED, set())['metrics']['solved'])
        messages[-1]['isError'] = True
        self.assertFalse(score(log(*messages), 'brute_force_zip', AGREED, set())['metrics']['solved'])

    def test_script_built_url_and_relative_reference(self):
        messages = [assistant(content=[{'type': 'toolCall', 'id': 'write', 'name': 'write',
                    'arguments': {'path': 'solve.py', 'content':
                        "host='hackattic.com'; slug='help_me_unpack'; url='https://'+host+'/challenges/'+slug+'/solve'"}}]),
                    assistant(content=[{'type': 'toolCall', 'id': 'run', 'name': 'bash',
                    'arguments': {'command': 'python solve.py'}}]),
                    {'role': 'toolResult', 'toolCallId': 'run', 'content': '{"result":"passed"}'}]
        result = score(log(*messages), 'help_me_unpack', AGREED, set())
        self.assertTrue(result['metrics']['solved'])
        self.assertNotIn('answer_mismatch', result['reasons'])
        self.assertEqual(result['reasons'], [])
        self.assertFalse(score(log(*messages), 'brute_force_zip', AGREED, set())['metrics']['solved'])
        messages[-1]['toolCallId'] = 'unrelated'
        self.assertFalse(score(log(*messages), 'help_me_unpack', AGREED, set())['metrics']['solved'])

    def test_thinking_level_change_is_not_reply_evidence(self):
        entries = [json.loads(line) for line in log(assistant()).splitlines()]
        entries[1]['message'].pop('thinkingLevel')
        entries.insert(1, {'type': 'thinking_level_change', 'id': 'level', 'parentId': None,
                          'thinkingLevel': 'low', 'timestamp': '2026-10-10T10:00:00Z'})
        entries[2]['parentId'] = 'level'
        result = score('\n'.join(map(json.dumps, entries)), 'x', AGREED, set())
        self.assertIn('thinking_level_mismatch', result['reasons'])
        self.assertEqual(result['metrics']['thinking_levels'], [])

    def test_any_setup_and_actual_model_switch(self):
        from . import UNRANKING_REASONS
        config = {'model': 'any', 'thinking_level': 'any'}
        first = assistant()
        second = dict(assistant(), model='other', thinkingLevel='high')
        result = score(log(first, second), 'x', config, set())
        self.assertIn('model_switched', result['reasons'])
        self.assertIn('model_switched', UNRANKING_REASONS)
        self.assertNotIn('model_mismatch', result['reasons'])
        self.assertNotIn('thinking_level_mismatch', result['reasons'])
        result = score(log(first, dict(assistant(), thinkingLevel='high')), 'x', config, set())
        self.assertNotIn('model_switched', result['reasons'])
        self.assertEqual(result['metrics']['thinking_levels'], ['high', 'low'])

    def test_initial_selection_events_ignored(self):
        entries = [json.loads(line) for line in log(assistant()).splitlines()]
        entries.insert(1, {'type': 'model_change', 'id': 'select', 'parentId': None,
                          'provider': 'other', 'modelId': 'unused', 'timestamp': '2026-10-10T10:00:00Z'})
        entries.insert(2, {'type': 'thinking_level_change', 'id': 'level', 'parentId': 'select',
                          'thinkingLevel': 'off', 'timestamp': '2026-10-10T10:00:00Z'})
        entries[3]['parentId'] = 'level'
        result = score('\n'.join(map(json.dumps, entries)), 'x', AGREED, set())
        self.assertEqual(result['metrics']['models'], ['openai/test'])
        self.assertEqual(result['metrics']['thinking_levels'], ['low'])
        self.assertEqual(result['reasons'], ['not_solved'])

    def test_missing_thinking_level_allowed_when_any(self):
        message = assistant()
        message.pop('thinkingLevel')
        result = score(log(message), 'x', dict(AGREED, thinking_level='any'), set())
        self.assertNotIn('thinking_level_mismatch', result['reasons'])

    def test_optional_summary_usage(self):
        for kind in ('compaction', 'branch_summary'):
            for value in (None, {}, {'totalTokens': None}, {'totalTokens': 0}, {'totalTokens': 5}):
                with self.subTest(kind=kind, value=value):
                    entries = [json.loads(line) for line in log(assistant(12)).splitlines()]
                    entry = {'type': kind, 'id': 'summary', 'parentId': '0',
                             'timestamp': '2026-10-10T10:00:00Z', 'model': 'not-a-reply', 'provider': 'other'}
                    if value is not None:
                        entry['usage'] = value
                    entries.append(entry)
                    result = score('\n'.join(map(json.dumps, entries)), 'x', AGREED, set())
                    recorded = (value or {}).get('totalTokens')
                    self.assertEqual(result['metrics']['total_tokens'], 12 + (recorded or 0))
                    self.assertNotIn('missing_usage', result['reasons'])
                    self.assertEqual('usage_not_recorded' in result['reasons'], (value or {}).get('totalTokens') is None)
                    self.assertEqual(result['metrics']['models'], ['openai/test'])

    def test_usage_entries_include_answering_model(self):
        entries = [json.loads(line) for line in log(assistant()).splitlines()]
        entries.append({'type': 'usage', 'id': 'warm', 'parentId': '0',
                        'timestamp': '2026-10-10T10:00:00Z', 'model': 'other',
                        'provider': 'openai', 'usage': {'totalTokens': 7}})
        result = score('\n'.join(map(json.dumps, entries)), 'x', {'model': 'any', 'thinking_level': 'any'}, set())
        self.assertEqual(result['metrics']['total_tokens'], 17)
        self.assertEqual(result['metrics']['models'], ['openai/other', 'openai/test'])
        self.assertIn('model_switched', result['reasons'])

    def test_fork_usage_stays_unknown(self):
        entries = [json.loads(line) for line in log(assistant()).splitlines()]
        entries[0]['parentSession'] = '/not-loaded.jsonl'
        result = score('\n'.join(map(json.dumps, entries)), 'x', AGREED, set())
        self.assertIsNone(result['metrics']['total_tokens'])
        self.assertIn('missing_usage', result['reasons'])

    def test_reason_sets_match_final_contract(self):
        from . import UNRANKING_REASONS, WARNING_REASONS
        self.assertEqual(UNRANKING_REASONS, {
            'not_solved', 'model_mismatch', 'thinking_level_mismatch',
            'model_switched', 'folder_reused', 'missing_usage'})
        self.assertEqual(WARNING_REASONS, {
            'custom_setup', 'inconsistent_log', 'usage_not_recorded'})

    def test_real_zip_has_only_model_that_answered(self):
        from pathlib import Path
        from . import UNRANKING_REASONS
        text = (Path(__file__).resolve().parents[2] / 'samples' / 'real-zip-redacted.jsonl').read_text()
        for agreed in ({'model': 'openai/gpt-6.1-sol', 'thinking_level': 'low'},
                       {'model': 'any', 'thinking_level': 'any'}):
            result = score(text, 'brute_force_zip', agreed, set())
            self.assertEqual(result['metrics']['models'], ['openai/gpt-6.1-sol'])
            self.assertEqual(result['metrics']['thinking_levels'], ['low'])
            self.assertFalse(set(result['reasons']) & UNRANKING_REASONS)
            self.assertEqual(result['reasons'], ['usage_not_recorded'])

    def test_redacted_real_uploads(self):
        from pathlib import Path
        samples = Path(__file__).resolve().parents[2] / 'samples'
        for filename, tokens, prompts, chars, tools, passed in (
            ('real-zip-redacted.jsonl', 202053, 10, 599, 15, True),
            ('real-second-redacted.jsonl', 79221, 2, 41, 9, False),
        ):
            result = score((samples / filename).read_text(), 'brute_force_zip', AGREED, set())
            m = result['metrics']
            self.assertEqual((m['total_tokens'], m['prompts'], m['chars_typed'], m['tool_calls'], m['solved']),
                             (tokens, prompts, chars, tools, passed))

    def test_assistant_claim_is_not_success(self):
        self.assertFalse(score(log(assistant(content=[{'type': 'text', 'text': '{"result":"passed"}'}])), 'x', AGREED, set())['metrics']['solved'])

    def test_setup_and_folder(self):
        result = score(log(assistant()), 'x', {'model': 'other', 'thinking_level': 'high'}, {'/attempt'})
        self.assertTrue({'model_mismatch', 'thinking_level_mismatch', 'folder_reused'} <= set(result['reasons']))

    def test_bad_uploads(self):
        for text in ('', '{}', 'not json', '[1]', log(assistant())+'\n{'):
            with self.assertRaises(NotPiLogError):
                score(text, 'x', AGREED, set())

    def test_all_branches_and_auxiliary_usage(self):
        entries = [json.loads(line) for line in log(assistant(10), assistant(20)).splitlines()]
        entries[-1]['parentId'] = None
        for kind in ('usage', 'compaction', 'branch_summary'):
            entries.append({'type': kind, 'id': kind, 'parentId': None,
                            'timestamp': '2026-10-10T10:00:00Z', 'usage': {'totalTokens': 3}})
        result = score('\n'.join(map(json.dumps, entries)), 'x', AGREED, set())
        self.assertEqual(result['metrics']['total_tokens'], 39)



if __name__ == '__main__':
    unittest.main()
