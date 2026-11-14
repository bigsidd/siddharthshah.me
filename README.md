# siddharthshah.me

Personal card. The home page is `public/index.html`, with the photo, icons and share image in `public/brand/`. No build step for the site itself.

Projects: edit `projects.json`, then run `python3 scripts/build-projects.py` to rewrite `public/projects/index.html`.

Run locally: `python3 -m http.server 8000 --directory public`

Deployed on Render as a static site from `render.yaml`, in the personal Render workspace.
