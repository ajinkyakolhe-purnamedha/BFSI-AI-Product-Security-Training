from labs.registry import LABS
from labs.starter_page import render_starter_page

LAB = LABS[12]
def run(user: dict, request: str) -> None:
    raise NotImplementedError("M13 starter: execute deterministic checks and score a golden agent trajectory.")
def render(user: dict) -> None:
    render_starter_page(LAB, user, run)
