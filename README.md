# DCSS idle player — first prototype

## Private Underhound credentials

Requires Python 3.11+ for TOML configuration. Copy `login.example.toml` to `login.toml` in this project and fill in `username` and `password` locally. `login.toml`, `*.private.toml`, and `.env` files are ignored by Git. The file is plaintext; on Linux restrict access with `chmod 600 login.toml`. Use TOML single-quoted strings if your password contains backslashes or double quotes.

Launch with your already verified console SSH command:

```sh
python3 -m idle --remote --game 'ssh YOUR_VERIFIED_SSH_TARGET' --login-config login.toml
```

These are DCSS account credentials, not necessarily SSH credentials. SSH transport authentication must already work; this does not handle SSH password prompts, keys or host verification. Edit the example prompt patterns, login menu key, and `success_pattern` to match the actual console lobby. Underhound's current prompts remain unverified. The success pattern must uniquely indicate authenticated login, rather than appear on the login menu.

The harness performs the configured login steps before calling any model or recording screens. Credentials are redacted from subsequent captured screens and error messages; login inputs are not saved as actions. A repeated credential prompt stops the harness. The terminal itself may show an echoed username, and tmux's process arguments briefly contain sent characters. Do not share terminal history or the private config. Login errors stop without passing the login screen to a model. Remote game restarts still use the lobby through the agent.

Python 3.10+, no Python dependencies. The real terminal transport requires Linux (or WSL) and tmux. It captures the visible console screen, asks a backend for a small action, sends literal keystrokes, records lessons, and respawns the local game after a recognized death. This is a prototype player, not a strong DCSS policy.

## Start locally

In a Linux/WSL terminal, install Python, tmux and the console build of DCSS. On Debian/Ubuntu:

```sh
sudo apt update
sudo apt install python3 tmux crawl
cd /path/to/dcss-idle
python3 -m idle --backend demo --game 'python3 demo_game.py' --steps 30
```

On your second monitor, attach read-only:

```sh
tmux -L dcss-idle attach -r -t game
```

The demo repeatedly dies after five actions and restarts. It tests plumbing, not game intelligence. Stop the harness with Ctrl+C. Detach the watcher with Ctrl+B, D. The game remains running. Before starting another harness with the same session name, close the old private server (this stops its game):

```sh
tmux -L dcss-idle kill-server
```

## Play DCSS with Codex

Install and authenticate the Codex CLI in the same Linux/WSL environment first. Check `codex exec --help` and `codex login` there. Then:

```sh
python3 -m idle --game crawl --backend codex --steps 500 --delay 1
```

Codex chooses character/menu inputs as well as game actions. Each decision is a fresh `codex exec` invocation with a read-only sandbox, a timeout, and the last 20 persistent notes plus recent actions. The harness does not require access to this desktop chat. Invocation flags were checked against the installed CLI; actual authenticated model calls were not tested. See the [official CLI reference](https://developers.openai.com/codex/cli/reference).

## Backend contract

`idle/backends.py` defines `Agent.decide(observation) -> action`. Harness and terminal modules contain no provider SDK. For a different API/model, write a small program that reads one JSON object from stdin and writes one JSON object to stdout, then exits:

```sh
python3 -m idle --backend command --agent-command 'python3 my_backend.py' --game crawl
```

Input: `version`, `run`, `step`, `screen`, `notes`, `recent`. Output:

```json
{"keys":"o","note":"Explore only when healthy and no enemies are visible."}
```

`keys` is literal text, up to 16 characters; `\n` is Enter, `\t` is Tab, `\u001b` is Escape. Do not return tmux key names. Empty keys waits. Empty note saves no lesson. Only the backend knows credentials or providers. stdout must contain just JSON; use stderr for diagnostic logs. Invalid responses, timeouts and backend errors stop the harness without sending an action. An action is discarded if the screen changed during inference.

## Persistent state and controls

`state/events.jsonl` records observations, decisions, deaths, exits, and errors. `state/notes.jsonl` stores backend-provided lessons across process/game restarts. These are fallible textual knowledge, not trained model weights. The files grow over time; the prompt uses only recent notes. Create `state/PAUSE` to pause decisions, remove it to resume. A pause does not stop already submitted inference. Use `--memory another-folder` for a separate history. Runs receive unique IDs.

## Underhound later

Terminal ASCII console and browser WebTiles are different transports. This prototype handles terminal output only; it cannot render browser tiles in tmux. The main [underhound website](https://underhound.eu/) was reachable, but its current game endpoint, SSH parameters, and bot policy were not confirmed. No account was created and no server game was started.

Once console access and permission for automated play are established, manually verify the SSH login first. Pass that working command through `--game 'ssh ...' --remote`. Authenticate in the watcher before letting the harness play; do not put account passwords in command arguments or model prompts. Captured screens are sent to the selected model and saved in logs. In remote mode the harness records a recognized death once and keeps the connection; the model must dismiss scores and start another game through the lobby. It never kills/reconnects the SSH process on death, and stops on process exit. This remote workflow is not tested yet.

Local mode matches lines beginning `You die.` / `You have died.` and respawns the game immediately. Other exits stop the harness. Detection may need adjustment for specific DCSS versions, score screens, or terminal sizes. Snapshots settle for 150ms, up to 3 seconds; animation and network latency can still cause incomplete observations. Do not run two harnesses against the same socket. Screen text alone omits tiles, colors and cursor location.

## Validation and next increment

```sh
python3 -m unittest discover -s tests -v
```

Unit tests cover restart/death persistence, remote death deduplication, stale actions, action validation, and a real subprocess backend exchange. Live tmux/DCSS testing is still required: this Windows session had no tmux and WSL enumeration returned access denied. First validate the demo in Linux, then one short local Codex/DCSS run. Next improve prompt handling and death detection from observed screens, add a compact run summary, and verify Underhound console access. API backends and historical morgue ingestion can be added independently afterward.
