"""The problem config (docs/spec.md, "Problems"): the single source for the problem
list, the `unknown_problem` check, the `agreed` setup sent to the counter, and the
pages. Adding a Hackattic problem means adding an entry to PROBLEMS.

A problem is listed and accepted only once its model and thinking level are both set
("any" counts as set). Every string here is plain text: no markup, no control characters.
"""

from dataclasses import dataclass

# Names the wording of RULES: change it whenever the wording changes.
RULES_VERSION = "mvp-1"

# docs/spec.md, "Rules for students", word for word but without markdown.
RULES = (
    "One attempt = one fresh Pi session in a new, empty folder. Students may make as many"
    " attempts as they like; their best solved attempt counts.",
    "1. Setup: the problem's model and thinking level only (shown in the problem list). If a"
    " problem allows any model, pick one and keep it for the whole session. No rules files,"
    " skills or extra setup.",
    "2. Each attempt: new empty folder, new Pi session, solve from scratch. No code from"
    " earlier attempts.",
    "3. Prompts: plain English only, no code pasted in.",
    "4. Proof: the program must print both Hackattic's problem reply (the input) and its"
    " solve reply (right/wrong).",
    "5. Finish: stop as soon as Hackattic says correct. Everything in the session counts,"
    " including wrong answers and dead ends.",
    "6. Submit: /golf-submit in that session. Resubmitting the same session replaces the"
    " earlier copy.",
    "7. Spot checks: unusually low scores may be asked to redo the attempt live.",
)


@dataclass(frozen=True)
class Problem:
    slug: str  # Hackattic's, e.g. help_me_unpack
    title: str
    challenge_url: str  # exactly https://hackattic.com/challenges/<slug>
    instructions: tuple[str, ...]  # public constraints and required evidence, never hints
    # "provider/model" or "any"; None until set. Not listed or accepted until both are set.
    model: str | None = None
    # A Pi thinking level or "any"; None until set.
    thinking_level: str | None = None


PROBLEMS = (
    Problem(
        slug="help_me_unpack",
        title="Help me unpack",
        challenge_url="https://hackattic.com/challenges/help_me_unpack",
        instructions=(
            "Solve Hackattic's Help me unpack challenge with your own Hackattic account. The"
            " task and its JSON formats are on the challenge page.",
            "Your program must fetch the problem from hackattic.com, send its answer back"
            " there, and print both of Hackattic's replies: the problem (the input) and the"
            " solve reply.",
            'It counts as solved only when that printed solve reply says "result": "passed".',
        ),
        # "any" for now, so uploads aren't refused. Step 0 (plan 001) sets the real values.
        model="any",
        thinking_level="any",
    ),
)


def listed() -> tuple[Problem, ...]:
    """The problems whose model and thinking level are set: the only ones listed or accepted."""
    return tuple(
        problem
        for problem in PROBLEMS
        if problem.model is not None and problem.thinking_level is not None
    )


def get(slug: object) -> Problem | None:
    """The listed problem with this slug, or None (`unknown_problem`)."""
    return next((problem for problem in listed() if problem.slug == slug), None)
