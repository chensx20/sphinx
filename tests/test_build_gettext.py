"""Test the build process with gettext builder with the test root."""

import gettext
import os
import re
import subprocess
from subprocess import PIPE, CalledProcessError

import pytest

from sphinx.builders.gettext import Catalog, MsgOrigin
from sphinx.util.osutil import cd


def test_catalog_locations():
    catalog = Catalog()
    assert list(catalog) == []

    origins = [MsgOrigin('z.rst', 0), MsgOrigin('a.rst', 12),
               MsgOrigin('z.rst', 0), MsgOrigin('z.rst', 4),
               MsgOrigin('a.rst', 0)]
    origins.append(origins[0])
    for origin in origins:
        catalog.add('Type', origin)
    catalog.add('Another message', origins[0])
    metadata = {text: list(occurrences) for text, occurrences in catalog.metadata.items()}

    for _ in range(2):
        messages = list(catalog)
        assert [message.text for message in messages] == ['Type', 'Another message']
        assert messages[0].locations == [('z.rst', 0), ('a.rst', 12),
                                         ('z.rst', 4), ('a.rst', 0)]
        assert messages[0].uuids == [origin.uid for origin in origins]
        assert messages[1].locations == [('z.rst', 0)]
        assert messages[1].uuids == [origins[0].uid]
        assert catalog.metadata == metadata
        assert catalog.messages == ['Type', 'Another message']


@pytest.mark.sphinx('gettext', srcdir='root-gettext')
def test_build_gettext(app):
    # Generic build; should fail only when the builder is horribly broken.
    app.builder.build_all()

    # Do messages end up in the correct location?
    # top-level documents end up in a message catalog
    assert (app.outdir / 'extapi.pot').isfile()
    # directory items are grouped into sections
    assert (app.outdir / 'subdir.pot').isfile()

    # regression test for issue #960
    catalog = (app.outdir / 'markup.pot').read_text(encoding='utf8')
    assert 'msgid "something, something else, something more"' in catalog


@pytest.mark.sphinx('gettext', srcdir='root-gettext')
def test_msgfmt(app):
    app.builder.build_all()
    (app.outdir / 'en' / 'LC_MESSAGES').makedirs()
    with cd(app.outdir):
        try:
            args = ['msginit', '--no-translator', '-i', 'markup.pot', '--locale', 'en_US']
            subprocess.run(args, stdout=PIPE, stderr=PIPE, check=True)
        except OSError:
            pytest.skip()  # most likely msginit was not found
        except CalledProcessError as exc:
            print(exc.stdout)
            print(exc.stderr)
            assert False, 'msginit exited with return code %s' % exc.returncode

        assert (app.outdir / 'en_US.po').isfile(), 'msginit failed'
        try:
            args = ['msgfmt', 'en_US.po',
                    '-o', os.path.join('en', 'LC_MESSAGES', 'test_root.mo')]
            subprocess.run(args, stdout=PIPE, stderr=PIPE, check=True)
        except OSError:
            pytest.skip()  # most likely msgfmt was not found
        except CalledProcessError as exc:
            print(exc.stdout)
            print(exc.stderr)
            assert False, 'msgfmt exited with return code %s' % exc.returncode

        mo = app.outdir / 'en' / 'LC_MESSAGES' / 'test_root.mo'
        assert mo.isfile(), 'msgfmt failed'

    _ = gettext.translation('test_root', app.outdir, languages=['en']).gettext
    assert _("Testing various markup") == "Testing various markup"


@pytest.mark.sphinx(
    'gettext', testroot='intl', srcdir='gettext',
    confoverrides={'gettext_compact': False})
def test_gettext_index_entries(app):
    # regression test for #976
    app.builder.build(['index_entries'])

    _msgid_getter = re.compile(r'msgid "(.*)"').search

    def msgid_getter(msgid):
        m = _msgid_getter(msgid)
        if m:
            return m.groups()[0]
        return None

    pot = (app.outdir / 'index_entries.pot').read_text(encoding='utf8')
    msgids = [_f for _f in map(msgid_getter, pot.splitlines()) if _f]

    expected_msgids = [
        "i18n with index entries",
        "index target section",
        "this is :index:`Newsletter` target paragraph.",
        "various index entries",
        "That's all.",
        "Mailing List",
        "Newsletter",
        "Recipients List",
        "First",
        "Second",
        "Third",
        "Entry",
        "See",
        "Module",
        "Keyword",
        "Operator",
        "Object",
        "Exception",
        "Statement",
        "Builtin",
    ]
    for expect in expected_msgids:
        assert expect in msgids
        msgids.remove(expect)

    # unexpected msgid existent
    assert msgids == []


