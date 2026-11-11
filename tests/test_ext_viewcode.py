"""
    test_ext_viewcode
    ~~~~~~~~~~~~~~~~~

    Test sphinx.ext.viewcode extension.

    :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest


@pytest.mark.parametrize('confoverrides', [
    {}, {'viewcode_enable_epub': False}, {'viewcode_enable_epub': True},
], ids=['default', 'disabled', 'enabled'])
@pytest.mark.parametrize('shared_cache', [True, False], ids=['cached', 'fresh'])
def test_viewcode_epub(make_app, rootdir, tempdir, confoverrides, shared_cache):
    srcdir = tempdir / 'viewcode'
    (rootdir / 'test-ext-viewcode').copytree(srcdir)

    if shared_cache:
        html = make_app('html', srcdir=srcdir, confoverrides=confoverrides)
        html.build()
        for page in ('index', 'spam/mod1', 'spam/mod2'):
            assert (html.outdir / '_modules' / (page + '.html')).exists()
        assert html.env._viewcode_modules
        assert (html.doctreedir / 'environment.pickle').exists()

    epub = make_app('epub', srcdir=srcdir, confoverrides=confoverrides)
    if shared_cache:
        assert epub.doctreedir == html.doctreedir
        assert epub.outdir != html.outdir
        assert epub.env is not html.env
        assert epub.env._viewcode_modules == html.env._viewcode_modules
        assert epub.env._viewcode_modules

    reread = []
    epub.connect('doctree-read', lambda app, doctree: reread.append(doctree))
    epub.build()
    if shared_cache:
        assert reread == []
        assert epub.env._viewcode_modules == html.env._viewcode_modules

    opf = ElementTree.fromstring((epub.outdir / 'content.opf').read_text())
    manifest = {item.attrib['href'] for item in opf.findall(
        './/{http://www.idpf.org/2007/opf}item')}
    with ZipFile(epub.outdir / (epub.config.epub_basename + '.epub')) as archive:
        packaged = set(archive.namelist())

    if epub.config.viewcode_enable_epub:
        for page in ('index', 'spam/mod1', 'spam/mod2'):
            filename = '_modules/' + page + '.xhtml'
            assert (epub.outdir / filename).exists()
            assert filename in manifest
            assert filename in packaged
    else:
        assert not (epub.outdir / '_modules').exists()
        assert not any(filename.startswith('_modules/') for filename in manifest)
        assert not any(filename.startswith('_modules/') for filename in packaged)


@pytest.mark.sphinx(testroot='ext-viewcode')
def test_viewcode(app, status, warning):
    app.builder.build_all()

    warnings = re.sub(r'\\+', '/', warning.getvalue())
    assert re.findall(
        r"index.rst:\d+: WARNING: Object named 'func1' not found in include " +
        r"file .*/spam/__init__.py'",
        warnings
    )

    result = (app.outdir / 'index.html').read_text()
    assert result.count('href="_modules/spam/mod1.html#func1"') == 2
    assert result.count('href="_modules/spam/mod2.html#func2"') == 2
    assert result.count('href="_modules/spam/mod1.html#Class1"') == 2
    assert result.count('href="_modules/spam/mod2.html#Class2"') == 2
    assert result.count('@decorator') == 1

    # test that the class attribute is correctly documented
    assert result.count('this is Class3') == 2
    assert 'this is the class attribute class_attr' in result
    # the next assert fails, until the autodoc bug gets fixed
    assert result.count('this is the class attribute class_attr') == 2

    result = (app.outdir / '_modules/spam/mod1.html').read_text()
    result = re.sub('<span class=".*?">', '<span>', result)  # filter pygments classes
    assert ('<div class="viewcode-block" id="Class1"><a class="viewcode-back" '
            'href="../../index.html#spam.Class1">[docs]</a>'
            '<span>@decorator</span>\n'
            '<span>class</span> <span>Class1</span>'
            '<span>(</span><span>object</span><span>):</span>\n'
            '    <span>&quot;&quot;&quot;</span>\n'
            '<span>    this is Class1</span>\n'
            '<span>    &quot;&quot;&quot;</span></div>\n') in result


@pytest.mark.sphinx(testroot='ext-viewcode', tags=['test_linkcode'])
def test_linkcode(app, status, warning):
    app.builder.build(['objects'])

    stuff = (app.outdir / 'objects.html').read_text()

    assert 'http://foobar/source/foolib.py' in stuff
    assert 'http://foobar/js/' in stuff
    assert 'http://foobar/c/' in stuff
    assert 'http://foobar/cpp/' in stuff


@pytest.mark.sphinx(testroot='ext-viewcode-find')
def test_local_source_files(app, status, warning):
    def find_source(app, modname):
        if modname == 'not_a_package':
            source = (app.srcdir / 'not_a_package/__init__.py').read_text()
            tags = {
                'func1': ('def', 1, 1),
                'Class1': ('class', 1, 1),
                'not_a_package.submodule.func1': ('def', 1, 1),
                'not_a_package.submodule.Class1': ('class', 1, 1),
            }
        else:
            source = (app.srcdir / 'not_a_package/submodule.py').read_text()
            tags = {
                'not_a_package.submodule.func1': ('def', 11, 15),
                'Class1': ('class', 19, 22),
                'not_a_package.submodule.Class1': ('class', 19, 22),
                'Class3': ('class', 25, 30),
                'not_a_package.submodule.Class3.class_attr': ('other', 29, 29),
            }
        return (source, tags)

    app.connect('viewcode-find-source', find_source)
    app.builder.build_all()

    warnings = re.sub(r'\\+', '/', warning.getvalue())
    assert re.findall(
        r"index.rst:\d+: WARNING: Object named 'func1' not found in include " +
        r"file .*/not_a_package/__init__.py'",
        warnings
    )

    result = (app.outdir / 'index.html').read_text()
    assert result.count('href="_modules/not_a_package.html#func1"') == 1
    assert result.count('href="_modules/not_a_package.html#not_a_package.submodule.func1"') == 1
    assert result.count('href="_modules/not_a_package/submodule.html#Class1"') == 1
    assert result.count('href="_modules/not_a_package/submodule.html#Class3"') == 1
    assert result.count('href="_modules/not_a_package/submodule.html#not_a_package.submodule.Class1"') == 1

    assert result.count('href="_modules/not_a_package/submodule.html#not_a_package.submodule.Class3.class_attr"') == 1
    assert result.count('This is the class attribute class_attr') == 1
