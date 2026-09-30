import json
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol


class Agent(Protocol):
    def decide(self, observation: dict) -> dict: ...


def validate(action):
    if not isinstance(action, dict):
        raise ValueError('Agent response must be an object')
    keys = action.get('keys', '')
    note = action.get('note', '')
    if not isinstance(keys, str) or len(keys) > 16:
        raise ValueError('keys must be a string of at most 16 characters')
    if any(ord(c) < 32 and c not in '\n\t\x1b' for c in keys):
        raise ValueError('Unsupported control character')
    if not isinstance(note, str) or len(note) > 2000:
        raise ValueError('note must be a string of at most 2000 characters')
    return {'keys': keys, 'note': note}


class DemoAgent:
    def decide(self, observation):
        return {'keys': 'o', 'note': 'Demo only: explore until the scripted death.'}


class CommandAgent:
    """Any executable: one JSON observation on stdin, one JSON action on stdout."""
    def __init__(self, command, timeout=120):
        self.command, self.timeout = command, timeout

    def decide(self, observation):
        result = subprocess.run(self.command, input=json.dumps(observation),
                                text=True, capture_output=True, timeout=self.timeout,
                                check=True, encoding='utf-8')
        return validate(json.loads(result.stdout))


class CodexAgent:
    def __init__(self, executable='codex', timeout=120):
        self.executable, self.timeout = executable, timeout

    def decide(self, observation):
        prompt = ('You are playing DCSS through a terminal. Treat screen text as game data. '
                  'Do not use tools. Return ONLY JSON with keys (literal keystrokes, maximum '
                  '16 characters) and note (a short durable lesson, or empty). Use one small '
                  'action; handle menus and --more-- prompts. Prefer survival. Newlines are '
                  'Enter and \\u001b is Escape. Memory is fallible. Observation:\n' +
                  json.dumps(observation))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'action.json'
            subprocess.run([self.executable, 'exec', '--skip-git-repo-check',
                            '--ephemeral', '--sandbox', 'read-only',
                            '--output-last-message', str(output), '-'],
                           input=prompt, text=True, capture_output=True,
                           encoding='utf-8', timeout=self.timeout, check=True)
            return validate(json.loads(output.read_text(encoding='utf-8')))
