"""Deterministic console login; credentials never belong in agent observations."""
import re
import time
import tomllib
from pathlib import Path


class Login:
    def __init__(self, config):
        self.username = config['username']
        self.password = config['password']
        for value in (self.username, self.password):
            if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
                raise ValueError('Login credentials must be nonempty single-line strings')
        self.steps = config['steps']
        self.success = config['success_pattern']
        self.timeout = config.get('timeout', 60)
        if not isinstance(self.timeout, (int, float)) or not 0 < self.timeout <= 300:
            raise ValueError('Login timeout must be between 0 and 300 seconds')
        re.compile(self.success, re.I | re.M)
        for step in self.steps:
            re.compile(step['pattern'], re.I | re.M)
            if step['value'] not in ('username', 'password', 'literal'):
                raise ValueError('Login step value must be username, password or literal')

    @classmethod
    def load(cls, path):
        with Path(path).open('rb') as f:
            return cls(tomllib.load(f))

    def redact(self, text):
        for secret in sorted((self.username, self.password), key=len, reverse=True):
            text = text.replace(secret, '[REDACTED]')
        return text

    def wait(self, terminal, pattern):
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if terminal.dead():
                raise RuntimeError('Connection exited during login')
            screen = terminal.stable()
            if re.search(pattern, screen, re.I | re.M):
                return
            time.sleep(.2)
        raise RuntimeError('Login prompt timed out; inspect the tmux pane and login patterns')

    def authenticate(self, terminal):
        for step in self.steps:
            self.wait(terminal, step['pattern'])
            value = step.get('keys', '') if step['value'] == 'literal' else getattr(self, step['value']) + '\n'
            try:
                terminal.send(value)
            except Exception:
                # Subprocess error representations can contain the keystrokes.
                raise RuntimeError('Could not send login input') from None
        self.wait(terminal, self.success)
