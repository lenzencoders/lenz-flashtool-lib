# Shell completions

## `_lenz-flashtool-cli` — zsh completion

Tab-completion for the `lenz-flashtool-cli` command: all predefined BiSS
commands (`run`, `zeroing`, `ampcalibrate`, `reboot2bl`, …) plus the
sub-commands (`reg`, `regb`, `hex`, `registers`, `dump`, `sendhexfile`, …) with
per-argument usage hints. `sendhexfile` completes `*.hex` files.

### Install

Pick **one** of the following.

**A. Add to your `$fpath` (recommended, autoloaded):**

```zsh
mkdir -p ~/.zsh/completions
ln -s /path/to/lenz-flashtool-lib/completions/_lenz-flashtool-cli ~/.zsh/completions/

# in ~/.zshrc, BEFORE compinit runs:
fpath=(~/.zsh/completions $fpath)
autoload -Uz compinit && compinit
```

**B. Source it directly from `~/.zshrc`:**

```zsh
autoload -Uz compinit && compinit          # must come first
source /path/to/lenz-flashtool-lib/completions/_lenz-flashtool-cli
```

The file self-registers via `compdef` when sourced, so both methods work.

After changing how it's loaded, refresh the cache once:

```zsh
rm -f ~/.zcompdump*
exec zsh
```

### Required: enable description/message display

zsh does **not** show completion descriptions or argument hints unless a
`format` style is configured. Without these styles you'll get the command
list, but the per-argument hints (e.g. `regb` → "BiSS bank number") will
silently do nothing. Add this to your `~/.zshrc`:

```zsh
# Show completion descriptions, messages, and group headers
zstyle ':completion:*' format '%B%d%b'
zstyle ':completion:*:descriptions' format '%U%B%d%b%u'
zstyle ':completion:*:messages' format '%F{yellow}%d%f'
zstyle ':completion:*' group-name ''
```

(Frameworks like oh-my-zsh / prezto usually set equivalents already.)

### Verify

```zsh
print -r -- $_comps[lenz-flashtool-cli]   # → _lenz-flashtool-cli
lenz-flashtool-cli <Tab>                  # → command list
lenz-flashtool-cli regb <Tab>             # → BiSS bank number
lenz-flashtool-cli regb 1 <Tab>           # → address (hex)
lenz-flashtool-cli sendhexfile <Tab>      # → *.hex files
```

### Maintenance

The command list mirrors `biss_commands` in
`lenz_flashtool/biss/commands.py` and the dispatcher in
`lenz_flashtool/biss/cli.py` (`execute_command`). When you add a command,
add a matching line to `_lenz-flashtool-cli`.
