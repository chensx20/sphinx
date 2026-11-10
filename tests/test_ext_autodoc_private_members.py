"""
    test_ext_autodoc_private_members
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test the autodoc extension.  This tests mainly for private-members option.

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

import pytest
from test_ext_autodoc import do_autodoc

from sphinx import addnodes
from sphinx.ext.autodoc import ALL, ClassDocumenter, ExceptionDocumenter, ModuleDocumenter
from sphinx.testing import restructuredtext


def member_names(lines):
    return re.findall(r'^\s*\.\. py:(?:function|method|attribute):: ([^(\s]+)',
                      '\n'.join(lines), re.MULTILINE)


@pytest.mark.parametrize('documenter', [
    ModuleDocumenter, ClassDocumenter, ExceptionDocumenter,
])
@pytest.mark.parametrize('value, expected', [
    (None, ALL),
    (True, ALL),
    (' _first, , _second, _first, ', ['_first', '_second', '_first']),
    ('_first', ['_first']),
    ('', []),
    (' , , ', []),
])
def test_private_members_conversion(documenter, value, expected):
    assert documenter.option_spec['private-members'](value) == expected


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('objtype, suffix, prefix', [
    ('module', '', ''),
    ('class', '.Sample', 'Sample.'),
    ('exception', '.Problem', 'Problem.'),
])
@pytest.mark.parametrize('selection, expected', [
    ('_first', ['_first']),
    (' _second, , _first, _first, ', ['_first', '_second']),
    ('', []),
    (' , ', []),
    ('missing', []),
])
def test_private_members_selection(app, objtype, suffix, prefix, selection, expected):
    actual = member_names(do_autodoc(app, objtype, 'target.private_selection' + suffix,
                                     {'members': None, 'private-members': selection}))
    assert prefix + 'public' in actual
    assert [name for name in actual if name in (prefix + '_first', prefix + '_second')] == [
        prefix + name for name in expected
    ]
    assert prefix + '_undocumented' not in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_private_members_attributes(app):
    actual = member_names(do_autodoc(app, 'class', 'target.private_selection.Sample', {
        'members': None, 'private-members': '_class_attr, _instance_attr',
    }))
    assert actual == ['Sample._class_attr', 'Sample._instance_attr',
                      'Sample._visible', 'Sample.public']
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('objtype, suffix, prefix', [
    ('module', '', ''), ('class', '.Sample', 'Sample.'),
])
@pytest.mark.parametrize('undoc', [False, True])
def test_private_members_undocumented(app, objtype, suffix, prefix, undoc):
    options = {'members': None, 'private-members': '_undocumented, _undoc_attr'}
    if undoc:
        options['undoc-members'] = None
    actual = member_names(do_autodoc(app, objtype, 'target.private_selection' + suffix,
                                     options))
    assert (prefix + '_undocumented' in actual) is undoc
    if objtype == 'class':
        assert ('Sample._undoc_attr' in actual) is undoc
    assert prefix + '_first' not in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('objtype, suffix, prefix', [
    ('module', '', ''), ('class', '.Sample', 'Sample.'),
])
@pytest.mark.parametrize('selection', ['', 'hidden'])
def test_private_members_metadata(app, objtype, suffix, prefix, selection):
    actual = member_names(do_autodoc(app, objtype, 'target.private_selection' + suffix,
                                     {'members': None, 'private-members': selection}))
    assert (prefix + 'hidden' in actual) is (selection == 'hidden')
    assert prefix + '_visible' in actual
    assert prefix + '_first' not in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('selection', [None, True])
def test_private_members_bare_recursive(app, selection):
    actual = member_names(do_autodoc(app, 'module', 'target.private_selection',
                                     {'members': None, 'private-members': selection}))
    for prefix in ('', 'Sample.', 'Problem.'):
        assert prefix + '_first' in actual
        assert prefix + '_second' in actual
    assert 'Sample._class_attr' in actual
    assert 'Sample._instance_attr' in actual
    assert '_undocumented' not in actual
    assert 'Sample.__special__' not in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_private_members_recursive_selection(app):
    actual = member_names(do_autodoc(app, 'module', 'target.private_selection',
                                     {'members': None, 'private-members': '_first'}))
    for prefix in ('', 'Sample.', 'Problem.'):
        assert prefix + '_first' in actual
        assert prefix + '_second' not in actual
        assert prefix + 'public' in actual
    assert 'Sample._class_attr' not in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('objtype, suffix, prefix', [
    ('module', '', ''), ('class', '.Sample', 'Sample.'),
    ('exception', '.Problem', 'Problem.'),
])
def test_private_members_discovery(app, objtype, suffix, prefix):
    target = 'target.private_selection' + suffix
    assert member_names(do_autodoc(app, objtype, target, {'private-members': '_first'})) == []
    actual = member_names(do_autodoc(app, objtype, target,
                                     {'members': '_second', 'private-members': '_first'}))
    assert actual == [prefix + '_second']
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('ignore_all', [False, True])
def test_private_members_exports(app, monkeypatch, ignore_all):
    from target import private_selection

    monkeypatch.setattr(private_selection, '__all__', ['public', '_second'], raising=False)
    options = {'members': None, 'private-members': '_first'}
    if ignore_all:
        options['ignore-module-all'] = None
    actual = member_names(do_autodoc(app, 'module', 'target.private_selection', options))
    assert ('_first' in actual) is ignore_all
    assert '_second' not in actual
    assert 'public' in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('imported', [False, True])
def test_private_members_imports(app, imported):
    options = {'members': None, 'private-members': '_imported'}
    if imported:
        options['imported-members'] = None
    actual = member_names(do_autodoc(app, 'module', 'target.private_selection', options))
    assert ('_imported' in actual) is imported
    assert '_first' not in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('inherited', [False, True])
def test_private_members_inheritance(app, inherited):
    options = {'members': None, 'private-members': '_inherited'}
    if inherited:
        options['inherited-members'] = None
    actual = member_names(do_autodoc(app, 'class', 'target.private_selection.Sample', options))
    assert ('Sample._inherited' in actual) is inherited
    assert ('Sample.inherited' in actual) is inherited
    assert 'Sample._first' not in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('special', [False, True])
def test_private_members_exclusions_and_special(app, special):
    options = {'members': None, 'private-members': '_first, _second, __special__',
               'exclude-members': '_first'}
    if special:
        options['special-members'] = '__special__'
    actual = member_names(do_autodoc(app, 'class', 'target.private_selection.Sample', options))
    assert 'Sample._first' not in actual
    assert 'Sample._second' in actual
    assert ('Sample.__special__' in actual) is special
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('order, expected', [
    ('alphabetical', ['Sample._first', 'Sample._second', 'Sample._visible', 'Sample.public']),
    ('bysource', ['Sample.public', 'Sample._second', 'Sample._first', 'Sample._visible']),
])
def test_private_members_order(app, order, expected):
    actual = member_names(do_autodoc(app, 'class', 'target.private_selection.Sample', {
        'members': None, 'private-members': '_first, _second', 'member-order': order,
    }))
    assert actual == expected
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_private_members_local_name(app):
    actual = member_names(do_autodoc(app, 'class', 'target.private_selection.Sample',
                                     {'members': None, 'private-members': '__local'}))
    assert 'Sample.__local' in actual
    assert 'Sample._first' not in actual
    assert 'Sample._Sample__local' not in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('options, first_skip, other_skip', [
    ({}, True, True),
    ({'private-members': None}, False, False),
    ({'private-members': True}, False, False),
    ({'private-members': ''}, True, True),
    ({'private-members': '_first, _class_attr'}, False, True),
])
def test_private_members_skip_event(app, options, first_skip, other_skip):
    decisions = {}

    def skip_member(app, what, name, obj, skip, options):
        assert type(skip) is bool
        decisions[name] = skip
        if name == '_first':
            return True
        if name == '_second':
            return False

    app.connect('autodoc-skip-member', skip_member)
    options.update({'members': None, 'exclude-members': '_second'})
    actual = member_names(do_autodoc(app, 'class', 'target.private_selection.Sample', options))
    assert decisions['_first'] is first_skip
    assert decisions['_second'] is True
    assert decisions['_class_attr'] is first_skip
    assert decisions['_other_class_attr'] is other_skip
    assert 'Sample._first' not in actual
    assert 'Sample._second' in actual
    assert ('Sample._class_attr' in actual) is (not first_skip)
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('default, options, expected', [
    ('_first', {}, ['_first']),
    (None, {}, ['_first', '_second']),
    (True, {}, ['_first', '_second']),
    ('', {}, []),
    ('_first', {'no-private-members': None}, []),
    ('_first', {'private-members': '_second'}, ['_first']),
    ('_first', {'no-private-members': None, 'private-members': '_second'}, ['_second']),
])
def test_private_members_default_options(app, default, options, expected):
    app.config.autodoc_default_options = {'members': None, 'private-members': default}
    actual = member_names(do_autodoc(app, 'module', 'target.private_selection', options))
    assert [name for name in actual if name in ('_first', '_second')] == expected
    assert 'public' in actual
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
@pytest.mark.parametrize('directive, suffix, prefix', [
    ('automodule', '', ''), ('autoclass', '.Sample', 'Sample.'),
    ('autoexception', '.Problem', 'Problem.'),
])
@pytest.mark.parametrize('selection', ['', ' _first, , _first'])
def test_private_members_rst(app, directive, suffix, prefix, selection):
    source = '\n'.join([
        '.. %s:: target.private_selection%s' % (directive, suffix),
        '   :members:', '   :private-members:%s' % selection, '',
    ])
    doctree = restructuredtext.parse(app, source)
    signatures = [node['fullname'] for node in doctree.traverse(addnodes.desc_signature)]
    assert prefix + '_first' in signatures
    assert (prefix + '_second' in signatures) is (selection == '')
    assert prefix + 'public' in signatures
    assert app._warning.getvalue() == ''


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_private_field(app):
    app.config.autoclass_content = 'class'
    options = {"members": None}
    actual = do_autodoc(app, 'module', 'target.private', options)
    assert list(actual) == [
        '',
        '.. py:module:: target.private',
        '',
        '',
        '.. py:function:: _public_function(name)',
        '   :module: target.private',
        '',
        '   public_function is a docstring().',
        '',
        '   :meta public:',
        '',
    ]


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_private_field_and_private_members(app):
    app.config.autoclass_content = 'class'
    options = {"members": None,
               "private-members": None}
    actual = do_autodoc(app, 'module', 'target.private', options)
    assert list(actual) == [
        '',
        '.. py:module:: target.private',
        '',
        '',
        '.. py:function:: _public_function(name)',
        '   :module: target.private',
        '',
        '   public_function is a docstring().',
        '',
        '   :meta public:',
        '',
        '',
        '.. py:function:: private_function(name)',
        '   :module: target.private',
        '',
        '   private_function is a docstring().',
        '',
        '   :meta private:',
        '',
    ]
