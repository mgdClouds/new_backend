#!/usr/bin/env python
# coding=utf-8
import datetime
import re

from flask_login import current_user
from marshmallow import Schema, fields, post_load
from sqlalchemy import not_

from ..extention import db


class BaseStatus(object):
  @classmethod
  def int2str(cls, v):
    ss = filter(lambda x: not x[0] == "_", cls.__dict__.keys())
    for s in ss:
      if cls.__dict__[s] == v:
        return s

  @classmethod
  def str2int(cls, v):
    return cls.__dict__[v]


class Base(db.Model):
  __abstract__ = True

  id = db.Column(db.Integer, primary_key=True)
  created = db.Column(db.DateTime, default=datetime.datetime.now)
  updated = db.Column(db.DateTime)

  def update(self, **kwargs):
    # self.updated = datetime.datetime.utcnow()
    self.updated = datetime.datetime.now()
    try:
      for key in kwargs:
        setattr(self, key, kwargs[key])
      db.session.add(self)
      db.session.flush()
    except Exception as e:
      db.session.rollback()
      raise e

  def update_from(self, source, *keys):
    for key in keys:
      setattr(self, key, getattr(source, key))
    self.save()

  def save(self):
    try:
      # self.updated = datetime.datetime.utcnow()
      self.updated = datetime.datetime.now()
      db.session.add(self)
      db.session.flush()
    except Exception as e:
      db.session.rollback()
      raise e

  @classmethod
  def find_or_create(cls, **kwargs):
    model = cls.query.filter_by(**kwargs).first()
    if not model:
      model = cls(**kwargs)
    return model

  def _before_delete(self):
    return True

  def delete(self):
    try:
      if not self._before_delete():
        raise Exception("删除条件未满足")
      db.session.delete(self)
      db.session.flush()
    except Exception as e:
      db.session.rollback()
      raise e

  @classmethod
  def _not(cls, query, **kwargs):
    """
    kwargs like _not_id=3
    :param query:
    :param kwargs:
    :return:
    """
    hit = []
    for key in kwargs:
      if not key[:4] == "not_":
        continue
      pure_key = key[4:]
      query = query.filter(not_(eval("cls.{}".format(pure_key)) == kwargs[key]))
      hit.append(key)
    for h in hit:
      kwargs.pop(h)
    return query, kwargs

  @classmethod
  def _eq(cls, query, **kwargs):
    """
    kwargs like a=1&b=2
    :param query:
    :param kwargs:
    :return:
    """
    for key in kwargs:
      # if hasattr(cls, key) and eval('cls.{}'.format(key)) is not Column:
      query = query.filter(eval("cls.{}".format(key)) == kwargs[key])

    return query, kwargs

  @classmethod
  def _gte(cls, query, **kwargs):
    """
    url example:_gt_id=3
    :param query:
    :param kwargs:
    :return:
    """
    hit = []
    for key in kwargs:
      if not key[:4] == "gte_":
        continue
      pure_key = key[4:]
      query = query.filter(eval("cls.{}".format(pure_key)) >= kwargs[key])
      hit.append(key)
    for h in hit:
      kwargs.pop(h)
    return query, kwargs

  @classmethod
  def _gt(cls, query, **kwargs):
    """
    url example:_gt_id=3
    :param query:
    :param kwargs:
    :return:
    """
    hit = []
    for key in kwargs:
      if not key[:3] == "gt_":
        continue
      pure_key = key[3:]
      query = query.filter(eval("cls.{}".format(pure_key)) > kwargs[key])
      hit.append(key)
    for h in hit:
      kwargs.pop(h)
    return query, kwargs

  @classmethod
  def _lt(cls, query, **kwargs):
    hit = []
    for key in kwargs:
      if not key[:3] == "lt_":
        continue
      pure_key = key[3:]
      query = query.filter(eval("cls.{}".format(pure_key)) < kwargs[key])
      hit.append(key)
    for h in hit:
      kwargs.pop(h)
    return query, kwargs

  @classmethod
  def _lte(cls, query, **kwargs):
    """
    url example:_lte_id=3
    :param query:
    :param kwargs:
    :return:
    """
    hit = []
    for key in kwargs:
      if not key[:4] == "lte_":
        continue
      pure_key = key[4:]
      query = query.filter(eval("cls.{}".format(pure_key)) <= kwargs[key])
      hit.append(key)
    for h in hit:
      kwargs.pop(h)
    return query, kwargs

  @classmethod
  def _in(cls, query, **kwargs):
    hit = []
    for key in kwargs:
      if not key[:3] == "in_":
        continue
      pure_key = key[3:]
      query = query.filter(eval("cls.{}.in_({})".format(pure_key, kwargs[key])))
      hit.append(key)
    for h in hit:
      kwargs.pop(h)
    return query, kwargs

  @classmethod
  def _like(cls, query, **kwargs):
    hit = []
    for key in kwargs:
      if not key[:5] == "like_":
        continue
      pure_key = key[5:]
      query = query.filter(
        eval('cls.{}.like("%{}%")'.format(pure_key, kwargs[key]))
      )
      hit.append(key)
    for h in hit:
      kwargs.pop(h)
    return query, kwargs

  @classmethod
  def _sort(cls, query, **kwargs):
    hit = []
    for key in kwargs:
      if not key[:5] == "sort_":
        continue
      pure_key = key[5:]
      if kwargs[key] == "1":
        query = query.order_by(eval("cls.{}".format(pure_key)))
      else:
        query = query.order_by(db.desc(eval("cls.{}".format(pure_key))))
      hit.append(key)
    for h in hit:
      kwargs.pop(h)
    return query, kwargs

  @classmethod
  def _paginate(cls, query, page, per_page):
    query = query.filter().limit(per_page).offset((page - 1) * per_page)
    return query

  @classmethod
  def get_items(cls, **kwargs):
    for key in kwargs:
      if isinstance(kwargs[key], list):
        kwargs[key] = kwargs[key][0]

    page = int(kwargs.pop("page", 1))
    per_page = int(kwargs.pop("per_page", 100))
    query = cls.query
    query, kwargs = cls._sort(query, **kwargs)
    query, kwargs = cls._gte(query, **kwargs)
    query, kwargs = cls._gt(query, **kwargs)
    query, kwargs = cls._lt(query, **kwargs)
    query, kwargs = cls._lte(query, **kwargs)
    query, kwargs = cls._in(query, **kwargs)
    query, kwargs = cls._like(query, **kwargs)
    # eq必须放在最后条件查询的最后
    # todo eq放在最后性能不好，应该先查eq.
    query, kwargs = cls._not(query, **kwargs)
    query, kwargs = cls._eq(query, **kwargs)
    query = cls._paginate(query, page, per_page)

    return query.all()

  @classmethod
  def get_items_with_pages(cls, **kwargs):
    for key in kwargs:
      if isinstance(kwargs[key], list):
        kwargs[key] = kwargs[key][0]
    page = int(kwargs.pop("page", 1))
    per_page = int(kwargs.pop("per_page", 100))

    query = cls.query
    query, kwargs = cls._sort(query, **kwargs)
    query, kwargs = cls._gt(query, **kwargs)
    query, kwargs = cls._gte(query, **kwargs)
    query, kwargs = cls._lt(query, **kwargs)
    query, kwargs = cls._lte(query, **kwargs)
    query, kwargs = cls._in(query, **kwargs)
    query, kwargs = cls._like(query, **kwargs)
    query, kwargs = cls._not(query, **kwargs)
    # eq必须放在最后
    query, kwargs = cls._eq(query, **kwargs)

    total = query.count()
    query = cls._paginate(query, page, per_page)
    page_count = query.count()
    page_info = PageInfo(page, per_page, total, page_count).render_page()
    return query.all(), page_info


