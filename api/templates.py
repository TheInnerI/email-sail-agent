"""
Email Sail Agent — Template rendering utility.

Separated from main.py to avoid circular imports.
"""

from fastapi import Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Create Jinja2 environment once
_jinja_env = None


def get_jinja_env():
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader("api/templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
    return _jinja_env


def respond(request: Request, template_name: str, context: dict = None) -> HTMLResponse:
    """Render a Jinja2 template and return HTMLResponse."""
    ctx = {"request": request}
    if context:
        ctx.update(context)
    env = get_jinja_env()
    tmpl = env.get_template(template_name)
    content = tmpl.render(**ctx)
    return HTMLResponse(content=content)
