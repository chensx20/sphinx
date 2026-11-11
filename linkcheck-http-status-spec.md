# Specification: HTTP errors take precedence over linkcheck anchors

## Scope and provenance

- Repository: `chensx20/sphinx`.
- Required implementation and PR base: `cam-base/sphinx-doc__sphinx-8269-AGYN-S55-20261111T113923Z-b1cbeb`.
- Verified base commit: `1e2ccd8f0eca0870cf6f8fce6934e2da8eba9b72`.
- Task identifiers: `sphinx-doc__sphinx-8269`, `AGYN-S55-20261111T113923Z-b1cbeb`.
- Evidence is limited to the supplied bug description and this repository at the base commit. No earlier fixes, benchmark patches, issue discussions, or external documentation were consulted.
- This PR is a research handoff, not an implementation. It changes only this specification. Implementation and regression tests belong in the subsequently created formal issue and implementation work.

## Problem

With `linkcheck_anchors=True`, checking `https://google.com/test.txt#test` reports `Anchor 'test' not found` when the HTTP response is 404 or 500. The result must instead be broken with the corresponding HTTP error, as when anchor checking is disabled. An HTTP error body containing a matching anchor must not make an error response working.

## Repository findings and root cause

All line references below refer to the verified base commit.

1. `sphinx/builders/linkcheck.py:132-146` separates the request URL from the fragment and applies ignored-anchor patterns.
2. `sphinx/builders/linkcheck.py:164-172` performs a streaming GET for a nonignored fragment when anchor checking is enabled, then immediately calls `check_anchor`. It never calls `response.raise_for_status()` on that path.
3. `check_anchor`, at `sphinx/builders/linkcheck.py:62-77`, streams response content into `AnchorCheckParser`. The parser checks `id` and `name` attributes without considering HTTP status. Consequently an error page without the anchor becomes an anchor error, while an error page with the anchor can become working (or redirected).
4. The alternative path, `sphinx/builders/linkcheck.py:173-185`, checks HEAD status and retries with GET on `HTTPError`, validating that GET too.
5. The shared `HTTPError` handler at `sphinx/builders/linkcheck.py:186-194` already provides the required classification: 401 is working with ` - unauthorized`; 503 is ignored; other HTTP errors, including 404 and 500, are broken with `str(err)`.
6. `sphinx/util/requests.py:get` and `head` add configured request settings and delegate to Requests. They do not validate response status automatically. Keep the fix at the linkcheck call site, not in these shared adapters or the HTML parser.
7. `sphinx/builders/linkcheck.py:241-254` handles retries and caching. Reporting at `:265-318` writes structured results and text diagnostics. `write_doc` sets `app.statuscode=1` if broken links exist. The JSON `code` field is a redirect code, not an HTTP error status; keep it zero for these errors.

## Required functional change

In the anchor-enabled GET branch of `CheckExternalLinksBuilder.check_thread`'s nested `check_uri`, validate the GET response with `response.raise_for_status()` immediately after receiving it and before calling `check_anchor` or reading its body. Keep validation inside the existing try block so the existing HTTP error handler owns classification and diagnostics.

Acceptance criteria:

- Both 404 and 500 with a fragment produce broken results with the HTTP status/reason and request URL, never an anchor-not-found message.
- Error classification is independent of whether the error body contains the requested anchor.
- HTTP errors short-circuit anchor parsing and body iteration.
- A successful response with the requested anchor remains working; a successful response without it remains broken with the existing anchor-not-found diagnostic.
- With anchors disabled, preserve HEAD-first and HTTP-error-to-GET fallback behavior, including when the original URI has a fragment.
- Preserve 401-working and 503-ignored policies for anchored requests by using the shared handler; do not redefine every 4xx/5xx as broken.
- Preserve URI fragment reporting, percent-decoding of anchors, ignored-anchor patterns, redirects, authentication, headers, timeouts, retries, TLS handling, and caching.
- Do not add content-type restrictions: a `.txt` URL with a fragment still needs HTTP status validation.
- No new dependency, configuration option, parser rewrite, network abstraction, or request-method refactor is needed.

## Deterministic regression design

### Placement and isolation

Add tests to `tests/test_build_linkcheck.py`, using its existing pytest and `unittest.mock` conventions and the `sphinx.testing.fixtures` plugin loaded by `tests/conftest.py`.