@pytest.mark.sphinx(
    'gettext', testroot='intl', srcdir='gettext',
    confoverrides={'gettext_compact': False,
                   'gettext_additional_targets': []})
def test_gettext_disable_index_entries(app):
    # regression test for #976
    app.builder.build(['index_entries'])

    _msgid_getter = re.compile(r'msgid "(.*)"').search

    def msgid_getter(msgid):
        m = _msgid_getter(msgid)
        if m:
            return m.groups()[0]
        return None

    pot = (app.outdir / 'index_entries.pot').read_text(encoding='utf8')
    msgids = [_f for _f in map(msgid_getter, pot.splitlines()) if _f]

    expected_msgids = [
        "i18n with index entries",
        "index target section",
        "this is :index:`Newsletter` target paragraph.",
        "various index entries",
        "That's all.",
    ]
    for expect in expected_msgids:
        assert expect in msgids
        msgids.remove(expect)

    # unexpected msgid existent
    assert msgids == []


@pytest.mark.sphinx('gettext', testroot='intl', srcdir='gettext')
def test_gettext_template(app):
    app.builder.build_all()
    assert (app.outdir / 'sphinx.pot').isfile()

    result = (app.outdir / 'sphinx.pot').read_text(encoding='utf8')
    assert "Welcome" in result
    assert "Sphinx %(version)s" in result


@pytest.mark.sphinx('gettext', testroot='gettext-template')
def test_gettext_template_msgid_order_in_sphinxpot(app):
    app.builder.build_all()
    assert (app.outdir / 'sphinx.pot').isfile()

    result = (app.outdir / 'sphinx.pot').read_text(encoding='utf8')
    assert re.search(
        ('msgid "Template 1".*'
         'msgid "This is Template 1\\.".*'
         'msgid "Template 2".*'
         'msgid "This is Template 2\\.".*'),
        result,
        flags=re.S)


@pytest.mark.parametrize('gettext_location', [True, False])
@pytest.mark.parametrize('gettext_uuid', [True, False])
@pytest.mark.sphinx('gettext', testroot='gettext-template',
                    srcdir='gettext-template-duplicate-locations')
def test_gettext_template_duplicate_locations(
        app_params, make_app, gettext_location, gettext_uuid):
    args, kwargs = app_params
    kwargs['confoverrides'] = {'gettext_location': gettext_location,
                               'gettext_uuid': gettext_uuid}
    template = kwargs['srcdir'] / '_templates' / 'template1.html'
    template.write_text("{{ _('Type') }} {{ _('Type') }}\n{{ _('Type') }}\n",
                        encoding='utf8')
    app = make_app(*args, **kwargs)
    app.builder.build_all()

    pot = (app.outdir / 'sphinx.pot').read_text(encoding='utf8')
    assert pot.count('msgid "Type"') == 1
    entry = next(entry for entry in pot.split('\n\n') if 'msgid "Type"' in entry)
    references = [line for line in entry.splitlines() if line.startswith('#: ')]
    occurrences = app.builder.catalogs['sphinx'].metadata['Type']
    assert [(source, line) for source, line, uid in occurrences] == [
        (str(template), 1), (str(template), 1), (str(template), 2)]
    uuids = [uid for source, line, uid in occurrences]
    assert len(set(uuids)) == 3
    expected = []
    if gettext_location:
        expected.extend(['#: ../../_templates/template1.html:1',
                         '#: ../../_templates/template1.html:2'])
    if gettext_uuid:
        expected.extend('#: ' + uid for uid in uuids)
    assert references == expected


@pytest.mark.sphinx(
    'gettext', srcdir='root-gettext',
    confoverrides={'gettext_compact': 'documentation'})
def test_build_single_pot(app):
    app.builder.build_all()

    assert (app.outdir / 'documentation.pot').isfile()

    result = (app.outdir / 'documentation.pot').read_text(encoding='utf8')
    assert re.search(
        ('msgid "Todo".*'
         'msgid "Like footnotes.".*'
         'msgid "The minute.".*'
         'msgid "Generated section".*'),
        result,
        flags=re.S)
