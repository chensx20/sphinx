# Quickstart existing-project cancellation: research and fix specification

## Scope and workflow

- Repository: chensx20/sphinx; checkout: /workspace/sphinx.
- Base branch: cam-base/sphinx-doc__sphinx-9320-AGYN-R4-20261110T125705Z-480f94.
- Exact base commit: e05cef574b8f23ab1b57f57e7da6dee509a4e230 (Sphinx 4.1.0).
- Sources: supplied report and this repository only. No previous benchmark patches,
  upstream solutions, issue bodies, or external documentation were researched.
- Active-work check: open PR titles/head/base metadata on the fork only; none
  targeted this quickstart bug. No unrelated PR contents were read.
- Research phase: source tracing, existing test execution, unchanged CLI reproduction.
- Engineer phase: implementation-ready specification and regression design below.
  No implementation or test code was authored, as explicitly requested.
- Reviewer phase: same-agent specification review and diff verification, not an
  independent human or subagent review. Actual implementation review is pending.
- Deliverable: documentation-only draft PR on the fork, left open. This is not a
  bug-fix PR and must not claim the implementation/tests have been completed.

## Diagnosis

The collision prompt advertises Enter as cancellation, but its validator rejects
an empty string before control can reach the existing cancellation branch.

Relevant locations at the exact base:

| Path and lines | Role |
| --- | --- |
| sphinx/cmd/quickstart.py:91-95 | is_path expands the user's home marker and rejects anything that is not an existing directory, including the empty string. |
| sphinx/cmd/quickstart.py:132-157 | do_prompt strips input, substitutes only truthy defaults, validates, and retries on ValidationError. An empty default does not bypass validation. |
| sphinx/cmd/quickstart.py:210-228 | ask_user checks root/conf.py and root/source/conf.py, asks for a replacement with empty default and is_path, then explicitly exits with status 1 for an empty returned path. |
| sphinx/cmd/quickstart.py:538-604 | main invokes ask_user before generate; it catches EOFError/KeyboardInterrupt as status 130, but does not catch the cancellation SystemExit. The module entrypoint exits with main's result. |
| tests/test_quickstart.py:27-41 | mock_input rejects a second identical prompt, so it cannot model invalid-then-valid retries. |
| tests/test_quickstart.py:52-92 | Existing prompt/default/whitespace tests, but no empty path cancellation coverage. |
| tests/test_quickstart.py:95-252 | Existing generation/build tests; no existing-conf collision regression. |
| setup.py:17-57; tox.ini:1-30 | Dependencies/test extras and the Python 3.6-3.9 / Docutils 0.14-0.17 test matrix. |

Execution trace: Enter becomes an empty string after stripping; the default is
also empty, so no substitution occurs; expanduser preserves the empty string;
isdir rejects it; ValidationError is caught inside do_prompt and the question
is repeated. Consequently the existing sys.exit(1) branch is unreachable for
Enter. A piped single newline then reaches EOF on the second prompt, producing
'[Interrupted.]' and process status 130. This is not a filesystem overwrite bug.

## Observed baseline

- Exact base branch SHA and HEAD were verified equal before research edits.
- Existing tests: 9 passed in tests/test_quickstart.py, Python 3.7.16,
  pytest 7.4.4, Jinja2 3.0.3, Docutils 0.17.1.
- Root conf.py + one newline: invalid-path warning, repeated prompt, then
  interruption/status 130 because the pipe ends.
- source/conf.py + one newline: same failure.
- Whitespace-only answer: same failure, confirming do_prompt stripping.
- Missing directory and regular file: each rejected with invalid-path warning.
- Another existing project: directory accepted by validator, collision warning
  repeated by ask_user as intended.
- Existing empty replacement directory: project generation succeeds, status 0.
- Existing replacement directory entered using '~': expands and generates,
  status 0, with HOME redirected to the workspace fixture directory.
- Cancellation left the original zero-byte conf.py fixtures unchanged; generation
  occurred only in explicitly selected valid replacement fixture directories.
