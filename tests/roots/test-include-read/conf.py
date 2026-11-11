extensions = ['sphinx.ext.duration']


def source_read(app, docname, source):
    source[0] = source[0].replace('&REPLACE_ME;', 'REPLACED')


def include_read(app, relative_path, parent_docname, content):
    source_read(app, parent_docname, content)


def setup(app):
    app.connect('source-read', source_read)
    app.connect('include-read', include_read)
