#!/usr/bin/env python
# encoding: utf-8

# Copyright (C) 2019 Chintalagiri Shashank
#
# This file is part of tendril.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from six import iteritems
from inspect import isclass
from tendril.validation.base import ValidatableBase
from tendril.validation.base import ValidationError
from tendril.utils.types import ParseException


class MultilineString(list):
    def __init__(self, value):
        super(MultilineString, self).__init__(value)

    def __repr__(self):
        return '\n'.join(self)


class SchemaObjectCollection(ValidatableBase):
    _objtype = None
    _validator = None
    _allow_empty = True

    def __init__(self, content, *args, **kwargs):
        super(SchemaObjectCollection, self).__init__(*args, **kwargs)
        self._source_content = content
        self._content = self._empty_container

    @property
    def _empty_container(self):
        raise NotImplementedError

    @property
    def content(self):
        return self._content

    def _parse_item_with(self, item, objtype):
        if isclass(objtype) and \
                issubclass(objtype, ValidatableBase):
            value = objtype(item, vctx=self._validation_context)
            value.validate()
            self._validation_errors.add(value.validation_errors)
        elif objtype:
            value = objtype(item)
        else:
            value = item
        return value

    def _parse_item(self, item):
        if isinstance(self._objtype, list):
            default_parser = None
            for sig, parser in self._objtype:
                if sig == 'default':
                    default_parser = parser
                    continue
                if isinstance(item, sig):
                    return self._parse_item_with(item, parser)
            return self._parse_item_with(item, default_parser)
        else:
            return self._parse_item_with(item, self._objtype)

    def _validate_item(self, item):
        if not item:
            return False
        if self._validator:
            try:
                self._validator(item)
                return True
            except (ValidationError, ParseException) as e:
                self._validation_errors.add(e)
                return False
        return True

    def _validate(self):
        pass

    def __getitem__(self, item):
        return self.content[item]


class SchemaObjectList(SchemaObjectCollection):
    def __init__(self, *args, **kwargs):
        super(SchemaObjectList, self).__init__(*args, **kwargs)
        if not self._source_content and self._allow_empty:
            return
        for item in self._source_content:
            if not self._validate_item(item):
                continue
            self._content.append(self._parse_item(item))

    @property
    def _empty_container(self):
        return []

    def __len__(self):
        return len(self._content)


class SchemaObjectSet(SchemaObjectCollection):
    def __init__(self, *args, **kwargs):
        super(SchemaObjectSet, self).__init__(*args, **kwargs)
        if not self._source_content and self._allow_empty:
            return
        for k, v in iteritems(self._source_content):
            if not self._validate_item(v):
                continue
            self._content[k] = self._parse_item(v)

    @property
    def _empty_container(self):
        return {}

    def keys(self):
        return self.content.keys()


class SchemaSelectableObjectSet(SchemaObjectSet):
    def __init__(self, content, *args, **kwargs):
        default = content.pop('default')
        super(SchemaSelectableObjectSet, self).__init__(content, *args, **kwargs)
        self.default = self.content[default]

    def __getitem__(self, item):
        if not item:
            return self.default
        return super(SchemaSelectableObjectSet, self).__getitem__(item)

    def __repr__(self):
        return "<{0} {1}>".format(self.__class__.__name__ ,
                                  ','.join(self.content.keys()))


def load(manager):
    pass
