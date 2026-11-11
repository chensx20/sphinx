"""Test transformations of included reStructuredText."""

import os
from pathlib import Path

import pytest
from docutils import nodes, statemachine
from docutils.parsers.rst import Parser
from docutils.utils import SystemMessage

from sphinx.directives.other import Include
from sphinx.errors import ExtensionError
from sphinx.testing import restructuredtext


@pytest.mark.sphinx('html', testroot='include-read')
def test_include_read_html(app, status, warning):
    source_reads = []
    include_reads = []
    starts = {}

    def source_read(app, docname, content):
        source_reads.append(docname)
        starts[docname] = app.env.temp_data['started_at']

    def include_read(app, relative_path, parent_docname, content):
        include_reads.append((relative_path, parent_docname, content[:]))
        assert app.env.docname == parent_docname
        assert app.env.temp_data['started_at'] == starts[parent_docname]

    app.connect('source-read', source_read)
    app.connect('include-read', include_read)
    app.build()

    html = (app.outdir / 'index.html').read_text(encoding='utf8')
    assert html.count('<p>REPLACED</p>') == 2
    assert 'REPLACE_ME' not in html
    assert sorted(source_reads) == ['index', 'something-to-include']
    assert include_reads == [(Path('something-to-include.rst'), 'index',
                              ['Testing\n========\n\nREPLACED'])]
    assert set(app.env.get_domain('duration').reading_durations) == set(source_reads)
    assert 'slowest reading durations' in status.getvalue()
    assert warning.getvalue() == ''
    for name in ('index', 'something-to-include'):
        assert '&REPLACE_ME;' in (app.srcdir / f'{name}.rst').read_text(encoding='utf8')


@pytest.mark.sphinx('html', testroot='include-read', freshenv=True)
def test_include_source_read_only(app):
    app.events.listeners['include-read'].clear()
    app.build()

    html = (app.outdir / 'index.html').read_text(encoding='utf8')
    assert '<p>&amp;REPLACE_ME;</p>' in html
    assert html.count('<p>REPLACED</p>') == 1
    included_html = (app.outdir / 'something-to-include.html').read_text(encoding='utf8')
    assert '<p>REPLACED</p>' in included_html


@pytest.mark.sphinx(testroot='basic')
def test_include_read_priority(app):
    included = app.srcdir / 'priority.inc'
    included.write_text('original', encoding='utf8')
    calls = []

    def first(app_, relative_path, parent_docname, content):
        assert app_ is app
        assert isinstance(relative_path, Path)
        assert relative_path == Path('priority.inc')
        assert parent_docname == app.env.docname == 'index'
        assert content == ['original']
        calls.append('first')
        content[0] = 'changed'

    def second(app, relative_path, parent_docname, content):
        calls.append('second')
        assert content == ['changed']
        content[0] += '\n\nfinal'

    app.connect('include-read', second, priority=700)
    app.connect('include-read', first, priority=200)
    doctree = restructuredtext.parse(app, '.. include:: priority.inc\n\nFollowing.\n')
    assert [node.astext() for node in doctree.findall(nodes.paragraph)] == [
        'changed', 'final', 'Following.']
    assert calls == ['first', 'second']
    assert included.read_text(encoding='utf8') == 'original'


@pytest.mark.sphinx(testroot='basic')
def test_include_read_nested_repeated(app, warning):
    (app.srcdir / 'outer.inc').write_text(
        'Outer.\n\n.. include:: nested.inc\n\nAfter nested.\n', encoding='utf8')
    (app.srcdir / 'nested.inc').write_text('Nested.', encoding='utf8')
    calls = []

    def include_read(app, relative_path, parent_docname, content):
        assert parent_docname == app.env.docname == 'index'
        calls.append(relative_path)
        # Altering "inclusion" would corrupt Docutils' end marker if exposed.
        content[0] = content[0].replace('inclusion', 'changed').replace('Nested.', 'Changed.')

    app.connect('include-read', include_read)
    doctree = restructuredtext.parse(
        app, '.. include:: outer.inc\n\n.. include:: outer.inc\n\nFollowing.\n')
    assert calls == [Path('outer.inc'), Path('nested.inc')] * 2
    assert [node.astext() for node in doctree.findall(nodes.paragraph)] == [
        'Outer.', 'Changed.', 'After nested.', 'Outer.', 'Changed.', 'After nested.',
        'Following.']
    assert doctree.include_log == [(str(app.srcdir / 'index.rst'), (None,) * 4)]
    assert warning.getvalue() == ''


@pytest.mark.parametrize('argument', [
    '../path with spaces/caf\u00e9.inc', '/path with spaces/caf\u00e9.inc'])