- No patched behavior or newly implemented regression tests have been executed.

## Engineer handoff: selected minimal fix

1. Change only is_path in sphinx/cmd/quickstart.py: accept the exact empty string
   unchanged before filesystem validation. For every nonempty input preserve the
   existing home expansion, isdir check, ValidationError text, and return value.
2. Keep do_prompt, the collision prompt's validator/default, and the existing
   ask_user empty-path exit branch unchanged.
3. Preserve SystemExit code 1 for user cancellation. Here 'clean exit' means
   immediate intentional termination without warning, retry, traceback,
   interruption message, subsequent questions, or generated files; it does not
   mean changing cancellation into success/status 0.
4. Keep existing-directory requirements for nonempty interactive replacement
   paths. Accepting nonexistent replacement directories is a separate behavior
   change, not part of this bug. Quiet-mode behavior and valid_dir stay unchanged.
5. Add regression tests to tests/test_quickstart.py; no new dependencies or
   generic validation abstraction are needed. A release note, if required by
   maintainers, should describe Enter cancellation without promising status 0.

Caller review: the production is_path call sites are the initial root question
(default '.') and the collision replacement question (default ''). Initial
blank/whitespace input still selects '.', and that directory remains validated.
Raw whitespace is not a valid is_path directory: stripping belongs to do_prompt.

Do not replace is_path with allow_empty or ok at the collision prompt: both
accept invalid nonempty filenames and nonexistent paths, removing established
validation. Do not make all empty defaults bypass validators in do_prompt,
catch SystemExit in main, change status codes, or add fallback recovery.

## Required regression tests

Use tempdir/tmp_path, monkeypatch, and capsys consistent with repository pytest
conventions. Restore qs.term_input using monkeypatch rather than persistent
module-global assignments. For multi-response tests use a finite ordered input
sequence with a prompt recorder; fail on unexpected questions or extra reads.
Do not reuse mock_input for repeated identical questions and do not use sleeps.

| Proposed test | Setup and assertions |
| --- | --- |
| test_is_path_empty | Empty string returns exactly empty string, not '.', None, or a boolean. This must fail on the base. |
| test_is_path_existing_directory | Absolute and relative existing directories return the existing spelling after expanduser; no creation or resolution changes. |
| test_is_path_invalid_nonempty | Missing path and regular file each raise qs.ValidationError with the existing message; verify missing path remains absent. |
| test_is_path_expands_home | Set HOME and USERPROFILE to the fixture home, supply an existing '~/docs', and assert the expanded path. Missing '~/missing' still raises. |
| test_do_prompt_empty_path | Default '', validator is_path, response '' or whitespace returns '' after exactly one read and emits no validation warning. |
| test_do_prompt_initial_path_default | Default '.', validator is_path, cwd existing fixture: empty/whitespace still returns '.' rather than cancelling. |
| test_do_prompt_path_retry | Missing directory, regular file, valid existing directory: exactly three reads, exactly two validation warnings, final valid path returned; no directories are created. |
| test_do_prompt_invalid_path_then_cancel | Missing path then empty response: one validation warning, two reads, empty result, no extra read. |
| test_quickstart_existing_conf_cancel | Parametrize conf.py versus source/conf.py, supplied path versus main([]) with changed cwd, and '' versus whitespace. Call main; assert SystemExit.value.code == 1, one replacement question, no invalid-path message, no '[Interrupted.]', no later questions, no traceback. Snapshot all fixture paths and existing configuration bytes; assert unchanged and no generated files/directories. This must fail on the base. |
| test_quickstart_collision_after_reselection | Supply another directory containing conf.py or source/conf.py, then Enter. Assert two collision notices/two replacement questions, no validation warning, status 1 and no writes in either tree. |
| test_quickstart_valid_replacement | Existing config sentinel in original tree, valid empty replacement, then controlled remaining answers (or provided project options). Assert return 0, generated config/index/Makefile/batch files only in replacement, original sentinel unchanged, no invalid-path warning. |
| test_quickstart_invalid_nonempty_replacement | Missing directory then regular file then valid directory. Run main to completion; exactly two validation warnings, generated files only in valid replacement, invalid targets and original project untouched. |
| test_quickstart_cli_cancel | Optional but useful subprocess test: invoke module in occupied cwd with a single newline; assert process status 1, one replacement question, no warning/interrupt/traceback and unchanged tree. Bound subprocess time to avoid an actual blocking regression. |

