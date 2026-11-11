"""
    test_build_linkcheck
    ~~~~~~~~~~~~~~~~~~~~

    Test the build process with manpage builder with the test root.

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import json
import shutil
from unittest import mock

import pytest
from docutils import nodes

from sphinx.errors import SphinxWarning
from sphinx.testing.path import path
from sphinx.util.console import strip_colors


@pytest.fixture
def local_link_app(make_app, rootdir, tmp_path):
    srcdir = path(str(tmp_path / 'source'))
    shutil.copytree(rootdir / 'test-linkcheck-local', srcdir)
    with mock.patch('sphinx.builders.linkcheck.requests.get') as get, \
            mock.patch('sphinx.builders.linkcheck.requests.head') as head:
        def create_app(**kwargs):
            return make_app('linkcheck', srcdir=srcdir, freshenv=True, **kwargs)

        yield create_app
        get.assert_not_called()
        head.assert_not_called()


def test_local_links(local_link_app):
    app = local_link_app()
    app.build()

    assert app.statuscode == 0
    assert not app._warning.getvalue()
    rows = [json.loads(line) for line in (app.outdir / 'output.json').read_text().splitlines()]
    local = {(row['filename'], row['uri']) for row in rows if row['status'] == 'local'}
    assert local == {
        ('index.rst', 'target'),
        ('index.rst', 'assets/'),
        ('index.rst', 'assets/semi;colon.txt'),
        ('index.rst', 'assets/encoded%20%23%3F.txt?download=1#missing-anchor'),
        ('nested/page.rst', 'target'),
        ('nested/page.rst', '/target'),
        ('nested/page.rst', '../target'),
    }
    assert all(row['status'] in ('local', 'unchecked') for row in rows)
    assert all(row['code'] == 0 and row['info'] == '' for row in rows)
    assert len((app.outdir / 'output.txt').read_text().splitlines()) == 7


@pytest.mark.parametrize('quiet', [False, True])
@pytest.mark.parametrize('uri', ['doesntexist', 'missing%20file?query#anchor'])
def test_local_missing(local_link_app, quiet, uri):
    app = local_link_app()
    app.quiet = quiet
    (app.srcdir / 'index.rst').write_text(
        'broken local-link_\n\n.. _local-link: %s\n' % uri)
    (app.srcdir / 'nested/page.rst').unlink()
    app.build()

    assert app.statuscode == 1
    assert not app.builder.broken  # Local results must not enter the HTTP cache.
    assert (app.outdir / 'output.txt').read_text() == (
        'index.rst:1: [broken] %s: Local file not found\n' % uri)
    assert json.loads((app.outdir / 'output.json').read_text()) == {
        'filename': 'index.rst', 'lineno': 1, 'uri': uri,
        'status': 'broken', 'code': 0, 'info': 'Local file not found',
    }
    if quiet:
        assert 'index.rst:1: WARNING: broken link: %s (Local file not found)' % uri in (
            app._warning.getvalue())
    else:
        assert not app._warning.getvalue()
        assert 'broken    %s - Local file not found' % uri in strip_colors(
            app._status.getvalue())


def test_local_warningiserror(local_link_app):
    app = local_link_app()
    app.warningiserror = True
    (app.srcdir / 'index.rst').write_text('`missing <doesntexist>`_\n')
    (app.srcdir / 'nested/page.rst').unlink()
    with pytest.raises(SphinxWarning, match='broken link: doesntexist'):
        app.build()
    assert app.statuscode == 1


def test_local_ignored(local_link_app):
    app = local_link_app(confoverrides={'linkcheck_ignore': ['doesntexist']})
    (app.srcdir / 'index.rst').write_text('`missing <doesntexist?query#anchor>`_\n')
    (app.srcdir / 'nested/page.rst').unlink()
    app.build()
    assert app.statuscode == 0
    assert not app._warning.getvalue()
    assert not (app.outdir / 'output.txt').read_text()
    assert json.loads((app.outdir / 'output.json').read_text()) == {
        'filename': 'index.rst', 'lineno': 1, 'uri': 'doesntexist?query#anchor',
        'status': 'ignored', 'code': 0, 'info': '',
    }


@pytest.mark.parametrize('existing_doc', ['a', 'z'])
def test_local_duplicate_uri(local_link_app, existing_doc):
    app = local_link_app(confoverrides={'linkcheck_workers': 1})
    (app.srcdir / 'index.rst').write_text(
        'Local links\n===========\n\n.. toctree::\n\n   a/page\n   z/page\n')
    (app.srcdir / 'nested/page.rst').unlink()
    for doc in ('a', 'z'):
        directory = app.srcdir / doc
        directory.makedirs()
        (directory / 'page.rst').write_text('`target <same>`_\n')
        if doc == existing_doc:
            (directory / 'same').write_text('exists')
    app.build()

    rows = [json.loads(line) for line in (app.outdir / 'output.json').read_text().splitlines()]
    duplicates = [row for row in rows if row['uri'] == 'same']
    assert [row['filename'] for row in duplicates] == ['a/page.rst', 'z/page.rst']
    assert {row['filename']: row['status'] for row in duplicates} == {
        doc + '/page.rst': 'local' if doc == existing_doc else 'broken' for doc in ('a', 'z')
    }
    assert app.statuscode == 1
    assert not app.builder.broken


@pytest.mark.parametrize('uri, status', [
    ('', 'unchecked'), ('#missing', 'unchecked'), ('mailto:nobody@example.org', 'unchecked'),
    ('ftp://example.org/missing', 'unchecked'), ('custom:missing', 'local'),
    ('file:///missing', 'local'), ('//example.org/missing', 'local'),
])
def test_local_exclusions(local_link_app, uri, status):
    app = local_link_app()
    doctree = nodes.paragraph('', '', nodes.reference('', 'link', refuri=uri))
    app.builder.write_doc('index', doctree)
    app.builder.finish()
    assert app.statuscode == 0
    assert json.loads((app.outdir / 'output.json').read_text())['status'] == status


def test_local_parent_outside_source(local_link_app):
    app = local_link_app()
    (app.srcdir.parent / 'outside').write_text('exists')
    (app.srcdir / 'index.rst').write_text('`outside <../outside>`_\n')
    (app.srcdir / 'nested/page.rst').unlink()
    app.build()
    assert app.statuscode == 0
    assert json.loads((app.outdir / 'output.json').read_text())['status'] == 'local'


def test_local_does_not_infer_html(local_link_app):
    app = local_link_app()
    with (app.srcdir / 'index.rst').open('a') as source:
        source.write('\n`generated HTML <nested/page.html>`_\n')
    app.build()
    rows = [json.loads(line) for line in (app.outdir / 'output.json').read_text().splitlines()]
    assert [row['status'] for row in rows if row['uri'] == 'nested/page.html'] == ['broken']
    assert app.statuscode == 1


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
    assert len(content.splitlines()) == 5


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

    assert len(content.splitlines()) == 8
    assert len(rows) == 8
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
        'lineno': 16,
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
                       'https://www.google.com/image2.png']
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
