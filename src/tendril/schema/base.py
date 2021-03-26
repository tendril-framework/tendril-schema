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
"""
Base Schemas (:mod:`tendril.schema.base`)
=========================================
"""

import os
import warnings
from six import iteritems
from decimal import Decimal
from jinja2 import Template
from tendril.utils.files import yml as yaml

from tendril.validation.base import ValidatableBase
from tendril.validation.base import ValidationContext
from tendril.validation.schema import SchemaPolicy
from tendril.validation.schema import SchemaNotSupportedError
from tendril.validation.configs import ConfigOptionPolicy
from tendril.validation.configs import ContextualConfigError

from tendril.utils import log
logger = log.get_logger(__name__, log.DEFAULT)


class SchemaProcessorBase(ValidatableBase):
    def __init__(self, *args, **kwargs):
        super(SchemaProcessorBase, self).__init__(*args, **kwargs)
        self._policies = {}
        self._load_schema_policies()

    @property
    def _raw(self):
        return self._raw_content

    def _p(self, *args, **kwargs):
        return ConfigOptionPolicy(self._validation_context, *args, **kwargs)

    def elements(self):
        return {}

    def schema_policies(self):
        policies = self.elements()
        return policies

    def _load_schema_policies(self):
        self._policies.update(self.schema_policies())

    def _process_element(self, key, policy):
        if isinstance(policy, ConfigOptionPolicy):
            try:
                value = policy.get(self._raw)
                if isinstance(value, ValidatableBase):
                    value.validate()
                    self._validation_errors.add(value.validation_errors)
                setattr(self, key, value)
            except ContextualConfigError as e:
                # If the error trapped is not useful, raising it right here can
                # sometimes be helpful.
                # raise e
                # TODO This seems to have to do with stacked exceptions, of the
                #  "During handling of the above exception, another exception occurred:" variety.
                #  A better way to communicate such errors is required.
                self._validation_errors.add(e)

    def _process(self):
        for key, policy in iteritems(self._policies):
            self._process_element(key, policy)

    def __getattr__(self, item):
        if item not in self._policies.keys():
            raise AttributeError("%r has no attribute %r" % (type(self), item))
        policy = self._policies[item]
        return policy.get(self._raw)

    def _validate(self):
        self._validated = True


class NakedSchemaObject(SchemaProcessorBase):
    def __init__(self, content, *args, **kwargs):
        super(NakedSchemaObject, self).__init__(*args, **kwargs)
        self._raw_content = content
        self._process()
        if self.validation_errors.terrors:
            warnings.warn("{0} of class {1} has {2} Validation Errors"
                          "".format(self.ident, self.__class__.__name__,
                                    self.validation_errors.terrors),
                          UserWarning)


class SchemaControlledObject(NakedSchemaObject):
    legacy_schema_name = None
    supports_schema_name = None
    supports_schema_version_max = None
    supports_schema_version_min = None

    def __init__(self, *args, strict_schema=False, **kwargs):
        self._strict_schema = strict_schema
        super(SchemaControlledObject, self).__init__(*args, **kwargs)

    def _stub_content(self):
        return {
            'schema_name': self.supports_schema_name,
            'schema_version': self.supports_schema_version_max,
        }

    def elements(self):
        e = super(SchemaControlledObject, self).elements()
        e.update({
            'schema_name':    self._p(('schema', 'name'),),
            'schema_version': self._p(('schema', 'version'), parser=Decimal),
        })
        return e

    def schema_policies(self):
        policies = super(SchemaControlledObject, self).schema_policies()
        policies.update({
                'schema_policy': SchemaPolicy(
                    self._validation_context,
                    self.supports_schema_name,
                    self.supports_schema_version_max,
                    self.supports_schema_version_min
                )
        })
        return policies

    def _verify_schema_decl(self):
        policy = self._policies['schema_policy']
        if self.supports_schema_name == '*':
            return
        if self.schema_name == self.legacy_schema_name:
            self.schema_name = self.supports_schema_name
        logger.debug("Validating Schema Policy : {0} {1}"
                     "".format(self.schema_name, self.schema_version))
        if not policy.validate(self.schema_name, self.schema_version):
            raise SchemaNotSupportedError(
                policy,
                '{0} v{1}'.format(self.schema_name, self.schema_version)
            )

    def _process(self):
        super(SchemaControlledObject, self)._process()
        try:
            self._verify_schema_decl()
        except SchemaNotSupportedError as e:
            if self._strict_schema:
                raise
            self._validation_errors.add(e)


class SchemaControlledYamlFile(SchemaControlledObject):
    supports_schema_name = '*'
    FileNotFoundExceptionType = None
    template = None

    def __init__(self, path, *args, **kwargs):
        self._path = path
        vctx = ValidationContext(
            self._path,
            locality=self.supports_schema_name or self.__class__.__name__
        )
        raw_content = self._get_yaml_file()
        super(SchemaControlledYamlFile, self).__init__(
            raw_content, *args, vctx=vctx, **kwargs
        )

    @property
    def path(self):
        return self._path

    def _generate_stub(self):
        template = Template(open(self.template).read())
        with open(self._path, 'w') as f:
            f.write(template.render(stage=self._stub_content()))

    def _get_yaml_file(self):
        if self.template and not os.path.exists(self._path):
            self._generate_stub()
        if self.FileNotFoundExceptionType and not os.path.exists(self._path):
            raise self.FileNotFoundExceptionType(self._path)
        return yaml.load(self._path)


def load(manager):
    logger.debug("Loading {0}".format(__name__))
    manager.load_schema('SchemaControlledYamlFile', SchemaControlledYamlFile,
                        doc="Base class for schema controlled file processors.")
