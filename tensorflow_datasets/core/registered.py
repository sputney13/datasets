# coding=utf-8
# Copyright 2020 The TensorFlow Datasets Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Access registered datasets."""

import abc
import collections
import contextlib
import inspect
from typing import ClassVar, Iterator

from tensorflow_datasets.core import naming
from tensorflow_datasets.core.utils import py_utils

# Internal registry containing <str registered_name, DatasetBuilder subclass>
_DATASET_REGISTRY = {}

# Internal registry containing:
# <str snake_cased_name, abstract DatasetBuilder subclass>
_ABSTRACT_DATASET_REGISTRY = {}

# Datasets that are under active development and which we can't therefore load.
# <str snake_cased_name, in development DatasetBuilder subclass>
_IN_DEVELOPMENT_REGISTRY = {}

# Keep track of Dict[str (module name), List[DatasetBuilder]]
# This is directly accessed by `tfds.community.builder_cls_from_module` when
# importing community packages.
_MODULE_TO_DATASETS = collections.defaultdict(list)



_skip_registration = False


@contextlib.contextmanager
def skip_registration() -> Iterator[None]:
  """Context manager within which dataset builders are not registered."""
  global _skip_registration
  try:
    _skip_registration = True
    yield
  finally:
    _skip_registration = False


class RegisteredDataset(abc.ABC):
  """Subclasses will be registered and given a `name` property."""

  # Name of the dataset, automatically filled.
  name: ClassVar[str]

  # Set to True for datasets that are under active development and should not
  # be available through tfds.{load, builder} or documented in overview.md.
  IN_DEVELOPMENT: ClassVar[bool] = False


  def __init_subclass__(cls, skip_registration=False, **kwargs):  # pylint: disable=redefined-outer-name
    super().__init_subclass__(**kwargs)

    # Set the name if the dataset does not define it.
    # Use __dict__ rather than getattr so subclasses are not affected.
    if not cls.__dict__.get('name'):
      cls.name = naming.camelcase_to_snakecase(cls.__name__)

    is_abstract = inspect.isabstract(cls)

    # Capture all concrete datasets, including when skip registration is True.
    # This ensure that `builder_cls_from_module` can load the datasets
    # even when the module has been imported inside a `skip_registration`
    # context.
    if not is_abstract:
      _MODULE_TO_DATASETS[cls.__module__].append(cls)

    # Skip dataset registration within contextmanager, or if skip_registration
    # is passed as meta argument.
    if skip_registration or _skip_registration:
      return

    # Check for name collisions
    if py_utils.is_notebook():  # On Colab/Jupyter, we allow overwriting
      pass
    elif cls.name in _DATASET_REGISTRY:
      raise ValueError(f'Dataset with name {cls.name} already registered.')
    elif cls.name in _IN_DEVELOPMENT_REGISTRY:
      raise ValueError(
          f'Dataset with name {cls.name} already registered as in development.'
      )
    elif cls.name in _ABSTRACT_DATASET_REGISTRY:
      raise ValueError(
          f'Dataset with name {cls.name} already registered as abstract.'
      )

    # Add the dataset to the registers
    if is_abstract:
      _ABSTRACT_DATASET_REGISTRY[cls.name] = cls
    elif cls.IN_DEVELOPMENT:
      _IN_DEVELOPMENT_REGISTRY[cls.name] = cls
    else:
      _DATASET_REGISTRY[cls.name] = cls
