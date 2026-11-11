"""Test the HTML builder and check output against XPath."""
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from docutils import nodes
from docutils.parsers.rst import directives, roles

from sphinx import addnodes
from sphinx.environment.adapters.toctree import TocTree
from sphinx.testing.util import strip_escseq
from sphinx.util.docutils import additional_nodes


@pytest.fixture
def special_srcdir(rootdir, tempdir, monkeypatch):
    # Isolate registrations left by other applications before testing setup warnings.
    monkeypatch.setattr(directives, '_directives', {})
    monkeypatch.setattr(roles, '_roles', {})
    for node in additional_nodes:
        for visitor in (nodes.GenericNodeVisitor, nodes.SparseNodeVisitor):
            for prefix in ('visit_', 'depart_'):
                monkeypatch.delattr(visitor, prefix + node.__name__, raising=False)
    srcdir = tempdir / 'source'
    (rootdir / 'test-toctree-special').copytree(srcdir)
    return srcdir


@pytest.mark.sphinx(testroot='toctree-glob')
def test_relations(app, status, warning):
    app.builder.build_all()
    assert app.builder.relations['index'] == [None, None, 'foo']
    assert app.builder.relations['foo'] == ['index', 'index', 'bar/index']
    assert app.builder.relations['bar/index'] == ['index', 'foo', 'bar/bar_1']
    assert app.builder.relations['bar/bar_1'] == ['bar/index', 'bar/index', 'bar/bar_2']
    assert app.builder.relations['bar/bar_2'] == ['bar/index', 'bar/bar_1', 'bar/bar_3']
    assert app.builder.relations['bar/bar_3'] == ['bar/index', 'bar/bar_2', 'bar/bar_4/index']
    assert app.builder.relations['bar/bar_4/index'] == ['bar/index', 'bar/bar_3', 'baz']
    assert app.builder.relations['baz'] == ['index', 'bar/bar_4/index', 'qux/index']
    assert app.builder.relations['qux/index'] == ['index', 'baz', 'qux/qux_1']
    assert app.builder.relations['qux/qux_1'] == ['qux/index', 'qux/index', 'qux/qux_2']
    assert app.builder.relations['qux/qux_2'] == ['qux/index', 'qux/qux_1', None]
    assert 'quux' not in app.builder.relations


@pytest.mark.sphinx('singlehtml', testroot='toctree-empty')
def test_singlehtml_toctree(app, status, warning):
    app.builder.build_all()
    try:
        app.builder._get_local_toctree('index')
    except AttributeError:
        pytest.fail('Unexpected AttributeError in app.builder.fix_refuris')


@pytest.mark.sphinx(testroot='toctree', srcdir="numbered-toctree")
def test_numbered_toctree(app, status, warning):
    # give argument to :numbered: option
    index = (app.srcdir / 'index.rst').read_text(encoding='utf8')
    index = re.sub(':numbered:.*', ':numbered: 1', index)
    (app.srcdir / 'index.rst').write_text(index, encoding='utf8')
    app.builder.build_all()


def test_special_pages(make_app, special_srcdir):
    app = make_app(srcdir=special_srcdir, confoverrides={'numfig': False})
    app.build()
    assert app._warning.getvalue() == ''
    tree = app.env.get_and_resolve_doctree('index', app.builder)
    wrapper = next(tree.findall(nodes.compound))
    links = [(ref['refuri'], ref.astext()) for ref in wrapper.findall(nodes.reference)]
    assert links[:3] == [('genindex.html', 'Index'),
                         ('py-modindex.html', 'Module Index'),
                         ('search.html', 'Search Page')]
    for name in ('genindex', 'py-modindex', 'search'):
        assert (app.outdir / (name + '.html')).exists()
    parsed = next(app.env.get_doctree('index').findall(addnodes.toctree))
    assert parsed['entries'][:3] == [(None, 'genindex'), (None, 'modindex'),
                                     (None, 'search')]
    assert parsed['includefiles'] == ['nested/child', 'second']


