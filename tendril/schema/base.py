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
from decimal import Decimal
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
        raise NotImplementedError

    def _p(self, *args, **kwargs):
        return ConfigOptionPolicy(self._validation_context, *args, **kwargs)

    def elements(self):
        return {}

    def schema_policies(self):
        policies = self.elements()
        return policies

    def _load_schema_policies(self):
        self._policies.update(self.schema_policies())

    def _process(self):
        for key, policy in iteritems(self._policies):
            if isinstance(policy, ConfigOptionPolicy):
                try:
                    value = policy.get(self._raw)
                    if isinstance(value, ValidatableBase):
                        value.validate()
                        self._validation_errors.add(value.validation_errors)
                    setattr(self, key, value)
                except ContextualConfigError as e:
                    self._validation_errors.add(e)

    def __getattr__(self, item):
        policy = self._policies[item]
        try:
            return policy.get(self._raw)
        except ContextualConfigError as e:
            raise e

    def _validate(self):
        self._validated = True


class NakedSchemaObject(SchemaProcessorBase):
    def __init__(self, content, *args, **kwargs):
        super(NakedSchemaObject, self).__init__(*args, **kwargs)
        self._raw_content = content
        self._process()

    @property
    def _raw(self):
        return self._raw_content


class SchemaControlledYamlFile(SchemaProcessorBase):
    supports_schema_name = None
    supports_schema_version_max = None
    supports_schema_version_min = None

    def __init__(self, path, *args, **kwargs):
        self._path = path
        vctx = ValidationContext(self._path,
                                 locality=self.supports_schema_name)
        super(SchemaControlledYamlFile, self).__init__(*args, vctx=vctx,
                                                       **kwargs)
        self._yamldata = None
        self._get_yaml_file()

    @property
    def _raw(self):
        return self._yamldata

    @property
    def path(self):
        return self._path

    def _get_yaml_file(self):
        self._yamldata = yaml.load(self._path)
        self._process()
        try:
            self._verify_schema_decl()
        except SchemaNotSupportedError as e:
            self._validation_errors.add(e)

    def elements(self):
        e = super(SchemaControlledYamlFile, self).elements()
        e.update({
            'schema_name':    self._p(('schema', 'name'),),
            'schema_version': self._p(('schema', 'version'), parser=Decimal),
        })
        return e

    def schema_policies(self):
        policies = super(SchemaControlledYamlFile, self).schema_policies()
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
        if not policy.validate(self.schema_name, self.schema_version):
            raise SchemaNotSupportedError(
                policy,
                '{0} v{1}'.format(self.schema_name, self.schema_version)
            )


def load(manager):
    logger.debug("Loading {0}".format(__name__))
    manager.load_schema('SchemaControlledYamlFile', SchemaControlledYamlFile,
                        doc="Base class for schema controlled file processors.")