@pytest.mark.sphinx(testroot='basic')
def test_include_read_paths(app, argument):
    included = app.srcdir / 'path with spaces' / 'caf\u00e9.inc'
    included.parent.mkdir(exist_ok=True)
    included.write_text('Unicode \u00e9 and \u65e5\u672c\u8a9e.', encoding='utf8')
    calls = []
    app.connect('include-read', lambda app, path, parent, content:
                calls.append((path, parent, content[:])))

    doctree = restructuredtext.parse(app, f'.. include:: {argument}\n', 'subdir/index')
    assert calls == [(Path('path with spaces/caf\u00e9.inc'), 'subdir/index',
                      ['Unicode \u00e9 and \u65e5\u672c\u8a9e.'])]
    paragraph = next(doctree.findall(nodes.paragraph))
    assert paragraph.astext() == 'Unicode \u00e9 and \u65e5\u672c\u8a9e.'
    assert Path(paragraph.source).resolve() == included
    assert paragraph.line == 1


@pytest.mark.parametrize(('options', 'expected'), [
    ('   :start-line: 1\n   :end-line: 4\n', 'BEGIN\nselected\nEND'),
    ('   :start-after: BEGIN\n   :end-before: END\n', '\nselected'),
    ('   :start-line: 1\n   :end-line: 4\n'
     '   :start-after: BEGIN\n   :end-before: END\n', '\nselected'),
])
@pytest.mark.sphinx(testroot='basic')
def test_include_read_selection(app, options, expected):
    (app.srcdir / 'selection.inc').write_text(
        'discard\nBEGIN\nselected\nEND\ndiscard\n', encoding='utf8')
    calls = []

    def include_read(app, relative_path, parent_docname, content):
        calls.append(content[0])
        content[0] = 'Replacement without selection markers.'

    app.connect('include-read', include_read)
    doctree = restructuredtext.parse(app, f'.. include:: selection.inc\n{options}\n')
    assert calls == [expected]
    assert doctree.astext() == 'Replacement without selection markers.'


@pytest.mark.parametrize('replacement', ['', '\n', 'One.\n\nTwo.\n',
                                         'Unicode \u00e9 \u65e5\u672c\u8a9e.\n',
                                         '::\n\n\tindented\n\tline\n'])
@pytest.mark.sphinx(testroot='basic')
def test_include_read_text(app, replacement, warning):
    (app.srcdir / 'text.inc').write_text('original\n', encoding='utf8')

    def include_read(app, relative_path, parent_docname, content):
        content[0] = replacement

    app.connect('include-read', include_read)
    doctree = restructuredtext.parse(app, '.. include:: text.inc\n\nFollowing.\n')
    expected = restructuredtext.parse(app, replacement + '\n\nFollowing.\n')
    assert doctree.astext() == expected.astext()
    assert doctree.include_log == [(str(app.srcdir / 'index.rst'), (None,) * 4)]
    assert warning.getvalue() == ''


@pytest.mark.parametrize('failure', ['listener', 'file', 'selection', 'insertion'])
@pytest.mark.sphinx(testroot='basic')
def test_include_read_cleanup(app, monkeypatch, failure):
    (app.srcdir / 'cleanup.inc').write_text('original', encoding='utf8')
    original_run = Include.__mro__[1].run
    machines = []

    def check_run(directive):
        state_machine = directive.state_machine
        assert state_machine.insert_input != statemachine.StateMachine.insert_input.__get__(
            state_machine)
        machines.append(state_machine)
        return original_run(directive)

    monkeypatch.setattr(Include.__mro__[1], 'run', check_run)

    def fail_listener(app, relative_path, parent_docname, content):
        msg = 'listener failed'
        raise ValueError(msg)

    def fail_insertion(self, lines, source):
        msg = 'insertion failed'
        raise ValueError(msg)

    text = '.. include:: cleanup.inc\n'
    if failure == 'listener':
        app.connect('include-read', fail_listener)
        with pytest.raises(ExtensionError, match='listener failed'):
            restructuredtext.parse(app, text)
    elif failure == 'insertion':
        monkeypatch.setattr(statemachine.StateMachine, 'insert_input', fail_insertion)
        with pytest.raises(ValueError, match='insertion failed'):
            restructuredtext.parse(app, text)
    else:
        if failure == 'file':
            text = '.. include:: missing.inc\n'
        else:
            text += '   :start-after: missing\n'
        with pytest.raises(SystemMessage):
            restructuredtext.parse(app, text)

    assert len(machines) == 1
    state_machine = machines[0]
    assert state_machine.insert_input == statemachine.StateMachine.insert_input.__get__(state_machine)