@pytest.mark.parametrize('builder,config,root_uris,child_prefix', [
    ('html', {}, ['genindex.html', 'py-modindex.html', 'search.html'], '../'),
    ('dirhtml', {}, ['genindex/', 'py-modindex/', 'search/'], '../../'),
    ('html', {'html_file_suffix': '.page', 'html_link_suffix': '.link'},
     ['genindex.link', 'py-modindex.link', 'search.link'], '../'),
])
def test_special_page_uris(special_srcdir, make_app, builder, config, root_uris, child_prefix):
    app = make_app(buildername=builder, srcdir=special_srcdir, confoverrides=config)
    app.build()
    assert app._warning.getvalue() == ''
    for docname, expected in [('index', root_uris),
                              ('nested/child', [child_prefix + uri for uri in root_uris])]:
        tree = app.env.get_and_resolve_doctree(docname, app.builder)
        wrapper = next(tree.findall(nodes.compound))
        links = [(ref['refuri'], ref.astext()) for ref in wrapper.findall(nodes.reference)]
        titles = ['Index', 'Module Index', 'Search Page'] if docname == 'index' else [
            'Custom index', 'Custom modules', 'Custom search']
        assert links[:3] == list(zip(expected, titles))
    for name in ('genindex', 'py-modindex', 'search'):
        assert Path(app.builder.get_outfilename(name)).exists()
    body = Path(app.builder.get_outfilename('index')).read_text(encoding='utf8')
    assert 'href="%s">Index</a>' % root_uris[0] in body
    assert app.env.toc_secnumbers['nested/child'][''] == (1,)
    assert app.env.toc_secnumbers['second'][''] == (2,)
    for docname, number in [('nested/child', (1, 1)), ('second', (2, 1))]:
        figure = next(app.env.get_doctree(docname).findall(nodes.figure))
        assert app.env.toc_fignumbers[docname]['figure'][figure['ids'][0]] == number
    for special in ('genindex', 'modindex', 'search', 'py-modindex'):
        for mapping in (app.env.found_docs, app.env.tocs, app.env.titles,
                        app.env.toctree_includes, app.env.files_to_rebuild,
                        app.env.collect_relations(), app.env.toc_secnumbers):
            assert special not in mapping
        assert all(special not in includes for includes in app.env.toctree_includes.values())


@pytest.mark.parametrize('config,empty_modules,expected', [
    ({'html_use_index': False}, False, ['Module Index', 'Search Page']),
    ({'html_domain_indices': False}, False, ['Index', 'Search Page']),
    ({'html_domain_indices': ['std-modindex']}, False, ['Index', 'Search Page']),
    ({}, True, ['Index', 'Search Page']),
])
def test_special_page_availability(special_srcdir, make_app, config, empty_modules, expected):
    if empty_modules:
        child = special_srcdir / 'nested' / 'child.rst'
        child.write_text(child.read_text(encoding='utf8').replace(
            '.. py:module:: special_module', ''), encoding='utf8')
    app = make_app(srcdir=special_srcdir, confoverrides=config)
    app.build()
    assert app._warning.getvalue() == ''
    tree = app.env.get_and_resolve_doctree('index', app.builder)
    wrapper = next(tree.findall(nodes.compound))
    titles = [item[0][0].astext() for item in wrapper[0][0]]
    assert [title for title in titles if title in ('Index', 'Module Index', 'Search Page')] == expected
    for pagename, title in [('genindex', 'Index'), ('py-modindex', 'Module Index')]:
        if title not in expected:
            assert not (app.outdir / (pagename + '.html')).exists()


@pytest.mark.parametrize('builder', ['singlehtml', 'text', 'man', 'latex', 'texinfo'])
def test_special_pages_unsupported(special_srcdir, make_app, builder):
    app = make_app(buildername=builder, srcdir=special_srcdir)
    app.build()
    assert 'toctree contains reference' not in app._warning.getvalue()
    tree = TocTree(app.env).get_toctree_for('index', app.builder, False)
    assert not any(ref.astext() in ('Index', 'Module Index', 'Search Page',
                                    'Custom index', 'Custom modules', 'Custom search')
                   for ref in tree.findall(nodes.reference))
    if builder == 'singlehtml':
        sidebar = app.builder._get_local_toctree('index')
        for name in ('genindex', 'modindex', 'search'):
            assert name + '.html' not in sidebar
            assert not (app.outdir / (name + '.html')).exists()


@pytest.mark.parametrize('use_index', [True, False])
def test_special_pages_epub(special_srcdir, make_app, use_index):
    child = special_srcdir / 'nested' / 'child.rst'
    child.write_text(child.read_text(encoding='utf8').replace(
        '.. toctree::', '.. toctree::\n   :hidden:'), encoding='utf8')
    app = make_app(buildername='epub', srcdir=special_srcdir,
                   confoverrides={'epub_use_index': use_index})
    app.build()
    assert app._warning.getvalue() == ''
    tree = app.env.get_and_resolve_doctree('index', app.builder)
    wrapper = next(tree.findall(nodes.compound))
    links = [(ref['refuri'], ref.astext()) for ref in wrapper.findall(nodes.reference)]
    expected = [('py-modindex.xhtml', 'Module Index')]
    if use_index:
        expected.insert(0, ('genindex.xhtml', 'Index'))
    assert links[:len(expected)] == expected
    assert not any(uri.endswith('search.xhtml') for uri, _title in links)
    with ZipFile(next(Path(app.outdir).glob('*.epub'))) as archive:
        for uri, _title in expected:
            assert uri in archive.namelist()
        assert 'search.xhtml' not in archive.namelist()
        navigation = archive.read('nav.xhtml').decode()
        for uri, _title in expected:
            assert 'href="%s"' % uri in navigation


