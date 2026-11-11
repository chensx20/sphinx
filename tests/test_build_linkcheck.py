"""
    test_build_linkcheck
    ~~~~~~~~~~~~~~~~~~~~

    Test the build process with manpage builder with the test root.

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import json
from unittest import mock

import pytest
from requests import Response

from sphinx.builders.linkcheck import check_anchor


@pytest.fixture
def build_linkcheck_response(make_app, rootdir, sphinx_test_tempdir, request):
    srcdir = sphinx_test_tempdir / request.node.name
    (rootdir / 'test-basic').copytree(srcdir)

    def build(status_code, reason, body, anchors=True, fragment=True):
        url = 'https://google.com/test.txt'
        uri = url + '#test' if fragment else url
        (srcdir / 'index.rst').write_text('Links\n=====\n\n`link <%s>`_\n' % uri)
        app = make_app('linkcheck', srcdir=srcdir, freshenv=True,
                       confoverrides={'linkcheck_workers': 1,
                                      'linkcheck_retries': 1,
                                      'linkcheck_anchors': anchors})
        responses = []
        for _ in range(2):
            response = Response()
            response.status_code = status_code
            response.reason = reason
            response.url = url
            response.encoding = 'utf-8'
            response.history = []
            response.iter_content = mock.Mock(return_value=iter([body]))
            responses.append(response)
        head_response, get_response = responses
        requests = mock.Mock()
        with mock.patch('sphinx.builders.linkcheck.requests.head',
                        requests.head), \
                mock.patch('sphinx.builders.linkcheck.requests.get',
                           requests.get), \
                mock.patch('sphinx.builders.linkcheck.check_anchor',
                           wraps=check_anchor) as anchor_check:
            requests.head.return_value = head_response
            requests.get.return_value = get_response
            app.builder.build_all()

        if anchors and fragment:
            assert [call[0] for call in requests.mock_calls] == ['get']
            assert requests.get.call_args[1]['stream'] is True
        elif status_code >= 400:
            assert [call[0] for call in requests.mock_calls] == ['head', 'get']
        else:
            assert [call[0] for call in requests.mock_calls] == ['head']
        for call in requests.mock_calls:
            assert call[1] == (url,)

        rows = [json.loads(line) for line in
                (app.outdir / 'output.json').read_text().splitlines()]
        assert len(rows) == 1
        row = rows[0]
        assert row['uri'] == uri
        assert row['filename'] == 'index.rst'
        assert row['lineno'] == 4
        assert row['code'] == 0
        head_response.iter_content.assert_not_called()
        return app, row, (app.outdir / 'output.txt').read_text(), get_response, anchor_check

    return build


@pytest.mark.parametrize('status_code,reason', [
    (404, 'Not Found'), (500, 'Internal Server Error'),
])
@pytest.mark.parametrize('anchors', [True, False])
@pytest.mark.parametrize('body', ['<p>Error</p>', '<p id="test">Error</p>'])
def test_linkcheck_http_error_with_fragment(
        build_linkcheck_response, status_code, reason, anchors, body):
    app, row, text, response, anchor_check = build_linkcheck_response(
        status_code, reason, body, anchors=anchors)
    error_type = 'Client' if status_code == 404 else 'Server'
    info = '%s %s Error: %s for url: https://google.com/test.txt' % (
        status_code, error_type, reason)
    assert row['status'] == 'broken'
    assert row['info'] == info
    assert '[broken]' in text
    assert row['uri'] in text
    assert info in text
    assert "Anchor 'test' not found" not in text
    assert app.statuscode == 1
    assert app.builder.broken == {row['uri']: info}
    anchor_check.assert_not_called()
    response.iter_content.assert_not_called()


@pytest.mark.parametrize('body,found', [
    ('<p id="test">Found</p>', True),
    ('<a name="test">Found</a>', True),
    ('<p id="different">Missing</p>', False),
])
def test_linkcheck_successful_response_anchors(build_linkcheck_response, body, found):
    app, row, text, response, anchor_check = build_linkcheck_response(200, 'OK', body)
    assert row['status'] == ('working' if found else 'broken')
    assert row['info'] == ('' if found else "Anchor 'test' not found")
    assert app.statuscode == (0 if found else 1)
    anchor_check.assert_called_once_with(response, 'test')
    response.iter_content.assert_called_once_with(chunk_size=4096, decode_unicode=True)
    if found:
        assert text == ''
    else:
        assert '[broken]' in text
        assert row['uri'] in text
        assert row['info'] in text


@pytest.mark.parametrize('fragment', [True, False])
def test_linkcheck_anchors_disabled_success(build_linkcheck_response, fragment):
    app, row, text, response, anchor_check = build_linkcheck_response(
        200, 'OK', '<p id="different">Missing</p>', anchors=False, fragment=fragment)
    assert row['status'] == 'working'
    assert row['info'] == ''
    assert app.statuscode == 0
    assert text == ''
    anchor_check.assert_not_called()
    response.iter_content.assert_not_called()


@pytest.mark.parametrize('anchors', [True, False])
@pytest.mark.parametrize('status_code,reason,status,info', [
    (401, 'Unauthorized', 'working', ' - unauthorized'),
    (503, 'Service Unavailable', 'ignored',
     '503 Server Error: Service Unavailable for url: https://google.com/test.txt'),
])
def test_linkcheck_anchor_http_error_policies(
        build_linkcheck_response, status_code, reason, status, info, anchors):
    app, row, text, response, anchor_check = build_linkcheck_response(
        status_code, reason, '<p id="test">Error</p>', anchors=anchors)
    assert row['status'] == status
    assert row['info'] == info
    assert app.statuscode == 0
    assert text == ''
    assert app.builder.broken == {}
    anchor_check.assert_not_called()
    response.iter_content.assert_not_called()


@pytest.mark.sphinx('linkcheck', testroot='linkcheck', freshenv=True)
def test_defaults(app, status, warning):
    app.builder.build_all()

    assert (app.outdir / 'output.txt').exists()
    content = (app.outdir / 'output.txt').read_text()

    print(content)
    # looking for '#top' and '#does-not-exist' not found should fail
    assert "Anchor 'top' not found" in content
    assert "Anchor 'does-not-exist' not found" in content
    # looking for non-existent URL should fail
    assert " Max retries exceeded with url: /doesnotexist" in content
    # images should fail
    assert "Not Found for url: https://www.google.com/image.png" in content
    assert "Not Found for url: https://www.google.com/image2.png" in content
    # looking for local file should fail
    assert "[broken] path/to/notfound" in content
    assert len(content.splitlines()) == 6


@pytest.mark.sphinx('linkcheck', testroot='linkcheck', freshenv=True)
def test_defaults_json(app, status, warning):
    app.builder.build_all()

    assert (app.outdir / 'output.json').exists()
    content = (app.outdir / 'output.json').read_text()
    print(content)

    rows = [json.loads(x) for x in content.splitlines()]
    row = rows[0]
    for attr in ["filename", "lineno", "status", "code", "uri",
                 "info"]:
        assert attr in row

    assert len(content.splitlines()) == 10
    assert len(rows) == 10
    # the output order of the rows is not stable
    # due to possible variance in network latency
    rowsby = {row["uri"]: row for row in rows}
    assert rowsby["https://www.google.com#!bar"] == {
        'filename': 'links.txt',
        'lineno': 10,
        'status': 'working',
        'code': 0,
        'uri': 'https://www.google.com#!bar',
        'info': ''
    }
    # looking for non-existent URL should fail
    dnerow = rowsby['https://localhost:7777/doesnotexist']
    assert dnerow['filename'] == 'links.txt'
    assert dnerow['lineno'] == 13
    assert dnerow['status'] == 'broken'
    assert dnerow['code'] == 0
    assert dnerow['uri'] == 'https://localhost:7777/doesnotexist'
    assert rowsby['https://www.google.com/image2.png'] == {
        'filename': 'links.txt',
        'lineno': 18,
        'status': 'broken',
        'code': 0,
        'uri': 'https://www.google.com/image2.png',
        'info': '404 Client Error: Not Found for url: https://www.google.com/image2.png'
    }
    # looking for '#top' and '#does-not-exist' not found should fail
    assert "Anchor 'top' not found" == \
        rowsby["https://www.google.com/#top"]["info"]
    assert "Anchor 'does-not-exist' not found" == \
        rowsby["http://www.sphinx-doc.org/en/1.7/intro.html#does-not-exist"]["info"]
    # images should fail
    assert "Not Found for url: https://www.google.com/image.png" in \
        rowsby["https://www.google.com/image.png"]["info"]


@pytest.mark.sphinx(
    'linkcheck', testroot='linkcheck', freshenv=True,
    confoverrides={'linkcheck_anchors_ignore': ["^!", "^top$"],
                   'linkcheck_ignore': [
                       'https://localhost:7777/doesnotexist',
                       'http://www.sphinx-doc.org/en/1.7/intro.html#',
                       'https://www.google.com/image.png',
                       'https://www.google.com/image2.png',
                       'path/to/notfound']
                   })
def test_anchors_ignored(app, status, warning):
    app.builder.build_all()

    assert (app.outdir / 'output.txt').exists()
    content = (app.outdir / 'output.txt').read_text()

    # expect all ok when excluding #top
    assert not content


@pytest.mark.sphinx(
    'linkcheck', testroot='linkcheck', freshenv=True,
    confoverrides={'linkcheck_auth': [
        (r'.+google\.com/image.+', 'authinfo1'),
        (r'.+google\.com.+', 'authinfo2'),
    ]})
def test_auth(app, status, warning):
    mock_req = mock.MagicMock()
    mock_req.return_value = 'fake-response'

    with mock.patch.multiple('requests', get=mock_req, head=mock_req):
        app.builder.build_all()
        for c_args, c_kwargs in mock_req.call_args_list:
            if 'google.com/image' in c_args[0]:
                assert c_kwargs['auth'] == 'authinfo1'
            elif 'google.com' in c_args[0]:
                assert c_kwargs['auth'] == 'authinfo2'
            else:
                assert not c_kwargs['auth']


@pytest.mark.sphinx(
    'linkcheck', testroot='linkcheck', freshenv=True,
    confoverrides={'linkcheck_request_headers': {
        "https://localhost:7777/": {
            "Accept": "text/html",
        },
        "http://www.sphinx-doc.org": {  # no slash at the end
            "Accept": "application/json",
        },
        "*": {
            "X-Secret": "open sesami",
        }
    }})
def test_linkcheck_request_headers(app, status, warning):
    mock_req = mock.MagicMock()
    mock_req.return_value = 'fake-response'

    with mock.patch.multiple('requests', get=mock_req, head=mock_req):
        app.builder.build_all()
        for args, kwargs in mock_req.call_args_list:
            url = args[0]
            headers = kwargs.get('headers', {})
            if "https://localhost:7777" in url:
                assert headers["Accept"] == "text/html"
            elif 'http://www.sphinx-doc.org' in url:
                assert headers["Accept"] == "application/json"
            elif 'https://www.google.com' in url:
                assert headers["Accept"] == "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"
                assert headers["X-Secret"] == "open sesami"
            else:
                assert headers["Accept"] == "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"
