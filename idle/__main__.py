import argparse
import json
import re
import shlex
import time
from pathlib import Path
from .backends import CodexAgent, CommandAgent, DemoAgent, validate
from .terminal import Tmux
from .login import Login

DEATH = re.compile(r'^\s*(?:You die(?:[.!]|$)|You have died(?:[.!]|$))', re.M)


class Memory:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.notes = self.folder / 'notes.jsonl'

    def event(self, **event):
        with (self.folder / 'events.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps({'time': time.time(), **event}) + '\n')

    def remember(self, note):
        if note:
            with self.notes.open('a', encoding='utf-8') as f:
                f.write(json.dumps(note) + '\n')

    def recall(self):
        if not self.notes.exists():
            return []
        return [json.loads(line) for line in self.notes.read_text(encoding='utf-8').splitlines()[-20:]]


def run(terminal, agent, memory, steps, delay, restart_on_death=True, login=None):
    run_id = f'{time.time_ns()}'
    death_seen = False
    recent = []
    for step in range(steps):
        if (memory.folder / 'PAUSE').exists():
            time.sleep(.5)
            continue
        raw_screen = terminal.stable()
        screen = login.redact(raw_screen) if login else raw_screen
        if login and re.search(r'(?:password|username|user name|login name):\s*$', raw_screen, re.I | re.M):
            raise RuntimeError('Authentication prompt reappeared; restart the harness to log in again')
        died = bool(DEATH.search(screen))
        exited = terminal.dead()
        if died and not death_seen:
            memory.event(type='death', run=run_id, screen=screen)
            death_seen = True
            if restart_on_death:
                terminal.restart()
                run_id = f'{time.time_ns()}'
                death_seen = False
                recent = []
                time.sleep(delay)
                continue
        if exited:
            memory.event(type='exit', run=run_id, screen=screen)
            # Unknown exits may be disconnects or configuration errors. Stop.
            return
        observation = {'version': 1, 'run': run_id, 'step': step,
                       'screen': screen, 'notes': memory.recall(), 'recent': recent[-5:]}
        action = validate(agent.decide(observation))
        # Reject stale decisions if the terminal changed while the model thought.
        if terminal.capture() != raw_screen:
            memory.event(type='stale_action', run=run_id)
            continue
        memory.event(type='action', run=run_id, observation=observation, action=action)
        memory.remember(action['note'])
        terminal.send(action['keys'])
        recent.append({'keys': action['keys'], 'note': action['note']})
        print(f"{step}: {action!r}", flush=True)
        time.sleep(delay)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--game', default='crawl')
    p.add_argument('--backend', choices=['codex', 'command', 'demo'], default='codex')
    p.add_argument('--agent-command')
    p.add_argument('--codex', default='codex')
    p.add_argument('--session', default='dcss-idle')
    p.add_argument('--memory', default='state')
    p.add_argument('--steps', type=int, default=1000)
    p.add_argument('--delay', type=float, default=1)
    p.add_argument('--remote', action='store_true', help='Never respawn on death; let agent navigate lobby')
    p.add_argument('--login-config', help='Private TOML credentials and console login prompts (remote only)')
    a = p.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', a.session):
        p.error('session must contain only letters, digits, underscores or hyphens')
    if a.steps < 1 or a.delay < 0:
        p.error('steps must be positive and delay nonnegative')
    if a.backend == 'command' and not a.agent_command:
        p.error('--agent-command is required')
    if a.login_config and not a.remote:
        p.error('--login-config requires --remote')
    login = Login.load(a.login_config) if a.login_config else None
    agent = {'demo': lambda: DemoAgent(), 'codex': lambda: CodexAgent(a.codex),
             'command': lambda: CommandAgent(shlex.split(a.agent_command))}[a.backend]()
    terminal = Tmux(shlex.split(a.game), a.session)
    memory = Memory(a.memory)
    try:
        terminal.start()
        print(f'Watch: tmux -L {a.session} attach -r -t game', flush=True)
        if login:
            login.authenticate(terminal)
            memory.event(type='login_complete')
        run(terminal, agent, memory, a.steps, a.delay, not a.remote, login)
    except KeyboardInterrupt:
        print('Stopped harness; game remains in tmux.')
    except Exception as error:
        message = login.redact(str(error)) if login else str(error)
        memory.event(type='error', error=message)
        raise SystemExit(f'Harness stopped; game remains available: {message}')


if __name__ == '__main__':
    main()
