#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path

try:  # Windows terminals may default to a non-UTF-8 code page.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):  # pragma: no cover - very old Pythons
    pass

STRINGS = {
    "en": {
        "header": "NAMMA MITRA — Your matches",
        "reply": "reply: ",
        "optional_hint": "(optional, 0 to skip)",
        "empty_hint": "(press Enter to skip)",
        "back_hint": "b = go back, q = quit",
        "no_back": "You are at the first question — cannot go back.",
        "goodbye": "Thank you for using Namma Mitra. Goodbye!",
        "invalid_number": "Please enter a whole number, or press Enter to skip.",
        "invalid_pincode": "Please enter a 6-digit pincode, or press Enter to skip.",
        "invalid_choice": "Please reply with a number from 1 to {n}.",
        "no_skip": "This question is required — reply 1 to {n}.",
        "cannot_reach": (
            "Cannot reach the API at {url} — start it with:\n"
            "  cd backend && python manage.py runserver"
        ),
        "http_error": "The API returned an error ({status}) for {path}.",
        "bad_response": "The API reply for {path} was not the expected JSON.",
        "counts": "Eligible {y} | Fix needed {f} | Not eligible {n}",
        "footer_note": (
            "Screening only — confirm with the department. CSC help: "
            "reply with your pincode at your Grama One centre."
        ),
        "dry_run_note": "Dry run — embedded sample data, no network calls.",
        "answers_file_error": "Cannot read answers file {path}: {err}",
    },
    "kn": {
        "header": "ನಮ್ಮ ಮಿತ್ರ — ನಿಮ್ಮ ಅರ್ಹ ಯೋಜನೆಗಳು",
        "reply": "ಉತ್ತರ: ",
        "optional_hint": "(ಐಚ್ಛಿಕ, ಬಿಡಲು 0)",
        "empty_hint": "(ಬಿಡಲು ಎಂಟರ್ ಒತ್ತಿ)",
        "back_hint": "b = ಹಿಂದೆ, q = ನಿರ್ಗಮನ",
        "no_back": "ಇದು ಮೊದಲ ಪ್ರಶ್ನೆ — ಹಿಂದೆ ಹೋಗಲಾಗುವುದಿಲ್ಲ.",
        "goodbye": "ನಮ್ಮ ಮಿತ್ರ ಬಳಸಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು. ವಿದಾಯ!",
        "invalid_number": "ದಯವಿಟ್ಟು ಪೂರ್ಣಾಂಕ ನಮೂದಿಸಿ, ಅಥವಾ ಬಿಡಲು ಎಂಟರ್ ಒತ್ತಿ.",
        "invalid_pincode": "ದಯವಿಟ್ಟು 6 ಅಂಕೆಗಳ ಪಿನ್‌ಕೋಡ್ ನಮೂದಿಸಿ, ಅಥವಾ ಬಿಡಲು ಎಂಟರ್ ಒತ್ತಿ.",
        "invalid_choice": "ದಯವಿಟ್ಟು 1 ರಿಂದ {n} ರವರೆಗಿನ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ.",
        "no_skip": "ಈ ಪ್ರಶ್ನೆ ಕಡ್ಡಾಯ — 1 ರಿಂದ {n} ರವರೆಗೆ ನಮೂದಿಸಿ.",
        "cannot_reach": (
            "API ಗೆ ಸಂಪರ್ಕವಿಲ್ಲ ({url}) — ಇದನ್ನು ಚಲಾಯಿಸಿ:\n"
            "  cd backend && python manage.py runserver"
        ),
        "http_error": "API ದೋಷ ನೀಡಿದೆ ({status}) — {path}.",
        "bad_response": "API ಉತ್ತರ ನಿರೀಕ್ಷಿತ JSON ಅಲ್ಲ — {path}.",
        "counts": "ಅರ್ಹ {y} | ತಿದ್ದುಪಡಿ ಬೇಕು {f} | ಅರ್ಹವಲ್ಲ {n}",
        "footer_note": (
            "ಇದು ಪ್ರಾಥಮಿಕ ತಪಾಸಣೆ ಮಾತ್ರ — ಇಲಾಖೆಯಲ್ಲಿ ದೃಢೀಕರಿಸಿ. CSC ಸಹಾಯ: "
            "ನಿಮ್ಮ ಗ್ರಾಮ ಒನ್ ಕೇಂದ್ರದಲ್ಲಿ ಪಿನ್‌ಕೋಡ್ ತಿಳಿಸಿ."
        ),
        "dry_run_note": "ಡ್ರೈ-ರನ್ — ಒಳಗೊಂಡ ಮಾದರಿ ದತ್ತಾಂಶ, ನೆಟ್‌ವರ್ಕ್ ಇಲ್ಲ.",
        "answers_file_error": "ಉತ್ತರ ಫೈಲ್ ಓದಲಾಗಲಿಲ್ಲ {path}: {err}",
    },
}

