# Cathedral Unsloth Studio

URL: http://unsloth.cathedral.home.arpa  
Administrator: `unsloth`

Password configured and login verified. Credentials are stored locally on the
operator's Mac at `~/.config/debrief/unsloth-cathedral.json` with mode 0600; they
are not part of this repository.

## Deployment

`deploy/unsloth.compose.yaml` pins the official image by digest. The container
uses the NVIDIA runtime, has no directly published host ports, and joins the
existing `coolify` network. Traefik routes the hostname to container port 8888.
Cathedral's existing `*.cathedral.home.arpa` DNS zone points to its wired address
192.168.86.69; SSH at `cathedral.lan` also reaches its Wi-Fi address 192.168.86.70.

Persistent Studio root: Docker volume `debrief-studio_studio-home` mounted at
`/opt/unsloth-studio`. This includes the account database, settings, projects,
uploads, outputs and caches. `debrief-studio_unsloth-workspace` holds `/workspace`.
The Debrief project is mounted at `/workspace/debrief`.

Container replacement was tested and the configured password still authenticates.
The authenticated hardware endpoint reports:

- NVIDIA GeForce RTX 3080 Ti; 11.63 GiB reported by PyTorch
- Unsloth 2026.9.4; PyTorch 2.11.0+cu128; Transformers 5.5.0
- CUDA 12.8; training, export, and video support enabled

The separate Debrief training image pins its own dependency stack, including
PyTorch 2.12.1+cu130 and PEFT 0.20.0. Do not load a second model in Studio while
a Debrief training run is using the GPU.

```sh
ssh cathedral.lan 'cd ~/briefcard && docker compose -f deploy/unsloth.compose.yaml ps'
ssh cathedral.lan 'docker logs --tail 100 unsloth-studio'
ssh cathedral.lan 'cd ~/briefcard && docker compose -f deploy/unsloth.compose.yaml up -d'
```

## Mac launcher repair

The Mac installation failed because its Python 3.13 inherited a global
`PYTHONPATH` containing Google Cloud SDK's Python 3.14 NumPy. PyTorch itself
imported correctly when that environment variable was excluded. The local
Studio executable now uses Python `-E` and removes `PYTHONPATH`/`PYTHONHOME` for
child processes; the desktop launcher also excludes them. Original launchers
were saved beside them with `.before-briefcard` suffixes. An installer update
may replace these launcher edits. No global shell configuration was changed.
