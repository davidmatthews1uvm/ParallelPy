# Copyright 2018 David Matthews
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


from setuptools import setup

# Version Numbers:
# x.y.z.w
# w: Minor changes; Does not impact API.
# z: Minor changes: Backwards compatible.
# y: Semi-minor changes: Not all parts backwards compatible, you probably will not need to change your code.
# x: Major changes: Upgrades will likely require changes to your code.

setup(name='Parallel Computation',
      author='David Matthews',
      version='0.9.0.0',
      packages=['parallelpy'],
      description='package to preform distributed parallel computation using MPI.',
      install_requires=['numpy', 'scipy', ]
      )
