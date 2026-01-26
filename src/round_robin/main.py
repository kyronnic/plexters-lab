from __future__ import annotations

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from round_robin.interleave import interleave_episode_lists
from round_robin.plex_ops import (
    get_tv_sections,
    search_shows,
    fetch_show_episodes,
    format_episode_line
)
from round_robin.playlist_ops import create_video_playlist

app = FastAPI()
templates = Jinja2Templates(directory="src/round_robin/templates")

STATE = {
    "selected": [],
    "tv_section_key": None
}

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    sections = get_tv_sections()
    if not sections:
        return HTMLResponse("<div class='error'>No TV sections found</div>", status_code=500)

    if STATE["tv_section_key"] is None:
        STATE["tv_section_key"] = sections[0].key

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "selected": STATE["selected"], "sections": sections, "active_session": STATE["tv_section_key"]}
    )

@app.post("/set_section", response_class=HTMLResponse)
def set_section(request: Request, section_key: str = Form(...)):
    STATE["tv_section_key"] = section_key
    return HTMLResponse("<small>Library set.</small>")


@app.post("/search", response_class=HTMLResponse)
def search(request: Request, q: str = Form("")):
    q = (q or "").strip()
    if not q:
        return templates.TemplateResponse("_results.html", {"request": request, "results": [], "selected_keys": set()})

    section_key = STATE["tv_section_key"]
    results = search_shows(section_key, q, limit=30)

    selected_keys = {s["key"] for s in STATE["selected"]}

    return templates.TemplateResponse(
        "_results.html",
        {"request": request, "results": results, "selected_keys": selected_keys},
    )


@app.post("/select", response_class=HTMLResponse)
def select_show(request: Request, key: str = Form(...), title: str = Form(...)):
    if key not in {s["key"] for s in STATE["selected"]}:
        STATE["selected"].append({"title": title, "key": key})
    return templates.TemplateResponse("_selected.html", {"request": request, "selected": STATE["selected"]})


@app.post("/remove", response_class=HTMLResponse)
def remove_show(request: Request, key: str = Form(...)):
    STATE["selected"] = [s for s in STATE["selected"] if s["key"] != key]
    return templates.TemplateResponse("_selected.html", {"request": request, "selected": STATE["selected"]})


@app.post("/preview", response_class=HTMLResponse)
def preview(request: Request):
    if not STATE["selected"]:
        return templates.TemplateResponse("_preview.html", {"request": request, "total": 0, "lines": [], "error": "Select at least one show."})

    episode_lists = []
    for s in STATE["selected"]:
        eps = fetch_show_episodes(s["key"])
        episode_lists.append(eps)

    ordered = interleave_episode_lists(episode_lists)
    lines = [format_episode_line(ep) for ep in ordered[:50]]

    return templates.TemplateResponse("_preview.html", {"request": request, "total": len(ordered), "lines": lines, "error": None})


@app.post("/create", response_class=HTMLResponse)
def create(request: Request, playlist_name: str = Form(...)):
    if not STATE["selected"]:
        return HTMLResponse("<div class='error'>Select at least one show.</div>", status_code=400)

    episode_lists = []
    for s in STATE["selected"]:
        eps = fetch_show_episodes(s["key"])
        episode_lists.append(eps)

    ordered = interleave_episode_lists(episode_lists)
    if not ordered:
        return HTMLResponse("<div class='error'>No episodes found.</div>", status_code=400)

    create_video_playlist(playlist_name.strip(), [ep.rating_key for ep in ordered])

    return HTMLResponse(f"<div class='success'>Created <b>{playlist_name}</b> with {len(ordered)} episodes.</div>")