STATUS_LETTER = {"eligible": "Y", "blocked": "F", "not_eligible": "N"}
LINE_WIDTH = 72
SUMM_WIDTH = 60


def loc(value, lang):
    """Return a plain string from either a localized string or {en, kn}.

    The API is documented to return already-localized strings when a locale
    is requested, but we accept the raw {en, kn} shape too so the CLI keeps
    working against either the frozen data files or the live service.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get(lang) or value.get("en") or ""
    return str(value)


def fill(text, params):
    """Substitute {placeholders} when the API left params unsatisfied."""
    if params and "{" in text:
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError):
            pass
    return text


def wrap(text, width=LINE_WIDTH, initial_indent="", subsequent_indent=""):
    """Word-safe wrap; never breaks mid-word."""
    out = []
    for paragraph in str(text).splitlines() or [""]:
        wrapped = textwrap.wrap(
            paragraph,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [initial_indent.rstrip()]
        out.extend(wrapped)
    return out


def clip(text, limit=SUMM_WIDTH):
    """Trim to ~limit chars on a word boundary, adding an ellipsis."""
    text = str(text).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def condition_passes(answer, cond):
    if answer is None:
        return False  
    if isinstance(cond, list):
        return answer in cond
    if isinstance(cond, dict):
        try:
            value = float(answer)
        except (TypeError, ValueError):
            return False
        low, high = cond.get("min"), cond.get("max")
        if low is not None and value < low:
            return False
        if high is not None and value > high:
            return False
        return True
    return answer == cond


def is_visible(question, answers):
    show_if = question.get("showIf")
    if not show_if:
        return True
    for qid, cond in show_if.items():
        if qid not in answers or not condition_passes(answers.get(qid), cond):
            return False
    return True


def prune_invalidated(questions, answers, keep_qid):
    visible = {q["id"] for q in questions if is_visible(q, answers)}
    for qid in [k for k in answers if k != keep_qid and k not in visible]:
        del answers[qid]


def set_answer(questions, answers, qid, value):
    """Commit an answer, then prune answers invalidated by the change."""
    answers[qid] = value
    prune_invalidated(questions, answers, qid)

SAMPLE_MATCH_RESPONSE = {
    "results": [
        {
            "scheme_id": "anna-bhagya",
            "code": "ABH",
            "name": {"en": "Anna Bhagya", "kn": "ಅನ್ನ ಭಾಗ್ಯ"},
            "summ": {
                "en": "10 kg rice per person per month for eligible families",
                "kn": "ಅರ್ಹ ಕುಟುಂಬಗಳಿಗೆ ತಲಾ ತಿಂಗಳಿಗೆ 10 ಕೆಜಿ ಅಕ್ಕಿ",
            },
            "status": "eligible",
            "confidence": "likely",
            "reasons": [],
            "fixes": [],
            "matched_facts": [],
            "docs": [],
        },
        {
            "scheme_id": "gruha-jyothi",
            "code": "GJT",
            "name": {"en": "Gruha Jyothi", "kn": "ಗೃಹ ಜ್ಯೋತಿ"},
            "summ": {
                "en": "Free electricity up to 200 units a month",
                "kn": "ತಿಂಗಳಿಗೆ 200 ಘಟಕಗಳವರೆಗೆ ಉಚಿತ ವಿದ್ಯುತ್",
            },
            "status": "eligible",
            "confidence": "likely",
            "reasons": [],
            "fixes": [],
            "matched_facts": [],
            "docs": [],
        },
        {
            "scheme_id": "gruha-lakshmi",
            "code": "GLK",
            "name": {"en": "Gruha Lakshmi", "kn": "ಗೃಹ ಲಕ್ಷ್ಮಿ"},
            "summ": {
                "en": "₹2,000 a month for the woman who heads your household",
                "kn": "ಕುಟುಂಬದ ಮಹಿಳಾ ಮುಖ್ಯಸ್ಥೆಗೆ ತಿಂಗಳಿಗೆ ₹2,000",
            },
            "status": "blocked",
            "confidence": "likely",
            "reasons": [
                {
                    "code": "reason.noAadhaarLinkedBank",
                    "message": {
                        "en": "A bank account linked to Aadhaar is required for payment.",
                        "kn": "ಪಾವತಿಗೆ ಆಧಾರ್ ಜೊತೆ ಸೇರಿಸಿದ ಬ್ಯಾಂಕ್ ಖಾತೆ ಬೇಕು.",
                    },
                }
            ],
            "fixes": [
                {
                    "fix_id": "bank-aadhaar-link",
                    "reason": {"code": "reason.noAadhaarLinkedBank"},
                    "title": {
                        "en": "Link your Aadhaar to your bank account",
                        "kn": "ನಿಮ್ಮ ಆಧಾರ್ ಅನ್ನು ಬ್ಯಾಂಕ್ ಖಾತೆಗೆ ಸೇರಿಸಿ",
                    },
                    "steps": [
                        {
                            "en": "Visit your bank branch with your Aadhaar card.",
                            "kn": "ನಿಮ್ಮ ಆಧಾರ್ ಕಾರ್ಡಿನೊಂದಿಗೆ ಬ್ಯಾಂಕ್ ಶಾಖೆಗೆ ಭೇಟಿ ನೀಡಿ.",
                        },
                        {
                            "en": "Ask for Aadhaar seeding on your account.",
                            "kn": "ನಿಮ್ಮ ಖಾತೆಗೆ ಆಧಾರ್ ಸೀಡಿಂಗ್ ಕೇಳಿ.",
                        },
                        {
                            "en": "Collect the confirmation slip and keep it.",
                            "kn": "ದೃಢೀಕರಣ ರಶೀದನ್ನು ಸಂಗ್ರಹಿಸಿ ಇಟ್ಟುಕೊಳ್ಳಿ.",
                        },
                    ],
                }
            ],
            "matched_facts": [],
            "docs": [],
        },
        {
            "scheme_id": "sandhya-suraksha",
            "code": "SSY",
            "name": {"en": "Sandhya Suraksha Yojane", "kn": "ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ ಯೋಜನೆ"},
            "summ": {
                "en": "₹1,200 a month pension for eligible elderly persons",
                "kn": "ಅರ್ಹ ವೃದ್ಧರಿಗೆ ಪ್ರತಿ ತಿಂಗಳು ₹1,200 ಪೆನ್ಷನ್",
            },
            "status": "not_eligible",
            "confidence": "likely",
            "reasons": [
                {
                    "code": "reason.ageUnder",
                    "params": {"min": "65"},
                    "message": {
                        "en": "You must be at least {min} years old for this scheme.",
                        "kn": "ಈ ಯೋಜನೆಗೆ ನಿಮಗೆ ಕನಿಷ್ಠ {min} ವರ್ಷ ವಯಸ್ಸು ಬೇಕು.",
                    },
                }
            ],
            "fixes": [],
            "matched_facts": [],
            "docs": [],
        },
        {
            "scheme_id": "swavalambi-kmdc",
            "code": "KMV",
            "name": {"en": "Swavalambi Sarathi — KMDC", "kn": "ಸ್ವಾವಲಂಬಿ ಸಾರಥಿ — ಕೆಎಂಡಿಸಿ"},
            "summ": {
                "en": "50% subsidy, up to ₹3 lakh, to buy a vehicle for self-employment",
                "kn": "ಸ್ವಯಂ ಉದ್ಯೋಗಕ್ಕಾಗಿ ವಾಹನ ಖರೀದಿಗೆ 50% ಸಬ್ಸಿಡಿ, ₹3 ಲಕ್ಷದವರೆಗೆ",
            },
            "status": "not_eligible",
            "confidence": "likely",
            "reasons": [
                {
                    "code": "reason.categoryNotCovered",
                    "message": {
                        "en": "This scheme is for a different social category of applicants.",
                        "kn": "ಈ ಯೋಜನೆಯು ಬೇರೆ ಸಾಮಾಜಿಕ ವರ್ಗದ ಅರ್ಜಿದಾರರಿಗೆ ಅನ್ವಯವಾಗುತ್ತದೆ.",
                    },
                }
            ],
            "fixes": [],
            "matched_facts": [],
            "docs": [],
        },
    ],
    "hidden_route_groups": ["vehicle"],
}

FALLBACK_QUESTIONS = [
    {"id": "age", "type": "number", "label": {"en": "How old are you?", "kn": "ನಿಮ್ಮ ವಯಸ್ಸು ಎಷ್ಟು?"}, "optional": False},
    {
        "id": "gender",
        "type": "single_select",
        "label": {"en": "What is your gender?", "kn": "ನಿಮ್ಮ ಲಿಂಗ ಯಾವುದು?"},
        "options": [
            {"value": "woman", "label": {"en": "Woman", "kn": "ಮಹಿಳೆ"}},
            {"value": "man", "label": {"en": "Man", "kn": "ಪುರುಷ"}},
        ],
        "optional": False,
    },
    {"id": "pincode", "type": "pincode", "label": {"en": "Your area's pincode?", "kn": "ನಿಮ್ಮ ಪ್ರದೇಶದ ಪಿನ್‌ಕೋಡ್?"}, "optional": True},
]

class ApiError(Exception):
    """Carries a user-facing message for any API/transport failure."""


def http_json(base, path, params=None, payload=None, timeout=30):
    url = base.rstrip("/") + path
    if params:
        from urllib.parse import urlencode

        url += "?" + urlencode(params)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise ApiError(f"__http__{exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ConnectionError(str(exc)) from exc
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(str(exc)) from exc


def fetch_questions(base, lang, timeout):
    try:
        data = http_json(base, "/questions", params={"locale": lang}, timeout=timeout)
    except ApiError as exc:
        raise
    questions = data if isinstance(data, list) else data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("no questions")
    return questions


def post_match(base, lang, answers, timeout):
    return http_json(base, "/match", payload={"locale": lang, "answers": answers}, timeout=timeout)


def api_failure_message(S, base, path, exc):
    if isinstance(exc, ApiError) and str(exc).startswith("__http__"):
        status = str(exc).removeprefix("__http__")
        return S["http_error"].format(status=status, path=path)
    return S["cannot_reach"].format(url=base.rstrip("/"))

def prompt_line(S, text):
    try:
        return input(text).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        print(S["goodbye"])
        raise SystemExit(0)


def ask_one(questions, index, asked, answers, S, lang):
    question = questions[index]
    asked.append(index)
    qid = question["id"]
    qtype = question.get("type", "single_select")
    options = question.get("options") or []
    optional = bool(question.get("optional"))

    shown = len(asked)
    remaining = sum(
        1
        for j in range(index + 1, len(questions))
        if is_visible(questions[j], answers)
    )
    print()
    print(f"Q{shown}/{shown + remaining} {loc(question.get('label'), lang)}")
    hints = []
    if optional:
        hints.append(S["optional_hint"])
    elif qtype in ("number", "pincode"):
        hints.append(S["empty_hint"])
    if asked[:-1]:
        hints.append(S["back_hint"])
    if hints:
        print("   " + "  ".join(hints))
    for i, option in enumerate(options, start=1):
        print(f"  {i}) {loc(option.get('label'), lang)}")

    while True:
        raw = prompt_line(S, S["reply"]).strip()
        low = raw.lower()
        if low == "q":
            print(S["goodbye"])
            raise SystemExit(0)
        if low == "b":
            if len(asked) < 2:
                print(S["no_back"])
                continue
            asked.pop()  # drop the current question from the shown stack
            previous = asked.pop()
            answers.pop(questions[previous]["id"], None)
            prune_invalidated(questions, answers, None)
            return previous
        if qtype == "number":
            if raw == "":
                set_answer(questions, answers, qid, None)
                return index + 1
            try:
                set_answer(questions, answers, qid, int(raw, 10))
                return index + 1
            except ValueError:
                print(S["invalid_number"])
                continue
        if qtype == "pincode":
            if raw == "" or (raw == "0" and optional):
                set_answer(questions, answers, qid, None)
                return index + 1
            if raw.isdigit() and len(raw) == 6:
                set_answer(questions, answers, qid, raw)
                return index + 1
            print(S["invalid_pincode"])
            continue
        # single_select
        if raw == "0" and optional:
            set_answer(questions, answers, qid, None)
            return index + 1
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            set_answer(questions, answers, qid, options[int(raw) - 1]["value"])
            return index + 1
        if raw == "0":
            print(S["no_skip"].format(n=len(options)))
        else:
            print(S["invalid_choice"].format(n=len(options)))


def run_questions(questions, S, lang):
    answers = {}
    asked = []
    index = 0
    while 0 <= index < len(questions):
        if not is_visible(questions[index], answers):
            index += 1
            continue
        index = ask_one(questions, index, asked, answers, S, lang)
    return answers

def result_lines(result, S, lang):
    code = result.get("code", "???")
    letter = status_letter(result.get("status"))
    name = loc(result.get("name"), lang)
    fixes = result.get("fixes") or []
    reasons = result.get("reasons") or []

    if result.get("status") == "blocked" and fixes:
        text = loc(fixes[0].get("title"), lang)
    elif reasons:
        first = reasons[0]
        text = fill(loc(first.get("message"), lang), first.get("params") or {})
    else:
        text = clip(loc(result.get("summ"), lang))

    lines = wrap(f"[{code}] {letter} {name}: {text}", subsequent_indent="      ")
    if result.get("status") == "blocked" and fixes:
        steps = [loc(s, lang) for s in (fixes[0].get("steps") or []) if loc(s, lang)]
        if steps:
            lines.extend(
                wrap(
                    f"-> step 1 of {len(steps)}: {steps[0]}",
                    initial_indent="      ",
                    subsequent_indent="         ",
                )
            )
    return lines


def status_letter(status):
    return STATUS_LETTER.get(status, STATUS_LETTER["not_eligible"])


def build_sms(response, S, lang, short=False):
    results = response.get("results") or []
    counts = {"eligible": 0, "blocked": 0, "not_eligible": 0}
    for result in results:
        status = result.get("status")
        key = status if status in counts else "not_eligible"
        counts[key] = counts.get(key, 0) + 1

    if short:
        badges = " ".join(
            f"[{r.get('code', '???')}]{status_letter(r.get('status'))}"
            for r in results
        )
        lines = wrap(badges)
    else:
        lines = [S["header"]]
        for result in results:
            lines.extend(result_lines(result, S, lang))

    lines.append(
        S["counts"].format(y=counts.get("eligible", 0), f=counts.get("blocked", 0), n=counts.get("not_eligible", 0))
    )
    lines.extend(wrap(S["footer_note"]))
    return "\n".join(lines)

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="namma_mitra",
        description="Namma Mitra SMS-flow demo CLI (stdlib only).",
    )
    parser.add_argument("--lang", choices=["en", "kn"], default="en", help="output language (default: en)")
    parser.add_argument("--api", default="http://localhost:8000", help="base URL of the Namma Mitra API")
    parser.add_argument("--json", action="store_true", help="print the raw /match response JSON and exit")
    parser.add_argument("--short", action="store_true", help="print only the codes line and the footer (SMS-length simulation)")
    parser.add_argument("--answers-file", metavar="PATH", help="JSON file with a answers dict; skips all prompts")
    parser.add_argument("--dry-run", action="store_true", help="run the full flow on embedded sample data, no network")
    parser.add_argument("--timeout", type=int, default=30, help="network timeout in seconds (default 30)")
    return parser.parse_args(argv)


def load_answers(path, S):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(S["answers_file_error"].format(path=path, err=exc), file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(data, dict):
        print(S["answers_file_error"].format(path=path, err="not a JSON object"), file=sys.stderr)
        raise SystemExit(1)
    return data


def main(argv=None):
    args = parse_args(argv)
    S = STRINGS[args.lang]

    if args.dry_run:
        print(f"({S['dry_run_note']})")
        data_dir = Path(__file__).resolve().parent.parent / "data"
        questions_file = data_dir / "questions.json"
        if questions_file.is_file():
            with open(questions_file, encoding="utf-8") as handle:
                questions = json.load(handle)
        else:
            questions = FALLBACK_QUESTIONS
        response = SAMPLE_MATCH_RESPONSE
    else:
        try:
            questions = fetch_questions(args.api, args.lang, args.timeout)
        except ConnectionError as exc:
            print(S["cannot_reach"].format(url=args.api.rstrip("/")), file=sys.stderr)
            raise SystemExit(1)
        except ApiError as exc:
            print(api_failure_message(S, args.api, "/questions", exc), file=sys.stderr)
            raise SystemExit(1)
        except (ValueError, OSError) as exc:
            print(f"{S['bad_response'].format(path='/questions')} ({exc})", file=sys.stderr)
            raise SystemExit(1)

    if args.answers_file:
        answers = load_answers(args.answers_file, S)
    else:
        answers = run_questions(questions, S, args.lang)

    if not args.dry_run:
        try:
            response = post_match(args.api, args.lang, answers, args.timeout)
        except ConnectionError:
            print(S["cannot_reach"].format(url=args.api.rstrip("/")), file=sys.stderr)
            raise SystemExit(1)
        except ApiError as exc:
            print(api_failure_message(S, args.api, "/match", exc), file=sys.stderr)
            raise SystemExit(1)
        except (ValueError, OSError) as exc:
            print(f"{S['bad_response'].format(path='/match')} ({exc})", file=sys.stderr)
            raise SystemExit(1)

    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0

    print()
    print(build_sms(response, S, args.lang, short=args.short))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
