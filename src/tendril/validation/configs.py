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


from inspect import isclass
from tendril.validation.base import ValidatableBase
from tendril.validation.base import ValidationError
from tendril.validation.base import ValidationPolicy


class ContextualConfigError(ValidationError):
    msg = "Incorrect Configuration"

    def __init__(self, policy):
        super(ContextualConfigError, self).__init__(policy)

    def _format_path(self):
        if isinstance(self._policy.path, tuple):
            return '/'.join(self._policy.path)
        else:
            return self._policy.path

    def render(self):
        return {
            'is_error': self.policy.is_error,
            'group': self.msg,
            'headline': self._policy.context.render(),
            'detail': "Configuration seems to be incorrect.",
        }


class ConfigKeyError(ContextualConfigError):
    msg = "Configuration Key Missing"

    def __init__(self, policy):
        super(ConfigKeyError, self).__init__(policy)

    def __repr__(self):
        return "<ConfigKeyError {0} {1}>" \
               "".format(self._policy.context, self._format_path())

    def render(self):
        if self._policy.options:
            option_str = "Valid options are {0}" \
                         "".format(', '.join(self._policy.options))
        else:
            option_str = ''
        return {
            'is_error': self.policy.is_error,
            'group': self.msg,
            'headline': "{0} missing in {1}"
                        "".format(self._format_path(),
                                  self._policy.context.render()),
            'detail': "This required configuration option could not be "
                      "found in the configs file. " + option_str,
        }


class ConfigValueInvalidError(ContextualConfigError):
    msg = "Configuration Value Unrecognized"

    def __init__(self, policy, value):
        super(ConfigValueInvalidError, self).__init__(policy)
        self._value = value

    def __repr__(self):
        return "<ConfigValueInvalidError {0} {1}>" \
               "".format(self._policy.context, self._format_path())

    def render(self):
        if self._policy.options:
            option_str = "Valid options are {0}".format(', '.join(self._policy.options))
        else:
            option_str = ''
        return {
            'is_error': self.policy.is_error,
            'group': self.msg,
            'headline': "'{0}' Invalid for {1} in {2}"
                        "".format(self._value, self._format_path(),
                                  self._policy.context.render()),
            'detail': "The value provided for this configuration option is "
                      "unrecognized or not allowed in this context. " + option_str,
        }


class ConfigOptionPolicy(ValidationPolicy):
    def __init__(self, context, path, parser=None, required=True,
                 options=None, default=None, is_error=True):
        super(ConfigOptionPolicy, self).__init__(context, is_error)
        self.path = path
        self.parser = parser
        self.options = options
        self.default = default
        self.required = required

    def get(self, data):
        if self.path is None:
            return data
        try:
            return get_dict_val(data, self)
        except ConfigKeyError as error:
            if not self.required:
                if self.default is None or not self.parser:
                    return self.default
                if isclass(self.parser) and isinstance(self.default, self.parser):
                    return self.default
                vctx = self.context.child(self.parser.__name__)
                return _parse(self.parser, self.default, vctx=vctx)
            else:
                raise error


def _parse(parser, value, vctx=None):
    if isclass(parser) and \
            issubclass(parser, ValidatableBase):
        return parser(value, vctx=vctx)
    else:
        return parser(value)


def get_dict_val(d, policy=None):
    try:
        assert isinstance(d, dict)
    except AssertionError:
        print("Expected to get a dictionary here. This probably means the YAML "
              "file is empty or unrecognizably mangled. Got {0} instead.".format(d))
        print(policy.context)
        raise
    if isinstance(policy.path, tuple):
        try:
            for key in policy.path:
                if key not in d.keys():
                    raise KeyError
                d = d.get(key)
        except (KeyError, AttributeError):
            raise ConfigKeyError(policy=policy)
        rval = d
    else:
        try:
            if policy.path not in d.keys():
                raise KeyError
            rval = d.get(policy.path)
        except KeyError:
            raise ConfigKeyError(policy=policy)

    if policy.parser:
        try:
            if isinstance(policy.parser, tuple):
                for parser in policy.parser:
                    try:
                        vctx = policy.context.child(parser.__name__)
                        rval = _parse(parser, rval, vctx)
                        break
                    except:
                        continue
                else:
                    raise Exception
            else:
                vctx = policy.context.child(policy.parser.__name__)
                rval = _parse(policy.parser, rval, vctx)
        except Exception as e:
            raise ConfigValueInvalidError(policy=policy, value=rval)

    if policy.options is None or rval in policy.options:
        return rval
    else:
        raise ConfigValueInvalidError(policy=policy, value=rval)
