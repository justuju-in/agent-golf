"""The rules page: GET /rules (plan 002 step 3.3)."""

import unittest
from dataclasses import replace
from unittest import mock

from server import problems
from server.tests.test_board import FIXED, HELP, SCORING, UNSET, PageTestCase

COMMANDS = [
    "pi install npm:agent-golf@preview",
    "mkdir -p ~/golf/attempt-1 && cd ~/golf/attempt-1",
    "export HACKATTIC_TOKEN=<your Hackattic token>",
    # The page's own origin (PageTestCase's api_base_url), as the plugin needs it.
    "AGENT_GOLF_API_BASE_URL=https://golf.example pi --no-extensions -e ~/.pi/agent/npm/node_modules/agent-golf"
    " --no-skills --no-context-files --no-mcp --no-prompt-templates",
    # The GitHub Copilot option: one more extension, nothing else changes.
    "pi install npm:pi-github-copilot-auto@0.3.0",
    "AGENT_GOLF_API_BASE_URL=https://golf.example pi --no-extensions -e ~/.pi/agent/npm/node_modules/agent-golf"
    " -e ~/.pi/agent/npm/node_modules/pi-github-copilot-auto"
    " --no-skills --no-context-files --no-mcp --no-prompt-templates",
]
IN_PI = (
    "In Pi: /golf-login <your key> (once), pick your model with /model before your first prompt,"
    " solve, then /golf-submit <problem>."
)


class RulesPageTest(PageTestCase):
    def test_rules_text(self):
        page = self.page("/rules")
        self.assertEqual(page.find("title").text(), "Rules – Agent Golf")
        self.assertEqual(page.find("h1").text(), "Rules")
        # The problem config's rules, which mirror docs/spec.md (test_problems checks that).
        rules = [paragraph.text() for paragraph in page.find("div", class_="rules").find_all("p")]
        self.assertEqual(rules, list(problems.RULES))

    def test_the_problems_and_setups_of_the_problem_list(self):
        with mock.patch.object(problems, "PROBLEMS", (HELP, UNSET, FIXED)):
            listed = self.client.get("/api/v1/problems").json()["problems"]
            page = self.page("/rules")
        sections = page.find_all("section", class_="problem")
        self.assertEqual([section.find("h3").text() for section in sections], [problem["title"] for problem in listed])
        self.assertEqual(
            [section.find("p", class_="setup").text() for section in sections],
            ["Setup: any model, one per session; any thinking level", "Setup: openai/gpt-5.5; thinking level low"],
        )
        for section, problem in zip(sections, listed, strict=True):
            with self.subTest(problem=problem["slug"]):
                hackattic = section.find("a", href=problem["challenge_url"])
                self.assertEqual(hackattic.text(), f"{problem['title']} on Hackattic")
                instructions = [item.text() for item in section.find("ul", class_="instructions").find_all("li")]
                self.assertEqual(instructions, problem["instructions"])
                self.assertIn(f"Submit with /golf-submit {problem['slug']}.", section.text())
                self.assertEqual(
                    section.find("a", href=f"/problems/{problem['slug']}").text(), f"{problem['title']} board"
                )
                # Labelled by its own heading.
                self.assertEqual(section.find(id=section.attrs["aria-labelledby"]).tag, "h3")
        # Not listed yet, so not shown.
        self.assertNotIn("Not set yet", page.find("main").text())

    def test_scoring_install_login_and_submit(self):
        page = self.page("/rules")
        self.assertEqual(page.find("p", class_="scoring").text(), SCORING)
        self.assertEqual(page.find(id="install").text(), "Install the plugin")
        self.assertEqual(page.find_all("p", class_="placeholder"), [])
        self.assertEqual([command.text() for command in page.find_all("p", class_="command")], COMMANDS)
        main = page.find("main").text()
        self.assertIn("Install (once): pi install npm:agent-golf@preview Then restart Pi or run /reload.", main)
        self.assertEqual(page.find(id="start").text(), "Start an attempt")
        self.assertIn("Start each attempt in a new, empty folder:", main)
        self.assertEqual(page.find("p", class_="in-pi").text(), IN_PI)
        steps = page.find("ol", class_="how")
        self.assertEqual(
            [item.text() for item in steps.find_all("li")],
            [
                "Register to get your secret key. It is shown once, so save it.",
                "In Pi, run /golf-login <key> with that key.",
                "Solve the problem in a new Pi session, started in a new, empty folder.",
                "In that session, run /golf-submit <problem>, for example /golf-submit help_me_unpack."
                " Its reply links to your submission's page.",
            ],
        )
        self.assertEqual([a.attrs["href"] for a in steps.find_all("a")], ["/register"])

    def test_no_problems_listed(self):
        with mock.patch.object(problems, "PROBLEMS", (UNSET,)):
            page = self.page("/rules")
        self.assertEqual(len(page.find("div", class_="rules").find_all("p")), len(problems.RULES))
        self.assertEqual(page.find_all("section", class_="problem"), [])
        self.assertIn("No problems are open yet.", page.find("main").text())
        self.assertEqual(
            page.find("ol", class_="how").find_all("li")[-1].text(),
            "In that session, run /golf-submit <problem>. Its reply links to your submission's page.",
        )

    def test_text_is_escaped(self):
        # Plain text that problems.check() allows, shown as text.
        with mock.patch.object(problems, "PROBLEMS", (replace(FIXED, title='a < b, "quoted" & café'),)):
            response = self.client.get("/rules")
        self.assertIn("a &lt; b, &#34;quoted&#34; &amp; café", response.text)
        self.assertNotIn('a < b, "quoted"', response.text)


if __name__ == "__main__":
    unittest.main()
