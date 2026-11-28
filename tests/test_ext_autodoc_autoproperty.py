"""
    test_ext_autodoc_autoproperty
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test the autodoc extension.  This tests mainly the Documenters; the auto
    directives are tested in a test source file translated by test_build.

    :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys

import pytest

from sphinx.ext.autodoc.importer import get_class_members
from sphinx.util.inspect import safe_getattr

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


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_classmethod_property(app):
    actual = do_autodoc(app, 'property', 'target.classmethod_property.Concrete.prop')
    assert list(actual) == [
        '',
        '.. py:property:: Concrete.prop',
        '   :module: target.classmethod_property',
        '   :classmethod:',
        '   :type: int',
        '',
        '   concrete property',
        '',
    ]


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_abstract_classmethod_property(app):
    actual = do_autodoc(app, 'property', 'target.classmethod_property.Abstract.prop')
    assert list(actual) == [
        '',
        '.. py:property:: Abstract.prop',
        '   :module: target.classmethod_property',
        '   :classmethod:',
        '   :abstractmethod:',
        '   :type: int',
        '',
        '   abstract property',
        '',
    ]


@pytest.mark.skipif(sys.version_info < (3, 8),
                    reason='cached_property is available since python3.8.')
@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_classmethod_cached_property(app):
    actual = do_autodoc(app, 'property', 'target.classmethod_property.Cached.prop')
    assert list(actual) == [
        '',
        '.. py:property:: Cached.prop',
        '   :module: target.classmethod_property',
        '   :classmethod:',
        '',
        '   cached property',
        '',
    ]


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_classmethod_property_member(app):
    from target.classmethod_property import Concrete

    members = get_class_members(Concrete, [], safe_getattr)
    assert isinstance(members['prop'].object, classmethod)

    if sys.version_info >= (3, 8):
        from target.classmethod_property import Cached

        members = get_class_members(Cached, [], safe_getattr)
        assert isinstance(members['prop'].object, classmethod)
