from datetime import datetime
from time import sleep

from pylons import c
import re
import markdown

import pymongo
from pymongo.errors import OperationFailure

from ming import schema as S
from ming import Field

from pyforge.model import VersionedArtifact, Snapshot, Message

wikiwords = [
    (r'\b([A-Z]\w+[A-Z]+\w+)', r'<a href="../\1/">\1</a>'),
    (r'([^\\])\[(.*)\]', r'\1<a href="../\2/">\2</a>'),
    (r'\\\[(.*)\]', r'[\1]'),
    (r'^\[(.*)\]', r'<a href="../\1/">\1</a>'),
    ]
wikiwords = [
    (re.compile(pattern), replacement)
    for pattern, replacement in wikiwords ]

class PageHistory(Snapshot):
    class __mongometa__:
        name='page_history'

    def original(self):
        return Page.m.get(_id=self.artifact_id)
        
    def url(self):
        return self.original().url() + '?version=%d' % self.version

    def index(self):
        result = Snapshot.index(self)
        result.update(
            title_s='Version %d of %s' % (
                self.version,self.original().title),
            type_s='WikiPage Snapshot',
            text=self.data.text)
        return result

class Page(VersionedArtifact):
    class __mongometa__:
        name='page'
        history_class = PageHistory

    title=Field(str)
    text=Field(S.String, if_missing='')

    def url(self):
        return c.app.script_name + '/' + self.title + '/'

    def index(self):
        result = VersionedArtifact.index(self)
        result.update(
            title_s=self.title,
            version_i=self.version,
            type_s='WikiPage',
            text=self.text)
        return result

    @classmethod
    def upsert(cls, title, version=None):
        if version is None:
            q = dict(
                project_id=c.project._id,
                title=title)
            obj = cls.m.get(
                app_config_id=c.app.config._id,
                title=title)
            if obj is None:
                obj = cls.make(dict(title=title))
            new_obj = dict(obj, version=obj.version + 1)
            return cls.make(new_obj)
        else:
            HC = cls.__mongometa__.history_class
            ss = HC.m.find({'data.title':title, 'version':int(version)}).one()
            new_obj = dict(ss.data, version=version + 1)
            return cls.make(new_obj)

    @property
    def html_text(self):
        md = markdown.Markdown(
            extensions=['codehilite'],
            output_format='html4'
        )
        content = md.convert(self.text)
        for pattern, replacement in wikiwords:
            content = pattern.sub(replacement, content)
        return content

    def reply(self):
        while True:
            try:
                c = Comment.make(dict(page_title=self.title))
                c.m.insert()
                return c
            except OperationFailure:
                sleep(0.1)
                continue

    def root_comments(self):
        return Comment.m.find(dict(page_title=self.title, parent_id=None))

class Comment(Message):
    class __mongometa__:
        name='comment'
    page_title=Field(str)

    def index(self):
        result = Message.index(self)
        author = self.author()
        result.update(
            title_s='Comment on page %s by %s' % (
                self.page_title, author.display_name),
            type_s='Comment on WikiPage',
            page_title_t=self.page_title)
        return result

    @property
    def page(self):
        versions = Page.m.find(dict(title=self.page_title)).all()
        pg = max(versions, key=lambda p:p.version)
        return pg

    def url(self):
        return self.page.url() + '#comment-' + self._id

    
