"""
    test_quickstart
    ~~~~~~~~~~~~~~~

    Test the sphinx.quickstart module.

    :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import time
from io import StringIO
from unittest.mock import Mock

import pytest

from sphinx import application
from sphinx.cmd import quickstart as qs
from sphinx.util.console import coloron, nocolor

warnfile = StringIO()


def setup_module():
    nocolor()


def mock_input(answers, needanswer=False):
    called = set()

    def input_(prompt):
        if prompt in called:
            raise AssertionError('answer for %r missing and no default '
                                 'present' % prompt)
        called.add(prompt)
        for question in answers:
            if prompt.startswith(qs.PROMPT_PREFIX + question):
                return answers[question]
        if needanswer:
            raise AssertionError('answer for %r missing' % prompt)
        return ''
    return input_


real_input = input


def teardown_module():
    qs.term_input = real_input
    coloron()


def test_do_prompt():
    answers = {
        'Q2': 'v2',
        'Q3': 'v3',
        'Q4': 'yes',
        'Q5': 'no',
        'Q6': 'foo',
    }
    qs.term_input = mock_input(answers)

    assert qs.do_prompt('Q1', default='v1') == 'v1'
    assert qs.do_prompt('Q3', default='v3_default') == 'v3'
    assert qs.do_prompt('Q2') == 'v2'
    assert qs.do_prompt('Q4', validator=qs.boolean) is True
    assert qs.do_prompt('Q5', validator=qs.boolean) is False
    with pytest.raises(AssertionError):
        qs.do_prompt('Q6', validator=qs.boolean)


def test_do_prompt_inputstrip():
    answers = {
        'Q1': 'Y',
        'Q2': ' Yes ',
        'Q3': 'N',
        'Q4': 'N ',
    }
    qs.term_input = mock_input(answers)

    assert qs.do_prompt('Q1') == 'Y'
    assert qs.do_prompt('Q2') == 'Yes'
    assert qs.do_prompt('Q3') == 'N'
    assert qs.do_prompt('Q4') == 'N'


def test_do_prompt_with_nonascii():
    answers = {
        'Q1': '\u30c9\u30a4\u30c4',
    }
    qs.term_input = mock_input(answers)
    result = qs.do_prompt('Q1', default='\u65e5\u672c')
    assert result == '\u30c9\u30a4\u30c4'


def test_is_path_empty():
    assert qs.is_path('') == ''


def test_is_path_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert qs.is_path('.') == '.'
    assert qs.is_path(str(tmp_path)) == str(tmp_path)


def test_is_path_expands_home(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    (tmp_path / 'docs').mkdir()
    assert qs.is_path('~/docs') == str(tmp_path / 'docs')
    with pytest.raises(qs.ValidationError, match='^Please enter a valid path name[.]$'):
        qs.is_path('~/missing')
    assert not (tmp_path / 'missing').exists()


@pytest.mark.parametrize('default', ['', '.'])
@pytest.mark.parametrize('answer', ['', ' \t '])
def test_do_prompt_path_default(tmp_path, monkeypatch, capsys, default, answer):
    monkeypatch.chdir(tmp_path)
    input_ = Mock(side_effect=[answer])
    monkeypatch.setattr(qs, 'term_input', input_)

    assert qs.do_prompt('Root path', default, qs.is_path) == default
    assert input_.call_count == 1
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('cancel', [False, True])
def test_do_prompt_path_retry(tmp_path, monkeypatch, capsys, cancel):
    missing = tmp_path / 'missing'
    regular_file = tmp_path / 'file'
    regular_file.write_bytes(b'not a directory')
    for invalid in [missing, regular_file]:
        with pytest.raises(qs.ValidationError, match='^Please enter a valid path name[.]$'):
            qs.is_path(str(invalid))

    final_answer = '' if cancel else str(tmp_path)
    input_ = Mock(side_effect=[str(missing), str(regular_file), final_answer])
    monkeypatch.setattr(qs, 'term_input', input_)

    assert qs.do_prompt('Root path', '', qs.is_path) == final_answer
    assert input_.call_count == 3
    assert len({call[0][0] for call in input_.call_args_list}) == 1
    assert capsys.readouterr().out == '* Please enter a valid path name.\n' * 2
    assert not missing.exists()
    assert regular_file.read_bytes() == b'not a directory'


def snapshot_tree(root):
    return {str(filename.relative_to(root)): filename.read_bytes() if filename.is_file() else None
            for filename in root.rglob('*')}


@pytest.mark.parametrize('config_path', ['conf.py', 'source/conf.py'])
@pytest.mark.parametrize('supplied_root', [False, True])
@pytest.mark.parametrize('response', ['enter', 'whitespace', 'invalid', 'collision'])
def test_quickstart_existing_conf_cancel(tmp_path, monkeypatch, capsys,
                                         config_path, supplied_root, response):
    config = tmp_path / config_path
    config.parent.mkdir(exist_ok=True)
    config.write_bytes(b'# existing project\n')
    (tmp_path / 'index.rst').write_bytes(b'Existing documentation\n')
    answers = ['']
    if response == 'whitespace':
        answers = [' \t ']
    elif response == 'invalid':
        answers = [str(tmp_path / 'missing'), str(config), '']
    elif response == 'collision':
        other = tmp_path / 'other' / config_path
        other.parent.mkdir(parents=True)
        other.write_bytes(b'# another project\n')
        answers = [str(tmp_path / 'other'), '']
    expected = snapshot_tree(tmp_path)
    if not supplied_root:
        monkeypatch.chdir(tmp_path)
    input_ = Mock(side_effect=answers)
    monkeypatch.setattr(qs, 'term_input', input_)

    with pytest.raises(SystemExit) as exc:
        qs.main([str(tmp_path)] if supplied_root else [])

    assert exc.value.code == 1
    assert input_.call_count == len(answers)
    prompts = [call[0][0] for call in input_.call_args_list]
    assert all(prompt.startswith(qs.PROMPT_PREFIX + 'Please enter a new root path')
               for prompt in prompts)
    output = capsys.readouterr()
    assert output.out.count('Please enter a valid path name.') == (2 if response == 'invalid' else 0)
    assert output.out.count('an existing conf.py has been found') == (2 if response == 'collision' else 1)
    assert '[Interrupted.]' not in output.out
    assert output.err == ''
    assert snapshot_tree(tmp_path) == expected


@pytest.mark.parametrize('config_path', ['conf.py', 'source/conf.py'])
@pytest.mark.parametrize('invalid_first', [False, True])
def test_quickstart_valid_replacement(tmp_path, monkeypatch, capsys, config_path, invalid_first):
    original = tmp_path / 'original'
    config = original / config_path
    config.parent.mkdir(parents=True)
    config.write_bytes(b'# existing project\n')
    expected = snapshot_tree(original)
    replacement = tmp_path / 'replacement'
    replacement.mkdir()
    answers = [str(replacement), '', '']
    if invalid_first:
        answers[:0] = [str(tmp_path / 'missing'), str(config)]
    input_ = Mock(side_effect=answers)
    monkeypatch.setattr(qs, 'term_input', input_)

    assert qs.main(['-p', 'Test', '-a', 'Author', '-l', 'en', str(original)]) == 0

    assert input_.call_count == len(answers)
    output = capsys.readouterr()
    assert output.out.count('Please enter a valid path name.') == (2 if invalid_first else 0)
    assert output.err == ''
    assert snapshot_tree(original) == expected
    assert not (tmp_path / 'missing').exists()
    for filename in ['conf.py', 'index.rst', 'Makefile', 'make.bat']:
        assert (replacement / filename).is_file()
    for dirname in ['_static', '_templates']:
        assert (replacement / dirname).is_dir()


def test_quickstart_defaults(tempdir):
    answers = {
        'Root path': tempdir,
        'Project name': 'Sphinx Test',
        'Author name': 'Georg Brandl',
        'Project version': '0.1',
    }
    qs.term_input = mock_input(answers)
    d = {}
    qs.ask_user(d)
    qs.generate(d)

    conffile = tempdir / 'conf.py'
    assert conffile.isfile()
    ns = {}
    exec(conffile.read_text(), ns)
    assert ns['extensions'] == []
    assert ns['templates_path'] == ['_templates']
    assert ns['project'] == 'Sphinx Test'
    assert ns['copyright'] == '%s, Georg Brandl' % time.strftime('%Y')
    assert ns['version'] == '0.1'
    assert ns['release'] == '0.1'
    assert ns['html_static_path'] == ['_static']

    assert (tempdir / '_static').isdir()
    assert (tempdir / '_templates').isdir()
    assert (tempdir / 'index.rst').isfile()
    assert (tempdir / 'Makefile').isfile()
    assert (tempdir / 'make.bat').isfile()


def test_quickstart_all_answers(tempdir):
    answers = {
        'Root path': tempdir,
        'Separate source and build': 'y',
        'Name prefix for templates': '.',
        'Project name': 'STASI™',
        'Author name': 'Wolfgang Schäuble & G\'Beckstein',
        'Project version': '2.0',
        'Project release': '2.0.1',
        'Project language': 'de',
        'Source file suffix': '.txt',
        'Name of your master document': 'contents',
        'autodoc': 'y',
        'doctest': 'yes',
        'intersphinx': 'no',
        'todo': 'y',
        'coverage': 'no',
        'imgmath': 'N',
        'mathjax': 'no',
        'ifconfig': 'no',
        'viewcode': 'no',
        'githubpages': 'no',
        'Create Makefile': 'no',
        'Create Windows command file': 'no',
        'Do you want to use the epub builder': 'yes',
    }
    qs.term_input = mock_input(answers, needanswer=True)
    d = {}
    qs.ask_user(d)
    qs.generate(d)

    conffile = tempdir / 'source' / 'conf.py'
    assert conffile.isfile()
    ns = {}
    exec(conffile.read_text(), ns)
    assert ns['extensions'] == [
        'sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.todo'
    ]
    assert ns['templates_path'] == ['.templates']
    assert ns['source_suffix'] == '.txt'
    assert ns['root_doc'] == 'contents'
    assert ns['project'] == 'STASI™'
    assert ns['copyright'] == '%s, Wolfgang Schäuble & G\'Beckstein' % \
        time.strftime('%Y')
    assert ns['version'] == '2.0'
    assert ns['release'] == '2.0.1'
    assert ns['todo_include_todos'] is True
    assert ns['html_static_path'] == ['.static']

    assert (tempdir / 'build').isdir()
    assert (tempdir / 'source' / '.static').isdir()
    assert (tempdir / 'source' / '.templates').isdir()
    assert (tempdir / 'source' / 'contents.txt').isfile()


def test_generated_files_eol(tempdir):
    answers = {
        'Root path': tempdir,
        'Project name': 'Sphinx Test',
        'Author name': 'Georg Brandl',
        'Project version': '0.1',
    }
    qs.term_input = mock_input(answers)
    d = {}
    qs.ask_user(d)
    qs.generate(d)

    def assert_eol(filename, eol):
        content = filename.read_bytes().decode()
        assert all([l[-len(eol):] == eol for l in content.splitlines(True)])

    assert_eol(tempdir / 'make.bat', '\r\n')
    assert_eol(tempdir / 'Makefile', '\n')


def test_quickstart_and_build(tempdir):
    answers = {
        'Root path': tempdir,
        'Project name': 'Fullwidth characters: \u30c9\u30a4\u30c4',
        'Author name': 'Georg Brandl',
        'Project version': '0.1',
    }
    qs.term_input = mock_input(answers)
    d = {}
    qs.ask_user(d)
    qs.generate(d)

    app = application.Sphinx(
        tempdir,  # srcdir
        tempdir,  # confdir
        (tempdir / '_build' / 'html'),  # outdir
        (tempdir / '_build' / '.doctree'),  # doctreedir
        'html',  # buildername
        status=StringIO(),
        warning=warnfile)
    app.builder.build_all()
    warnings = warnfile.getvalue()
    assert not warnings


def test_default_filename(tempdir):
    answers = {
        'Root path': tempdir,
        'Project name': '\u30c9\u30a4\u30c4',  # Fullwidth characters only
        'Author name': 'Georg Brandl',
        'Project version': '0.1',
    }
    qs.term_input = mock_input(answers)
    d = {}
    qs.ask_user(d)
    qs.generate(d)

    conffile = tempdir / 'conf.py'
    assert conffile.isfile()
    ns = {}
    exec(conffile.read_text(), ns)


def test_extensions(tempdir):
    qs.main(['-q', '-p', 'project_name', '-a', 'author',
             '--extensions', 'foo,bar,baz', tempdir])

    conffile = tempdir / 'conf.py'
    assert conffile.isfile()
    ns = {}
    exec(conffile.read_text(), ns)
    assert ns['extensions'] == ['foo', 'bar', 'baz']
