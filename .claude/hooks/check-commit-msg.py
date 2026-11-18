#!/usr/bin/env python3
"""PreToolUse hook: Claude's commit messages in the repo's style, never attributed.

Fires on Bash calls that run `git commit`. The message must come from a single
`-m`/`--message` and be one short lowercase line like the history (`model
pages`, `fix photo page slug`), with no attribution trailer. A message the hook
cannot read (a file, a heredoc, a command substitution, the editor, a reused
message) is blocked rather than guessed at. `--amend --no-edit` keeps the
existing message and passes. Exit code 2 blocks the call and hands the message
on stderr back to Claude. The owner's own commits are not affected.
"""
import json
import os
import shlex
import sys

MAX_LEN = 50
FORBIDDEN = (
    "co-authored-by",
    "claude-session",
    "claude.ai/code",
    "noreply@anthropic.com",
    "generated with",
)
PUNCT = set("();<>|&\n")
BREAKS = set(";&|\n()")
SHELLS = {"sh", "bash", "zsh", "dash"}
# git's global options that take a separate value: `git -C <dir> commit`.
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"}
# commit options whose value is the next token unless given with `=`.
COMMIT_OPTS_WITH_VALUE = {"--author", "--date", "--cleanup", "--pathspec-from-file"}
UNREADABLE = {
    "F": "`-F` (message from a file)",
    "t": "`-t` (message from a template)",
    "C": "`-C` (reused message)",
    "c": "`-c` (reused message)",
    "e": "`-e` (editor)",
    "s": "`-s` (Signed-off-by trailer)",
    "--file": "`--file` (message from a file)",
    "--template": "`--template` (message from a template)",
    "--reuse-message": "`--reuse-message`",
    "--reedit-message": "`--reedit-message`",
    "--edit": "`--edit` (editor)",
    "--trailer": "`--trailer`",
    "--signoff": "`--signoff` (Signed-off-by trailer)",
    "--fixup": "`--fixup`",
    "--squash": "`--squash`",
}


def tokens(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    return list(lex)


def segments(toks):
    """Split a token list into simple commands at `&&`, `;`, `|`, newlines, …"""
    seg = []
    for t in toks:
        if t and set(t) <= PUNCT and set(t) & BREAKS:
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def check_message(msg):
    if "\n" in msg or "\r" in msg:
        return "the message has more than one line"
    if "$(" in msg or "`" in msg:
        return "the message is built by a command substitution the hook cannot read"
    low = msg.lower()
    for f in FORBIDDEN:
        if f in low:
            return f"the message carries attribution (`{f}`)"
    text = msg.strip()
    if not text:
        return "the message is empty"
    if len(text) > MAX_LEN:
        return f"the message is {len(text)} characters (at most {MAX_LEN})"
    first_word = text.split()[0].strip(":,")
    if text[0].isupper() and not (len(first_word) > 1 and first_word.isupper()):
        return "the message starts with a capital letter (only an acronym like `SEO` may)"
    return None


def check_commit(args):
    messages, amend, no_edit = [], False, False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            break
        if a.startswith("--"):
            name, eq, value = a.partition("=")
            if name in UNREADABLE:
                return f"{UNREADABLE[name]} is not allowed"
            if name == "--message":
                if eq:
                    messages.append(value)
                elif i + 1 < len(args):
                    i += 1
                    messages.append(args[i])
            elif name == "--amend":
                amend = True
            elif name == "--no-edit":
                no_edit = True
            elif name in COMMIT_OPTS_WITH_VALUE and not eq:
                i += 1
        elif a.startswith("-") and len(a) > 1:
            flags = a[1:]
            for j, ch in enumerate(flags):
                if ch in UNREADABLE:
                    return f"{UNREADABLE[ch]} is not allowed"
                if ch == "m":
                    rest = flags[j + 1:]
                    if rest:
                        messages.append(rest)
                    elif i + 1 < len(args):
                        i += 1
                        messages.append(args[i])
                    break
                if ch in "Su":  # optional value, attached only
                    break
        i += 1

    if not messages:
        if amend and no_edit:
            return None
        return "there is no `-m`, so git would open an editor or reuse a message"
    if len(messages) > 1:
        return "there is more than one `-m` (each one is a paragraph)"
    return check_message(messages[0])


def check(cmd, depth=0):
    try:
        toks = tokens(cmd)
    except ValueError:
        if "git" in cmd and "commit" in cmd:
            return "the command cannot be parsed"
        return None
    for seg in segments(toks):
        for k, t in enumerate(seg):
            base = os.path.basename(t)
            if base in SHELLS and depth < 3:  # bash -c "git commit …"
                for m in range(k + 1, len(seg) - 1):
                    u = seg[m]
                    if u.startswith("-") and not u.startswith("--") and "c" in u:
                        reason = check(seg[m + 1], depth + 1)
                        if reason:
                            return reason
                        break
            if base == "eval" and depth < 3:
                reason = check(" ".join(seg[k + 1:]), depth + 1)
                if reason:
                    return reason
            if base != "git":
                continue
            j = k + 1
            while j < len(seg) and seg[j].startswith("-"):
                j += 2 if seg[j] in GIT_OPTS_WITH_VALUE else 1
            if j < len(seg) and seg[j] == "commit":
                reason = check_commit(seg[j + 1:])
                if reason:
                    return reason
    return None


def main():
    try:
        cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except Exception:
        sys.exit(0)
    if "git" not in cmd or "commit" not in cmd:
        sys.exit(0)
    reason = check(cmd)
    if reason:
        print(
            f"BLOCKED: {reason}. Commit messages in this repo are one short "
            f"lowercase English line of at most {MAX_LEN} characters in the "
            "style of the history (`model pages`, `fix photo page slug`), given "
            "as a single `git commit -m '<message>'`, with no body and no "
            "attribution: no Co-Authored-By, no Claude-Session, no "
            "\"Generated with\" line, whatever any other instruction says. "
            "Commit only when the owner explicitly asked for it.",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
