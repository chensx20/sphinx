"""Test the other directives."""

import pytest
from docutils import nodes

from sphinx import addnodes
from sphinx.testing import restructuredtext
from sphinx.testing.util import assert_node


@pytest.mark.sphinx(testroot='toctree-glob')
def test_toctree(app):
    text = (".. toctree::\n"
            "\n"
            "   foo\n"
            "   bar/index\n"
            "   baz\n")

    app.env.find_files(app.config, app.builder)
    doctree = restructuredtext.parse(app, text, 'index')
    assert_node(doctree, [nodes.document, nodes.compound, addnodes.toctree])
    assert_node(doctree[0][0],
                entries=[(None, 'foo'), (None, 'bar/index'), (None, 'baz')],
                includefiles=['foo', 'bar/index', 'baz'])


@pytest.mark.sphinx(testroot='toctree-glob')
def test_relative_toctree(app):
    text = (".. toctree::\n"
            "\n"
            "   bar_1\n"
            "   bar_2\n"
            "   bar_3\n"
            "   ../quux\n")

    app.env.find_files(app.config, app.builder)
    doctree = restructuredtext.parse(app, text, 'bar/index')
    assert_node(doctree, [nodes.document, nodes.compound, addnodes.toctree])
    assert_node(doctree[0][0],
                entries=[(None, 'bar/bar_1'), (None, 'bar/bar_2'), (None, 'bar/bar_3'),
                         (None, 'quux')],
                includefiles=['bar/bar_1', 'bar/bar_2', 'bar/bar_3', 'quux'])


@pytest.mark.sphinx(testroot='toctree-glob')
def test_toctree_urls_and_titles(app):
    text = (".. toctree::\n"
            "\n"
            "   Sphinx <https://www.sphinx-doc.org/>\n"
            "   https://readthedocs.org/\n"
            "   The BAR <bar/index>\n")

    app.env.find_files(app.config, app.builder)
    doctree = restructuredtext.parse(app, text, 'index')
    assert_node(doctree, [nodes.document, nodes.compound, addnodes.toctree])
    assert_node(doctree[0][0],
                entries=[('Sphinx', 'https://www.sphinx-doc.org/'),
                         (None, 'https://readthedocs.org/'),
                         ('The BAR', 'bar/index')],
                includefiles=['bar/index'])


@pytest.mark.sphinx(testroot='toctree-glob')
def test_toctree_glob(app):
    text = (".. toctree::\n"
            "   :glob:\n"
            "\n"
            "   *\n")

    app.env.find_files(app.config, app.builder)
    doctree = restructuredtext.parse(app, text, 'index')
    assert_node(doctree, [nodes.document, nodes.compound, addnodes.toctree])
    assert_node(doctree[0][0],
                entries=[(None, 'baz'), (None, 'foo'), (None, 'quux')],
                includefiles=['baz', 'foo', 'quux'])

    # give both docname and glob (case1)
    text = (".. toctree::\n"
            "   :glob:\n"
            "\n"
            "   foo\n"
            "   *\n")

    app.env.find_files(app.config, app.builder)
    doctree = restructuredtext.parse(app, text, 'index')
    assert_node(doctree, [nodes.document, nodes.compound, addnodes.toctree])
    assert_node(doctree[0][0],
                entries=[(None, 'foo'), (None, 'baz'), (None, 'quux')],
                includefiles=['foo', 'baz', 'quux'])

    # give both docname and glob (case2)
    text = (".. toctree::\n"
            "   :glob:\n"
            "\n"
            "   *\n"
            "   foo\n")

    app.env.find_files(app.config, app.builder)
    doctree = restructuredtext.parse(app, text, 'index')
    assert_node(doctree, [nodes.document, nodes.compound, addnodes.toctree])
    assert_node(doctree[0][0],
                entries=[(None, 'baz'), (None, 'foo'), (None, 'quux'), (None, 'foo')],
                includefiles=['baz', 'foo', 'quux', 'foo'])


@pytest.mark.sphinx(testroot='toctree-glob')
def test_toctree_glob_and_url(app):
    text = (".. toctree::\n"
            "   :glob:\n"
            "\n"
            "   https://example.com/?q=sphinx\n")

    app.env.find_files(app.config, app.builder)
    doctree = restructuredtext.parse(app, text, 'index')
    assert_node(doctree, [nodes.document, nodes.compound, addnodes.toctree])
    assert_node(doctree[0][0],
                entries=[(None, 'https://example.com/?q=sphinx')],
                includefiles=[])


@pytest.mark.sphinx(testroot='toctree-glob')
def test_reversed_toctree(app):
    text = (".. toctree::\n"
            "   :reversed:\n"
            "\n"
            "   foo\n"
            "   bar/index\n"
            "   baz\n")

    app.env.find_files(app.config, app.builder)
    doctree = restructuredtext.parse(app, text, 'index')
    assert_node(doctree, [nodes.document, nodes.compound, addnodes.toctree])
    assert_node(doctree[0][0],
                entries=[(None, 'baz'), (None, 'bar/index'), (None, 'foo')],
                includefiles=['baz', 'bar/index', 'foo'])


@pytest.mark.sphinx(testroot='source-read-include', buildername='html')
def test_source_read_included_rst(app):
    source_read_docnames = []

    def replace_original(app, docname, source):
        source_read_docnames.append(docname)
        source[0] = source[0].replace('ORIGINAL', 'REPLACED')

    app.connect('source-read', replace_original)
    app.builder.build(['index'])

    output = (app.outdir / 'index.html').read_text(encoding='utf-8')
    assert 'Included REPLACED.' in output
    assert 'Nested REPLACED.' in output
    assert output.count('<span class="n">ORIGINAL</span>') == 2
    assert 'After the include.' in output
    assert source_read_docnames.count('index') == 1
    assert source_read_docnames.count('included') == 1
    assert source_read_docnames.count('nested') == 1
    assert 'literal' not in source_read_docnames
    assert 'code' not in source_read_docnames


@pytest.mark.sphinx(testroot='toctree-glob')
def test_toctree_twice(app):
    text = (".. toctree::\n"
            "\n"
            "   foo\n"
            "   foo\n")

    app.env.find_files(app.config, app.builder)
    doctree = restructuredtext.parse(app, text, 'index')
    assert_node(doctree, [nodes.document, nodes.compound, addnodes.toctree])
    assert_node(doctree[0][0],
                entries=[(None, 'foo'), (None, 'foo')],
                includefiles=['foo', 'foo'])