Direct main cancellation raises SystemExit(1); do not incorrectly assert that
main returns 1. For a completed successful wizard main returns 0. Prefer checking
message fragments and prompt counts rather than entire localized/versioned output.
Disable terminal coloring using the module's established nocolor setup.

## Environment and commands

The initial container had no bare 'python' command and the available Python 3.7
had no pytest. An isolated environment was created under /workspace; application
sources were not changed. Clone emitted encoding warnings for two unrelated
wrongenc.inc fixtures; checkout subsequently reported a clean tracked tree and
focused tests passed. No encoding configuration was changed.

Reproduce the tested environment (run from /workspace/sphinx):

```sh
/usr/local/bin/python3.7 -m venv /workspace/sphinx-research-venv
/workspace/sphinx-research-venv/bin/python -m pip install -e . \
  'pytest==7.4.4' html5lib 'Jinja2==3.0.3' 'docutils==0.17.1' \
  'sphinxcontrib-applehelp==1.0.2' 'sphinxcontrib-devhelp==1.0.2' \
  'sphinxcontrib-htmlhelp==2.0.0' 'sphinxcontrib-serializinghtml==1.1.5' \
  'sphinxcontrib-qthelp==1.0.3' 'sphinxcontrib-jsmath==1.0.1'
/workspace/sphinx-research-venv/bin/python -m pytest tests/test_quickstart.py -q
```

These compatibility pins are a research environment recipe, not proposed project
dependency changes or a complete lockfile. Python 3.7 is in this base's supported
matrix; using a current global Sphinx/runtime would not validate this checkout.

Minimal unchanged-CLI reproduction, in workspace fixtures only:

```sh
mkdir -p /workspace/sphinx-research-cases/root-conf
# Fixture file, not application code:
touch /workspace/sphinx-research-cases/root-conf/conf.py
printf "\n" | /workspace/sphinx-research-venv/bin/python -m sphinx.cmd.quickstart \
  /workspace/sphinx-research-cases/root-conf
printf "exit=%s\n" "$?"
```

After an engineer implements the specified change and tests:

```sh
/workspace/sphinx-research-venv/bin/python -m pytest tests/test_quickstart.py -q
/workspace/sphinx-research-venv/bin/python -m pytest tests/test_quickstart.py \
  -k 'is_path or path_retry or existing_conf or replacement or cancel' -vv
/workspace/sphinx-research-venv/bin/python -m pytest -q
git diff --check
```

The first and second commands are required focused checks; the full suite is a
broader follow-up, not executed during this no-code investigation. Repository tox
alternatives, with tox installed and matching Python available, are
`tox -e py37 -- tests/test_quickstart.py -q` and `tox -e flake8 --
sphinx/cmd/quickstart.py tests/test_quickstart.py`. No new lint tool was installed.

## Reviewer acceptance checklist

- Empty input reaches the already-established SystemExit(1), never generation.
- Missing paths/files still fail; valid paths and home expansion still work.
- Both configuration layouts and repeated collisions have coverage.
- Tests distinguish successful wizard completion (0), cancellation (1), and EOF
  interruption (130), and assert no output files rather than only exit codes.
- Existing prompt tests and end-to-end generation/build tests remain green.
- Source changes are confined to the validator; tests cover the real boundary.
- No global validator bypass, status-code change, new dependency, or unrelated fix.
- This research PR changes only this Markdown document. Implementation and its
  independent review remain pending; keep the fork PR open and do not auto-merge.
