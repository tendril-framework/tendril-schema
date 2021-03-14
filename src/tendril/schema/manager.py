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
Tendril Schema Manager (:mod:`tendril.schema.manager`)
======================================================
"""


import importlib

from tendril.validation.base import ValidationContext
from tendril.validation.configs import ConfigOptionPolicy
from tendril.validation.schema import SchemaNotSupportedError
from tendril.schema.base import SchemaControlledYamlFile

from tendril.utils.versions import get_namespace_package_names
from tendril.utils import log
logger = log.get_logger(__name__, log.DEBUG)


class SchemaManager(object):
    def __init__(self, prefix):
        self._prefix = prefix
        self._schemas = {}
        self._file_schemas = {}
        self._docs = []
        self._load_schemas()
        self._validation_context = ValidationContext(self.__module__)

    def _load_schemas(self):
        logger.debug("Loading schema modules from {0}".format(self._prefix))
        modules = list(get_namespace_package_names(self._prefix))
        for m_name in modules:
            if m_name == __name__:
                continue
            m = importlib.import_module(m_name)
            m.load(self)
        logger.debug("Done loading schema modules from {0}".format(self._prefix))

    def load_schema(self, name, processor, doc):
        logger.debug("Installing schema definition {0}".format(name))
        self._schemas[name] = processor
        if issubclass(processor, SchemaControlledYamlFile):
            self._file_schemas[name] = processor
        self._docs.append((name, doc))

    def __getattr__(self, item):
        if item == '__file__':
            return None
        if item == '__path__':
            return None
        if item == '__len__':
            return len(self._schemas.keys())
        if item == '__all__':
            return list(self._schemas.keys()) + \
                   ['load_schema', 'load', 'doc_render']
        return self._schemas[item]

    def load(self, targetpath):
        baseparser = getattr(self, 'SchemaControlledYamlFile')
        target = baseparser(targetpath)
        target_schema = target.schema_name
        if target_schema not in self._file_schemas.keys():
            # TODO Replace with a generic OptionPolicy?
            policy = ConfigOptionPolicy(self._validation_context,
                                        'schema.name',
                                        self._file_schemas.keys())
            raise SchemaNotSupportedError(policy, target_schema)
        return getattr(self, target_schema)(targetpath)

    def doc_render(self):
        return self._docs

    def __repr__(self):
        return "<SchemaManager>"
