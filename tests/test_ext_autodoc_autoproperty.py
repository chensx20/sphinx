"""
    test_ext_autodoc_autoproperty
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test the autodoc extension.  This tests mainly the Documenters; the auto
    directives are tested in a test source file translated by test_build.

    :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import pytest

from .test_ext_autodoc import do_autodoc


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_properties(app):
    actual = do_autodoc(app, 'property', 'target.properties.Foo.prop')
    assert list(actual) == [
        '',
        '.. py:property:: Foo.prop',
        '   :module: target.properties',
        '   :type: int',
        '',
        '   docstring',
        '',
    ]


@pytest.mark.parametrize('classname,summary,types', [
    ('ClassProperties', 'concrete', ('int', 'str')),
    ('InheritedProperties', 'concrete', ('int', 'str')),
    ('SubclassProperties', 'overridden', ('float', 'bytes')),
    ('MetaProperties', 'metaclass', ('int', 'str')),
    ('InheritedMetaProperties', 'metaclass', ('int', 'str')),
    ('WithMetaProperties', 'metaclass', ('int', 'str')),
])
@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_class_properties(app, classname, summary, types):
    from target import properties

    properties.getter_calls.clear()
    for name, typ in zip(('concrete', 'abstract'), types):
        actual = list(do_autodoc(app, 'property',
                                 'target.properties.%s.%s' % (classname, name)))
        assert '.. py:property:: %s.%s' % (classname, name) in actual[1]
        assert '   :classmethod:' in actual
        assert '   :type: ' + typ in actual
        assert ('   :abstractmethod:' in actual) == (name == 'abstract')
        assert any('descriptor summary.' in line for line in actual)
        assert not any('(cls' in line or '%s()' % name in line for line in actual)
    actual = list(do_autodoc(app, 'property',
                             'target.properties.%s.concrete' % classname))
    assert '   The %s descriptor summary.' % summary in actual
    assert properties.getter_calls == []
    assert app._warning.getvalue() == ''


@pytest.mark.parametrize('typehints', ['signature', 'description', 'both', 'none'])
@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_class_property_typehints(app, typehints):
    app.config.autodoc_typehints = typehints
    actual = list(do_autodoc(app, 'property', 'target.properties.ClassProperties.concrete'))
    assert ('   :type: int' in actual) == (typehints != 'none')
    assert '   The concrete descriptor summary.' in actual


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_class_property_docstring_signature(app, monkeypatch):
    from target import properties

    prop = properties.ClassProperties.__dict__['concrete'].__func__
    monkeypatch.setattr(prop, '__doc__', 'concrete(cls)\n\nThe descriptor summary.')
    actual = list(do_autodoc(app, 'property', 'target.properties.ClassProperties.concrete'))
    assert actual[1] == '.. py:property:: ClassProperties.concrete'
    assert '   The descriptor summary.' in actual
    assert not any('(cls)' in line for line in actual)
