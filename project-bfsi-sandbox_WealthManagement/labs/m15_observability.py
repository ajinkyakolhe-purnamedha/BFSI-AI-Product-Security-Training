from labs.registry import LABS
from labs.starter_page import render_starter_page

LAB = LABS[14]
def run(user: dict, request: str) -> None:
    raise NotImplementedError("M15 starter: trace a bounded advisor run and compare a measured improvement.")
def render(user: dict) -> None:
    render_starter_page(LAB, user, run)
