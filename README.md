# siddharthshah.me

Personal card. The home page is `public/index.html`, with the photo, icons and share image in `public/brand/`. No build step for the site itself.

Projects: edit `projects.json`, then run `python3 scripts/build-projects.py` to rewrite `public/projects/index.html`.

/os: run `python3 scripts/build-os.py path/to/os` (default `../os`) to rewrite `public/os/index.html` from the os repo's rules, test cases and `tests/results.json`. Edit `scripts/os.template.html`, not the page.

Run locally: `python3 -m http.server 8000 --directory public`

Deployed on Render as a static site from `render.yaml`, in the personal Render workspace.
