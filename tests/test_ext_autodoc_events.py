"""
    test_ext_autodoc_events
    ~~~~~~~~~~~~~~~~~~~~~~~

    Test the autodoc extension.  This tests mainly for autodoc events

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import pytest

from sphinx.ext.autodoc import between, cut_lines
from test_ext_autodoc import do_autodoc


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_process_docstring(app):
    def on_process_docstring(app, what, name, obj, options, lines):
        lines.clear()
        lines.append('my docstring')

    app.connect('autodoc-process-docstring', on_process_docstring)

    actual = do_autodoc(app, 'function', 'target.process_docstring.func')
    assert list(actual) == [
        '',
        '.. py:function:: func()',
        '   :module: target.process_docstring',
        '',
        '   my docstring'
    ]


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_process_signature_for_each_overload(app):
    processed = []

    def process_signature(app, what, name, obj, options, args, retann):
        processed.append((args, retann))
        return args.replace('value', 'processed'), retann

    app.connect('autodoc-process-signature', process_signature)

    actual = do_autodoc(app, 'function', 'target.docstring_overloads.overloaded')
    assert processed == [('(value: int)', 'int'), ('(value: str)', 'str')]
    assert list(actual) == [
        '',
        '.. py:function:: overloaded(processed: int) -> int',
        '                 overloaded(processed: str) -> str',
        '   :module: target.docstring_overloads',
        '',
        '   Shared body.',
        '',
    ]


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_cut_lines(app):
    app.connect('autodoc-process-docstring',
                cut_lines(2, 2, ['function']))

    actual = do_autodoc(app, 'function', 'target.process_docstring.func')
    assert list(actual) == [
        '',
        '.. py:function:: func()',
        '   :module: target.process_docstring',
        '',
        '   second line',
        '',
    ]


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_between(app):
    app.connect('autodoc-process-docstring',
                between('---', ['function']))

    actual = do_autodoc(app, 'function', 'target.process_docstring.func')
    assert list(actual) == [
        '',
        '.. py:function:: func()',
        '   :module: target.process_docstring',
        '',
        '   second line',
        '',
    ]


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_between_exclude(app):
    app.connect('autodoc-process-docstring',
                between('---', ['function'], exclude=True))

    actual = do_autodoc(app, 'function', 'target.process_docstring.func')
    assert list(actual) == [
        '',
        '.. py:function:: func()',
        '   :module: target.process_docstring',
        '',
        '   first line',
        '   third line',
        '',
    ]
