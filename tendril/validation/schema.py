#!/usr/bin/env python
# encoding: utf-8

# Copyright (C) 2016-2019 Chintalagiri Shashank
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


from tendril.validation.base import ValidationPolicy
from tendril.validation.base import ValidationError


class SchemaPolicy(ValidationPolicy):
    def __init__(self, context, name, vmax, vmin):
        super(SchemaPolicy, self).__init__(context)
        self.name = name
        self.vmax = vmax
        self.vmin = vmin

    def validate(self, name, version):
        if name == self.name and self.vmin <= version <= self.vmax:
            return True
        else:
            return False

    def render(self):
        return "Supports {0}<={1}<={2}".format(self.vmin, self.name, self.vmax)


class SchemaNotSupportedError(ValidationError):
    msg = "The file specifies a schema which is not supported."

    def __init__(self, policy, value):
        super(SchemaNotSupportedError, self).__init__(policy)
        self._value = value

    def __repr__(self):
        return "<SchemaNotSupportedError {0} {1}>" \
               "".format(self.policy.context, self._value)

    def render(self):
        return {
            'is_error': self.policy.is_error,
            'group': self.msg,
            'headline': "Got {0} in {1}".format(
                self._value, self.policy.context),
            'detail': self.policy.render(),
        }
