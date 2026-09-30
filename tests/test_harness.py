import json
import sys
import tempfile
import unittest
from pathlib import Path
from idle.__main__ import DEATH, Memory, run
from idle.backends import CommandAgent, DemoAgent, validate


class Terminal:
    def __init__(self):
        self.screen = 'HP: 5/5'
        self.restarts = 0
        self.actions = []

    def stable(self): return self.screen
    def capture(self): return self.screen
    def dead(self): return False
    def send(self, keys):
        self.actions.append(keys)
        self.screen = 'You die.'
    def restart(self):
        self.restarts += 1
        self.screen = 'HP: 5/5'


class Tests(unittest.TestCase):
    def test_death_restart_and_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            terminal = Terminal()
            run(terminal, DemoAgent(), Memory(folder), 4, 0)
            self.assertEqual(terminal.restarts, 2)
            events = [json.loads(x) for x in (Path(folder)/'events.jsonl').read_text().splitlines()]
            self.assertEqual(sum(x['type'] == 'death' for x in events), 2)
            self.assertEqual(len(Memory(folder).recall()), 2)

    def test_remote_death_not_respawned(self):
        with tempfile.TemporaryDirectory() as folder:
            terminal = Terminal()
            run(terminal, DemoAgent(), Memory(folder), 3, 0, False)
            self.assertEqual(terminal.restarts, 0)
            events = (Path(folder)/'events.jsonl').read_text()
            self.assertEqual(events.count('"type": "death"'), 1)

    def test_stale_action(self):
        class ChangingAgent:
            def decide(self, observation):
                terminal.screen = 'changed'
                return {'keys': 'o'}
        with tempfile.TemporaryDirectory() as folder:
            terminal = Terminal()
            run(terminal, ChangingAgent(), Memory(folder), 1, 0)
            self.assertEqual(terminal.actions, [])

    def test_validation(self):
        for action in [[], {'keys': 'x'*17}, {'keys': '\x03'}, {'note': 3}]:
            with self.assertRaises(ValueError): validate(action)
        self.assertEqual(validate({'keys': '\n'}), {'keys': '\n', 'note': ''})
        self.assertFalse(DEATH.search('The inscription says You die.'))

    def test_command_contract(self):
        command = [sys.executable, '-c', 'import json,sys; o=json.load(sys.stdin); print(json.dumps({"keys":"o","note":o["screen"]}))']
        self.assertEqual(CommandAgent(command).decide({'screen': 'hello'})['note'], 'hello')


if __name__ == '__main__': unittest.main()
