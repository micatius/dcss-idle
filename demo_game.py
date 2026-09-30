"""POSIX-only toy terminal for tmux integration checks; not DCSS."""
import sys
import termios
import tty

old = termios.tcgetattr(sys.stdin)
try:
    tty.setcbreak(sys.stdin)
    for turn in range(5):
        print(f'\x1b[2J\x1b[HDEMO dungeon\r\n#####\r\n#.@.#\r\n#####\r\nHP: {5-turn}/5\r\n', end='', flush=True)
        sys.stdin.read(1)
    print('\r\nYou die.\r\n', end='', flush=True)
    sys.stdin.read(1)
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