def test_special_pages_no_search_and_cached_environment(special_srcdir, make_app):
    app = make_app(srcdir=special_srcdir)
    app.builder.search = False
    app.build()
    assert app._warning.getvalue() == ''
    assert not (app.outdir / 'search.html').exists()
    parsed = next(app.env.get_doctree('index').findall(addnodes.toctree))
    assert (None, 'search') in parsed['entries']
    resolved = TocTree(app.env).resolve('index', app.builder, parsed)
    assert 'Search Page' not in resolved.astext()
    app.builder.search = True
    app.build(force_all=True)
    assert app._warning.getvalue() == ''
    resolved = TocTree(app.env).resolve('index', app.builder, parsed)
    assert ('search.html', 'Search Page') in [
        (ref['refuri'], ref.astext()) for ref in resolved.findall(nodes.reference)]
    outdir = app.outdir.parent / 'dirhtml'
    result = subprocess.run(
        [sys.executable, '-m', 'sphinx', '-b', 'dirhtml', '-d', app.doctreedir,
         app.srcdir, outdir], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    assert 'loading pickled environment' in result.stdout.decode()
    assert result.stderr == b''
    output = (outdir / 'nested' / 'child' / 'index.html').read_text(encoding='utf8')
    assert 'href="../../search/">Custom search</a>' in output
    assert (outdir / 'search' / 'index.html').exists()


def test_special_page_nonexact_names(special_srcdir, make_app):
    app = make_app(srcdir=special_srcdir)
    (app.srcdir / 'nested' / 'search.rst').write_text(
        'Normal search\n=============\n', encoding='utf8')
    index = app.srcdir / 'index.rst'
    index.write_text(index.read_text(encoding='utf8') + '''

.. toctree::

   nested/search
   ./search
   /search
   search.rst
   py-modindex
   genindex#fragment
   typo
''', encoding='utf8')
    app.build()
    warnings = strip_escseq(app._warning.getvalue())
    assert warnings.count('toctree contains reference to nonexisting document') == 6
    for target in ('search', 'py-modindex', 'genindex#fragment', 'typo'):
        assert "nonexisting document '%s'" % target in warnings
    assert 'index.rst:16: WARNING:' in warnings
    trees = list(app.env.get_doctree('index').findall(addnodes.toctree))
    assert trees[1]['includefiles'] == ['nested/search']


@pytest.mark.parametrize('options', [
    '', ':glob:', ':hidden:', ':reversed:', ':titlesonly:\n   :maxdepth: 1',
])
def test_special_page_options(special_srcdir, make_app, options):
    app = make_app(srcdir=special_srcdir)
    index = app.srcdir / 'index.rst'
    index.write_text(index.read_text(encoding='utf8') + '''

.. toctree::
   %s

   Custom <genindex>
   modindex
   search
   https://example.org/
   self
''' % options, encoding='utf8')
    app.build()
    assert app._warning.getvalue() == ''
    parsed = list(app.env.get_doctree('index').findall(addnodes.toctree))[1]
    expected = ['Custom', 'Module Index', 'Search Page', 'https://example.org/', 'Special pages']
    if options == ':reversed:':
        expected.reverse()
    adapter = TocTree(app.env)
    if options == ':hidden:':
        assert adapter.resolve('index', app.builder, parsed) is None
        parsed['includehidden'] = True
    resolved = adapter.resolve('index', app.builder, parsed, includehidden=True)
    assert [ref.astext() for ref in resolved.findall(nodes.reference)] == expected


def test_special_page_translated_titles(special_srcdir, make_app):
    app = make_app(srcdir=special_srcdir, confoverrides={'language': 'de'})
    app.build()
    assert app._warning.getvalue() == ''
    tree = app.env.get_and_resolve_doctree('index', app.builder)
    wrapper = next(tree.findall(nodes.compound))
    assert [ref.astext() for ref in wrapper.findall(nodes.reference)][:3] == [
        'Stichwortverzeichnis', 'Modulindex', 'Suche']
    tree = app.env.get_and_resolve_doctree('nested/child', app.builder)
    wrapper = next(tree.findall(nodes.compound))
    assert [ref.astext() for ref in wrapper.findall(nodes.reference)][:3] == [
        'Custom index', 'Custom modules', 'Custom search']