Use `testroot='basic'`, a fresh app/environment per parameter case, `linkcheck_workers=1`, `linkcheck_retries=1`, and an explicit `linkcheck_anchors` override. Replace only the copied temporary `index.rst` with a minimal titled document containing one explicit external link before `build_all()`. Do not modify the shared `tests/roots/test-linkcheck/links.txt`: existing tests assert its exact line numbers and result counts and it contains live URLs.

Patch `sphinx.builders.linkcheck.requests.get` and `.head` for the entire build; every request must be intercepted. Return real `requests.Response` instances with explicitly assigned integer `status_code`, string `reason`, string fragment-free `url`, UTF-8 `encoding`, and empty `history`. Feed deterministic HTML chunks through a mock of each response's `iter_content`; retain real `raise_for_status()` behavior. Do not use a bare `MagicMock` response whose status check silently succeeds. The real `HTTPError` must carry its response so the existing handler can read `err.response.status_code`.

The mocked URL can be the exact reported `https://google.com/test.txt#test`; it must never be contacted. Assert outgoing requests use `https://google.com/test.txt`, without `#test`. A local `.invalid` hostname may be used for additional cases. Unexpected GET/HEAD calls must fail assertions; do not let them reach the network. Keep patches active until build completion and ensure worker teardown uses the existing builder/fixture lifecycle.

### Required HTTP-error matrix

Cross these dimensions (eight cases):

- Status: 404 / `Not Found`, 500 / `Internal Server Error`.
- `linkcheck_anchors`: true and false.
- Body: no matching anchor, or HTML containing `id="test"`.

For anchors enabled, GET returns the configured error response and HEAD must not be called. Assert anchor checking and `iter_content` were not called: HTTP validation must occur before either. For anchors disabled, HEAD returns the configured error and GET returns a separate response with the same status/reason; assert HEAD then GET, and no anchor checking or body iteration. Inspect ordering within each case, not global worker execution order.

For every case, assert:

- Exactly one JSON result with `status='broken'`, `code=0`, original URI including `#test`, expected source filename/line, and the corresponding HTTP error in `info`.
- Expected HTTP diagnostics are `404 Client Error: Not Found for url: https://google.com/test.txt` and `500 Server Error: Internal Server Error for url: https://google.com/test.txt`; enabled and disabled modes agree for equivalent responses.
- `output.txt` contains the original URI, `[broken]`, and HTTP diagnostic, not `Anchor 'test' not found`.
- `app.statuscode` is 1 and the broken-link cache contains the HTTP diagnostic.

The four anchors-enabled cases must fail on the base: absent-anchor bodies currently yield anchor diagnostics; matching-anchor bodies currently incorrectly pass. The four anchors-disabled cases are parity controls and should already pass on the base. After the fix all eight must pass.

### Successful-response matrix

With anchors enabled and status 200 / `OK`, parameterize the following bodies:

| Body | Expected result |
| --- | --- |
| HTML containing `id="test"` | working, empty info, exit status 0 |
| HTML containing `name="test"` | working, empty info, exit status 0 |
| HTML containing only `id="different"` | broken, `Anchor 'test' not found`, exit status 1 |

Assert GET only, fragment-free request URL, one JSON row preserving the original URI, and `code=0`. Working cases leave `output.txt` empty; the missing-anchor case has one broken text entry. Spy on real anchor parsing rather than replacing it with a fixed answer, so these tests verify actual body handling.

With anchors disabled, status-200 HEAD and a body missing `test` must be working with empty info, no GET, and no anchor parsing. Include a fragmentless successful URL control for HEAD-first behavior.

### Existing special-status policies

Add focused anchored GET cases for 401 / `Unauthorized` and 503 / `Service Unavailable` to prove the shared handler is used before parsing. Expect working with ` - unauthorized` for 401, ignored with the HTTP diagnostic for 503, `code=0`, no body iteration, no missing-anchor text, and exit status 0 for either isolated build. Use the same disabled-anchor cases as parity controls if convenient.

### Output and test quality rules

- Index results by URI if a test ever contains multiple links; worker output order is not contractual.
- Build a fresh app for each parameter case; do not reuse cached good/broken entries or cumulative output files.
- Check both structured and human-readable diagnostics. A status-only assertion would miss this bug because one current failure mode already says broken.
- Do not assert an HTTP status of 404/500 in JSON `code`.
- Do not add sleeps, real external requests, a fixed-port HTTP server, or a third-party mocking dependency.
- Suggested names: `test_linkcheck_http_error_with_fragment`, `test_linkcheck_successful_response_anchors`, `test_linkcheck_anchors_disabled_success`, and `test_linkcheck_anchor_http_error_policies`.

