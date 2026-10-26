from labs.registry import LABS
from labs.starter_page import render_starter_page

LAB = LABS[10]
def run(user: dict, request: str) -> None:
    raise NotImplementedError("M11 starter: implement a scoped typed data tool with a row limit.")
def render(user: dict) -> None:
    render_starter_page(LAB, user, run)
