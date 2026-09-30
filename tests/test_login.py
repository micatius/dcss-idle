import unittest
from idle.login import Login


class Tests(unittest.TestCase):
    def test_login(self):
        login = Login({'username': 'alice', 'password': 'secret-value',
                       'success_pattern': '^Welcome', 'steps': [
                           {'pattern': '^Username:', 'value': 'username'},
                           {'pattern': '^Password:', 'value': 'password'}]})
        class Terminal:
            def __init__(self): self.sent = []
            def dead(self): return False
            def stable(self): return ['Username:', 'Password:', 'Welcome'][len(self.sent)]
            def send(self, value): self.sent.append(value)
        terminal = Terminal()
        login.authenticate(terminal)
        self.assertEqual(terminal.sent, ['alice\n', 'secret-value\n'])
        self.assertEqual(login.redact('alice secret-value'), '[REDACTED] [REDACTED]')
        terminal.dead = lambda: True
        with self.assertRaisesRegex(RuntimeError, 'exited'):
            login.authenticate(terminal)

    def test_invalid_credentials(self):
        with self.assertRaises(ValueError):
            Login({'username': 'a\nb', 'password': 'x'})