## Local dependency and test setup

### Observed environment and limitations

The supplied local checkout was absent, so it was cloned into `/workspace/sphinx` and detached at the verified base. Git reported encoding warnings during cloning; a subsequent working-tree status and tracked diff were clean. Python 3.12 is the system interpreter, without pip; cached Python 3.8.20 is available at `/opt/agyn/cache/python/cpython-3.8-linux-x86_64-gnu/bin/python3.8`, with pip but without pytest. No dependencies were downloaded and no runtime regression test was executed during this research. No implementation or test code was written.

The repository's `tox.ini` targets Python 3.5-3.9 and installs the `test` extra. Prefer Python 3.8 for this historical base, not the current system Python. `setup.py` declares runtime dependencies and the `test` extra (`pytest`, `pytest-cov`, `html5lib`, `typed_ast`, `cython`). `doc/internals/contributing.rst:165-220` describes pytest/tox use and requires regression tests that fail before the fix and pass afterward.

### Suggested reproducible bootstrap

Use an isolated environment under the checkout. The following is a proposed compatibility recipe, not a validated lockfile; installation requires access to the configured package index or a prepopulated local wheelhouse. These pins are setup recommendations, not claims of versions declared by the repository. Record the resolved environment after successful installation.

```sh
cd /workspace/sphinx
/opt/agyn/cache/python/cpython-3.8-linux-x86_64-gnu/bin/python3.8 -m venv .venv
.venv/bin/python -m pip install 'pip<25' 'setuptools==57.5.0' 'wheel==0.37.1'
.venv/bin/python -m pip install -e '.[test]' \
  'Jinja2==2.11.3' 'MarkupSafe==2.0.1' 'docutils==0.16' \
  'pytest==6.2.5' 'pytest-cov==2.12.1' 'Cython==0.29.36' \
  'sphinxcontrib-applehelp==1.0.2' 'sphinxcontrib-devhelp==1.0.2' \
  'sphinxcontrib-jsmath==1.0.1' 'sphinxcontrib-htmlhelp==1.0.3' \
  'sphinxcontrib-serializinghtml==1.1.4' 'sphinxcontrib-qthelp==1.0.3'
.venv/bin/python -m pip check
.venv/bin/python -m pip freeze
```

Jinja compatibility matters because `sphinx/jinja2glue.py` imports `contextfunction`; the old base does not declare an upper bound. The older Docutils, extension, and test-tool versions avoid assuming that unconstrained modern releases support this Sphinx base and Python 3.8. If installation fails, resolve environment compatibility separately; do not change production code to accommodate setup drift. For an offline installation, provide all transitive wheels locally and use pip's `--no-index --find-links` options.

### Verification commands after implementation

```sh
# Required fast, deterministic gate; these are proposed test names.
.venv/bin/python -m pytest -q tests/test_build_linkcheck.py -k 'http_error_with_fragment or successful_response_anchors or anchors_disabled_success or anchor_http_error_policies'
# Existing mocked build integration (no live-linkcheck default tests).
.venv/bin/python -m pytest -q tests/test_build.py -k 'test_build_all and linkcheck'
# Full module only when external-network tests are intentionally permitted.
.venv/bin/python -m pytest -q tests/test_build_linkcheck.py
# Repository's supported tox route; install compatible tox separately if used.
tox -e py38 -- tests/test_build_linkcheck.py -k 'http_error_with_fragment or successful_response_anchors or anchors_disabled_success or anchor_http_error_policies'
```

Run the new deterministic selection against the unmodified base and capture expected failures, then apply the minimal implementation and rerun to green. Keep test changes present for both runs; revert only the production change in an isolated implementation worktree when demonstrating the red run. Repeat the focused tests to check determinism. The full existing linkcheck module includes real Google, Sphinx, W3C, and localhost URLs, so it is not an offline/reliable gate and was not run here. No JavaScript, browser, LaTeX, or graphviz setup is required for the proposed focused tests.

## Handoff and completion criteria

The future formal issue should adopt the required functional change, test matrix, setup caveats, and fail-before/pass-after requirement above. The implementation is complete when the added status validation precedes body parsing, all deterministic cases pass, existing special policies remain intact, and the diff is limited to the minimal linkcheck change, related tests, and any repository-required changelog entry. Dependency/setup adjustments must not silently broaden production scope.

Keep this research PR OPEN and do not merge it. Its base must remain the exact required branch above; do not target the fork's default branch or upstream.