class PageInfo(object):
  def __init__(self, page, per_page, total, page_count):
    page = int(page)
    per_page = int(per_page)
    if page < 1 or page is None:
      page = 1
    if per_page < 1 or per_page is None:
      per_page = 20
    if per_page > 500:
      per_page = 500
    self._total = total
    self._page = page
    self._per_page = per_page
    self._page_count = page_count

  @classmethod
  def _build_pages(cls, page):
    if page.current_page > 0:
      if page.total_pages > 10:
        if page.current_page > 4:
          if page.current_page + 5 <= page.total_pages:
            start = page.current_page - 4
            end = page.current_page + 5 + 1
          else:
            start = page.total_pages - 9
            end = page.total_pages + 1
        else:
          start = 1
          end = 10 + 1
      else:
        start = 1
        end = page.total_pages + 1

      for i in range(start, end):
        page.pages.append(i)

  def render_page(self):
    page = Page()
    page.total = self._total
    pages = divmod(page.total, self._per_page)
    page.total_pages = pages[0] + 1 if pages[1] else pages[0]

    page.has_prev = self._page > 1
    page.prev_page = self._page - 1 if self._page > 1 else 0

    page.has_next = self._page < page.total_pages
    page.next_page = self._page + 1 if self._page < page.total_pages else 0

    page.first_page = 1 if page.total_pages > 0 else 0
    page.last_page = page.total_pages if page.total_pages > 0 else 0

    page.page_count = self._page_count

    page.current_page = self._page if page.total_pages else 0
    page.per_page = self._per_page

    self._build_pages(page)

    return page


class Page(object):
  def __init__(self):
    self.total = 0
    self.total_pages = 0
    self.has_prev = False
    self.prev_page = 0
    self.has_next = False
    self.next_page = 0
    self.first_page = 0
    self.last_page = 0
    self.page_count = 0
    self.current_page = 0
    self.per_page = 0
    self.pages = []


class OfferStatus(BaseStatus):
  closed = 0
  open = 1


class OfferShutDownReason(object):
  finished = "finished"
  project_change = "project_change"
  others = "others"


class PostSchema(Schema):
  _permission_roles = ["om"]

  def auth_require(self):
    if current_user.role not in self._permission_roles:
      raise Exception("bad role")
