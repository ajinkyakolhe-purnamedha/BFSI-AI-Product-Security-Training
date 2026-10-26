from labs.registry import LABS
from labs.starter_page import render_starter_page

LAB = LABS[13]
def run(user: dict, request: str) -> None:
    raise NotImplementedError("M14 starter: run a controlled attack and demonstrate the deterministic containment.")
def render(user: dict) -> None:
    render_starter_page(LAB, user, run)
