import shlex
import subprocess
import time


class Tmux:
    def __init__(self, command, session='dcss-idle'):
        self.command, self.session = command, session
        self.pane = None

    def call(self, *args):
        return subprocess.run(['tmux', *args], text=True, capture_output=True,
                              check=True, timeout=10).stdout.strip()

    def start(self):
        # A private socket avoids touching existing user sessions.
        self.pane = self.call('-L', self.session, 'new-session', '-d', '-P',
                              '-F', '#{pane_id}', '-s', 'game', '-x', '100', '-y', '35',
                              shlex.join(self.command))
        self.call('-L', self.session, 'set-option', '-w', '-t', self.pane,
                  'remain-on-exit', 'on')

    def capture(self):
        return self.call('-L', self.session, 'capture-pane', '-p', '-t', self.pane)

    def dead(self):
        return self.call('-L', self.session, 'display-message', '-p', '-t', self.pane,
                         '#{pane_dead}') == '1'

    def send(self, keys):
        for char in keys:
            special = {'\n': 'Enter', '\t': 'Tab', '\x1b': 'Escape'}.get(char)
            args = ['-L', self.session, 'send-keys', '-t', self.pane]
            self.call(*(args + ([special] if special else ['-l', '--', char])))

    def restart(self):
        self.call('-L', self.session, 'respawn-pane', '-k', '-t', self.pane,
                  shlex.join(self.command))

    def stable(self, timeout=3):
        previous = self.capture()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(.15)
            current = self.capture()
            if current == previous:
                return current
            previous = current
        return previous
