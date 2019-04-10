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


class MultilineString(list):
    def __init__(self, value):
        super(MultilineString, self).__init__(value)

    def __repr__(self):
        return '\n'.join(self)


class SchemaObjectSet(ValidatableBase):
    def __init__(self, content, objtype, *args, **kwargs):
        super(SchemaObjectSet, self).__init__(*args, **kwargs)
        self.content = content or {}
        for k, v in iteritems(content):
            if isclass(objtype) and issubclass(objtype, ValidatableBase):
                value = objtype(v, vctx=self._validation_context)
                value.validate()
                self._validation_errors.add(value.validation_errors)
            else:
                value = objtype(v)
            self.content[k] = value

    def keys(self):
        return self.content.keys()

    def _validate(self):
        # TODO
        pass

    def __getitem__(self, item):
        return self.content[item]


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
