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

    def test_missing_and_error_usage_unknown(self):
        for message in ({'role': 'assistant', 'content': []}, dict(assistant(0), stopReason='error')):
            result = score(log(message), 'x', AGREED, set())
            self.assertIsNone(result['metrics']['total_tokens'])
            self.assertIn('missing_usage', result['reasons'])

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

    def test_unpack_recheck(self):
        import base64
        import struct
        from .hackattic import answer_matches
        data = struct.pack('<iIh', -3, 7, -2) + b'\0\0' + struct.pack('<f', 1.5) + struct.pack('<d', 2.5) + struct.pack('>d', 3.5)
        problem = {'bytes': base64.b64encode(data).decode()}
        answer = dict(int=-3, uint=7, short=-2, float=1.5, double=2.5, big_endian_double=3.5)
        def entries():
            return [{'message': {'role': 'toolResult', 'content': json.dumps(problem)+'\n'+json.dumps(answer)}}]
        self.assertTrue(answer_matches(entries()))
        answer['int'] = 99
        self.assertFalse(answer_matches(entries()))


if __name__ == '__main__':
    unittest.main()
