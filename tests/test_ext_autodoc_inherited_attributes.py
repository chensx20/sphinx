"""
    test_ext_autodoc_inherited_attributes
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test source documentation for inherited attributes.

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import pytest

from sphinx.pycode import ModuleAnalyzer

from .test_ext_autodoc import do_autodoc, make_directive_bridge


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_inherited_attribute_members(app):
    actual = do_autodoc(app, 'class', 'target.inherited_attributes.Child',
                        {'members': None, 'inherited-members': None})
    for name, doc in [('data', 'Cross-module class data.'),
                      ('annotated', 'Cross-module annotated data.'),
                      ('instance', 'Cross-module constructor data.'),
                      ('local_data', 'Same-module class data.'),
                      ('local_instance', 'Same-module constructor data.'),
                      ('shared', 'Left documentation for the shared attribute.'),
                      ('own', 'Subclass documentation.')]:
        assert list(actual).count('   .. py:attribute:: Child.' + name) == 1
        assert '      ' + doc in actual
    assert '      :type: int' in actual
    assert '      :type: str' in actual
    assert '      :value: 10' in actual
    assert '      Inherited method documentation.' in actual
    assert '      Inherited property documentation.' in actual
    assert not any('Child._private' in line or 'Child.__special__' in line for line in actual)


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_inherited_attributes_disabled(app):
    actual = do_autodoc(app, 'class', 'target.inherited_attributes.Child', {'members': None})
    assert [line for line in actual if '.. py:attribute::' in line] == [
        '   .. py:attribute:: Child.own',
    ]


@pytest.mark.parametrize('options, included, excluded', [
    ({'inherited-members': 'Left'}, ['own'], ['local_data', 'local_instance', 'data']),
    ({'inherited-members': 'Base'}, ['own', 'local_data', 'local_instance', 'shared'],
     ['data', 'instance', 'annotated']),
    ({'inherited-members': None, 'exclude-members': 'data,instance'},
     ['annotated', 'local_data'], ['data', 'instance']),
    ({'inherited-members': None, 'private-members': '_private',
      'special-members': '__special__'}, ['_private', '__special__'], []),
    ({'inherited-members': 'Base', 'private-members': '_private',
      'special-members': '__special__'}, ['own'], ['_private', '__special__']),
])
@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_inherited_attribute_selection(app, options, included, excluded):
    actual = do_autodoc(app, 'class', 'target.inherited_attributes.Child',
                        dict(options, members=None))
    for name in included:
        assert '   .. py:attribute:: Child.' + name in actual
    for name in excluded:
        assert '   .. py:attribute:: Child.' + name not in actual


@pytest.mark.parametrize('inherit_docstrings', [True, False])
@pytest.mark.parametrize('cls, doc, value', [
    ('Child', 'Left documentation for the shared attribute.', 8),
    ('Override', 'Subclass documentation for the shared attribute.', 12),
    ('UndocumentedOverride', 'Left documentation for the shared attribute.', 13),
])
@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_inherited_attribute_direct(app, inherit_docstrings, cls, doc, value):
    app.config.autodoc_inherit_docstrings = inherit_docstrings
    actual = do_autodoc(app, 'attribute', 'target.inherited_attributes.' + cls + '.shared')
    assert list(actual) == [
        '', '.. py:attribute:: ' + cls + '.shared',
        '   :module: target.inherited_attributes', '   :value: ' + str(value),
        '', '   ' + doc, '',
    ]


@pytest.mark.parametrize('name, doc', [
    ('data', 'Cross-module class data.'),
    ('annotated', 'Cross-module annotated data.'),
    ('instance', 'Cross-module constructor data.'),
    ('local_instance', 'Same-module constructor data.'),
])
@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_inherited_attribute_callbacks_and_dependencies(app, name, doc):
    from target import inherited_attributes, inherited_attributes_base

    analyzer = ModuleAnalyzer.for_module('target.inherited_attributes_base')
    original = {key: list(lines) for key, lines in analyzer.find_attr_docs().items()}
    seen = []

    def process(app, what, fullname, obj, options, lines):
        seen.append((what, fullname, list(lines)))
        lines.append('Callback content.')

    app.connect('autodoc-process-docstring', process)
    for _ in range(2):
        bridge = make_directive_bridge(app.env)
        documenter = app.registry.documenters['attribute'](
            bridge, 'target.inherited_attributes.Child.' + name)
        documenter.generate()
        assert '   ' + doc in bridge.result
        assert list(bridge.result).count('   Callback content.') == 1
        assert inherited_attributes.__file__ in bridge.filename_set
        if name != 'local_instance':
            assert inherited_attributes_base.__file__ in bridge.filename_set
    assert len(seen) == 2
    assert all(what == 'attribute' and fullname.endswith('Child.' + name)
               for what, fullname, lines in seen)
    assert seen[0][2] == seen[1][2]
    assert analyzer.attr_docs == original
    assert not any(ns == 'Child' for ns, name in analyzer.attr_docs)


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_inherited_attribute_explicit_member_and_skip_event(app):
    def skip(app, what, name, obj, skipped, options):
        if name == 'data':
            assert not skipped
            return True

    actual = do_autodoc(app, 'class', 'target.inherited_attributes.Child',
                        {'members': 'instance'})
    assert '   .. py:attribute:: Child.instance' in actual
    app.connect('autodoc-skip-member', skip)
    actual = do_autodoc(app, 'class', 'target.inherited_attributes.Child',
                        {'members': None, 'inherited-members': None})
    assert '   .. py:attribute:: Child.data' not in actual


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_inherited_attribute_module_data(app):
    actual = do_autodoc(app, 'data', 'target.inherited_attributes_base.module_data')
    assert list(actual) == [
        '', '.. py:data:: module_data', '   :module: target.inherited_attributes_base',
        '   :value: 7', '', '   Module data documentation.', '',
    ]


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_inherited_attribute_descriptor(app):
    actual = do_autodoc(app, 'class', 'target.inherited_attributes.DescriptorChild',
                        {'members': None, 'inherited-members': None})
    assert '   .. py:attribute:: DescriptorChild.descr' in actual
    assert '      Descriptor instance docstring.' in actual
    assert not any(':value:' in line for line in actual)
    assert '   .. py:method:: DescriptorChild.prop' in actual
    assert '      Property.' in actual
