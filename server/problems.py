"""The problem config (docs/spec.md, "Problems"): the single source for the problem
list, the `unknown_problem` check, the `agreed` setup sent to the counter, and the
pages. Adding a Hackattic problem means adding an entry to PROBLEMS.

A problem is listed and accepted only once its model and thinking level are both set
("any" counts as set). Every string here is plain text: no markup, no control characters.
check() keeps docs/spec.md's limits for the problem list; the app runs it at startup.
"""

import json
import re
import unicodedata
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
        model="any",
        thinking_level="any",
    ),
    Problem(
        slug="brute_force_zip",
        title="Brute force ZIP",
        challenge_url="https://hackattic.com/challenges/brute_force_zip",
        instructions=(
            "Solve Hackattic's Brute force ZIP challenge with your own Hackattic account. The"
            " task and its JSON formats are on the challenge page.",
            "Your program must fetch the problem from hackattic.com, send its answer back"
            " there, and print both of Hackattic's replies: the problem (the input) and the"
            " solve reply.",
            'It counts as solved only when that printed solve reply says "result": "passed".',
        ),
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


def problem_list() -> dict:
    """The body of GET /api/v1/problems (docs/spec.md, "Contract: problem list")."""
    return {
        "rules_version": RULES_VERSION,
        "rules": list(RULES),
        "problems": [
            {
                "slug": problem.slug,
                "title": problem.title,
                "challenge_url": problem.challenge_url,
                "instructions": list(problem.instructions),
                "model": problem.model,
                "thinking_level": problem.thinking_level,
            }
            for problem in listed()
        ],
    }


def problem_list_json() -> bytes:
    """problem_list() as served: compact UTF-8 JSON, the bytes the 64 KB limit is about."""
    return json.dumps(problem_list(), ensure_ascii=False, separators=(",", ":")).encode()


# docs/spec.md, "Contract: problem list": limits the plugin checks too.
MAX_LIST_BYTES = 64 * 1024
MAX_STRING_CHARS = 1000
# The shapes the plugin accepts.
SLUG = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")
MODEL = re.compile(r"[^\s/]+/\S+")  # provider/model
THINKING_LEVEL = re.compile(r"[a-z][a-z0-9_-]*")
MARKUP = re.compile(r"<[A-Za-z/!?]")  # the start of an HTML tag, comment or declaration
# Bidirectional overrides and isolates: text that displays as something else.
BIDI_CONTROLS = frozenset("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


class InvalidConfig(ValueError):
    """The problem config breaks a limit of docs/spec.md, "Contract: problem list"."""


def _check_text(where: str, text: object) -> None:
    """Raise InvalidConfig unless `text` is non-blank plain text of at most 1,000 characters."""
    if not isinstance(text, str) or not text.strip():
        raise InvalidConfig(f"{where}: not text, or blank")
    if len(text) > MAX_STRING_CHARS:
        raise InvalidConfig(f"{where}: over {MAX_STRING_CHARS} characters")
    # C0 and C1 controls (terminal escapes among them), unpaired surrogates, bidi controls.
    if any(unicodedata.category(char) in ("Cc", "Cs") or char in BIDI_CONTROLS for char in text):
        raise InvalidConfig(f"{where}: a control character")
    if MARKUP.search(text):
        raise InvalidConfig(f"{where}: markup")


def check() -> None:
    """Raise InvalidConfig unless the config keeps docs/spec.md's limits for the problem
    list: plain text, at most 1,000 characters per string and 64 KB in all, each
    challenge_url exactly https://hackattic.com/challenges/<slug>, and slugs and setups
    in the shapes the plugin accepts. Problems not listed yet are checked too."""
    _check_text("RULES_VERSION", RULES_VERSION)
    if not isinstance(RULES, (tuple, list)):
        raise InvalidConfig("RULES: not a list of strings")
    for n, rule in enumerate(RULES):
        _check_text(f"RULES[{n}]", rule)
    slugs = [problem.slug for problem in PROBLEMS]
    for problem in PROBLEMS:
        where = f"problem {problem.slug!r}"
        _check_text(f"{where} slug", problem.slug)
        if not SLUG.fullmatch(problem.slug):
            raise InvalidConfig(f"{where}: slug is not lowercase words joined by single underscores")
        if slugs.count(problem.slug) > 1:
            raise InvalidConfig(f"{where}: in the config twice")
        _check_text(f"{where} title", problem.title)
        if problem.challenge_url != f"https://hackattic.com/challenges/{problem.slug}":
            raise InvalidConfig(f"{where}: challenge_url is not https://hackattic.com/challenges/<slug>")
        _check_text(f"{where} challenge_url", problem.challenge_url)
        if not isinstance(problem.instructions, (tuple, list)):
            raise InvalidConfig(f"{where}: instructions are not a list of strings")
        for n, line in enumerate(problem.instructions):
            _check_text(f"{where} instructions[{n}]", line)
        if problem.model is not None:
            _check_text(f"{where} model", problem.model)
            if problem.model != "any" and not MODEL.fullmatch(problem.model):
                raise InvalidConfig(f'{where}: model is neither "any" nor provider/model')
        if problem.thinking_level is not None:
            _check_text(f"{where} thinking_level", problem.thinking_level)
            if not THINKING_LEVEL.fullmatch(problem.thinking_level):
                raise InvalidConfig(f"{where}: thinking_level is not a lowercase level name")
    size = len(problem_list_json())
    if size > MAX_LIST_BYTES:
        raise InvalidConfig(f"the problem list is {size} bytes, over {MAX_LIST_BYTES}")
