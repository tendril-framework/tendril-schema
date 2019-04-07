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


from decimal import Decimal
from tendril.utils.files import yml as yaml

from tendril.validation.base import ValidatableBase
from tendril.validation.base import ValidationContext
from tendril.validation.schema import SchemaPolicy
from tendril.validation.schema import SchemaNotSupportedError
from tendril.validation.configs import ConfigOptionPolicy

from tendril.utils import log
logger = log.get_logger(__name__, log.DEFAULT)


class SchemaControlledYamlFile(ValidatableBase):
    supports_schema_name = None
    supports_schema_version_max = None
    supports_schema_version_min = None

    def __init__(self, path, hardfail=True):
        super(SchemaControlledYamlFile, self).__init__()
        self._path = path
        self._validation_context = ValidationContext(
            self._path, locality=self.supports_schema_name
        )
        self._policies = {}
        self._load_schema_policies()

        self._yamldata = None
        self._get_yaml_file(hardfail)

    @property
    def path(self):
        return self._path

    def _get_yaml_file(self, hardfail=True):
        self._yamldata = yaml.load(self._path)
        try:
            self._verify_schema_decl()
        except SchemaNotSupportedError as e:
            if hardfail:
                raise
            self._validation_errors.add(e)

    def schema_policies(self):
        return {
            'schema_name': ConfigOptionPolicy(
                self._validation_context, ('schema', 'name')
            ),
            'schema_version': ConfigOptionPolicy(
                self._validation_context, ('schema', 'version'),
                parser=Decimal
            ),
            'schema_policy': SchemaPolicy(
                self._validation_context,
                self.supports_schema_name,
                self.supports_schema_version_max,
                self.supports_schema_version_min
            )
        }

    def _load_schema_policies(self):
        self._policies.update(self.schema_policies())

    def _verify_schema_decl(self):
        policy = self._policies['schema_policy']
        if not policy.validate(self.schema_name, self.schema_version):
            raise SchemaNotSupportedError(
                policy,
                '{0} v{1}'.format(self.schema_name, self.schema_version)
            )

    def _validate(self):
        pass

    def __getattr__(self, item):
        return self._policies[item].get(self._yamldata)


def load(manager):
    logger.debug("Loading {0}".format(__name__))
    manager.load_schema('SchemaControlledYamlFile', SchemaControlledYamlFile,
                        doc="Base class for schema controlled file processors.")