@pytest.mark.sphinx(testroot='basic')
def test_include_read_diagnostics(app, warning):
    (app.srcdir / 'diagnostic.inc').write_text(
        'Paragraph.\n\n.. unknown-directive::\n', encoding='utf8')
    doctree = restructuredtext.parse(app, '.. include:: diagnostic.inc\n')
    assert Path(doctree[0].source).resolve() == app.srcdir / 'diagnostic.inc'
    assert doctree[0].line == 1
    warnings = warning.getvalue()
    assert 'diagnostic.inc:3:' in warnings
    assert 'Unknown directive type "unknown-directive"' in warnings
    with pytest.raises(SystemMessage):
        restructuredtext.parse(app, 'Paragraph.\n\n.. include:: missing.inc\n')
    with pytest.raises(SystemMessage):
        restructuredtext.parse(app, 'Paragraph.\n\n\n\n.. include:: diagnostic.inc\n'
                               '   :start-after: missing\n')
    warnings = warning.getvalue()
    assert 'index.rst:3:' in warnings
    assert 'missing.inc' in warnings
    assert 'index.rst:5:' in warnings
    assert 'Text not found' in warnings


@pytest.mark.sphinx(testroot='basic')
def test_include_read_circular(app, warning):
    (app.srcdir / 'circular.inc').write_text('.. include:: circular.inc\n', encoding='utf8')
    calls = []
    app.connect('include-read', lambda app, path, parent, content: calls.append(path))
    restructuredtext.parse(app, '.. include:: circular.inc\n\nFollowing.\n')
    assert calls == [Path('circular.inc')]
    assert 'circular inclusion' in warning.getvalue()
    assert 'circular.inc:1:' in warning.getvalue()


@pytest.mark.parametrize('options', ['   :literal:\n', '   :code: text\n'])
@pytest.mark.sphinx(testroot='basic')
def test_include_read_unaffected_branches(app, options):
    (app.srcdir / 'literal.inc').write_text('&REPLACE_ME;\n', encoding='utf8')
    calls = []
    app.connect('include-read', lambda *args: calls.append(args))
    doctree = restructuredtext.parse(app, f'.. include:: literal.inc\n{options}\n')
    assert next(doctree.findall(nodes.literal_block)).astext().strip() == '&REPLACE_ME;'
    assert calls == []


@pytest.mark.sphinx(testroot='basic')
def test_include_read_standard_and_literalinclude(app):
    (app.srcdir / 'literalinclude.inc').write_text('&REPLACE_ME;\n', encoding='utf8')
    calls = []
    app.connect('include-read', lambda *args: calls.append(args))
    doctree = restructuredtext.parse(
        app, '.. include:: <isonum.txt>\n\n'
        '|copy|\n\n.. literalinclude:: literalinclude.inc\n')
    assert '\u00a9' in doctree.astext()
    assert '&REPLACE_ME;' in doctree.astext()
    assert calls == []


@pytest.mark.sphinx(testroot='basic')
def test_include_read_separate_parser(app, monkeypatch):
    (app.srcdir / 'parser.inc').write_text('Unchanged.', encoding='utf8')
    calls = []
    app.connect('include-read', lambda *args: calls.append(args))
    monkeypatch.setitem(Include.option_spec, 'parser', lambda value: Parser)
    doctree = restructuredtext.parse(app, '.. include:: parser.inc\n   :parser: rst\n')
    assert doctree.astext() == 'Unchanged.'
    assert calls == []


def test_include_read_dependency_rebuild(tmp_path, make_app):
    (tmp_path / 'conf.py').write_text('', encoding='utf8')
    app = make_app('html', srcdir=tmp_path)
    (app.srcdir / 'index.rst').write_text(
        'Title\n=====\n\n.. include:: dependency.inc\n', encoding='utf8')
    included = app.srcdir / 'dependency.inc'
    included.write_text('original', encoding='utf8')
    calls = []

    def include_read(app, relative_path, parent_docname, content):
        calls.append((relative_path, parent_docname))
        content[0] = content[0].upper()

    app.connect('include-read', include_read)
    app.build()
    assert '<p>ORIGINAL</p>' in (app.outdir / 'index.html').read_text(encoding='utf8')
    dependencies = {Path(app.srcdir, dep).resolve() for dep in app.env.dependencies['index']}
    assert included in dependencies
    included.write_text('updated', encoding='utf8')
    mtime = app.env.all_docs['index'] + 1
    os.utime(included, (mtime, mtime))
    app.build()
    assert calls == [(Path('dependency.inc'), 'index')] * 2
    assert '<p>UPDATED</p>' in (app.outdir / 'index.html').read_text(encoding='utf8')
    assert 'index' in app.env.found_docs
    assert 'dependency' not in app.env.found_docs
    assert app._warning.getvalue() == ''
