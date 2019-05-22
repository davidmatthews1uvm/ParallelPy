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

setup(name='Parallel Computation',
      author='David Matthews',
      version='0.9dev',
      packages=['parallelpy'],
      description='Tools to support parallel computation of generic work via either MPI or a process pool',
      install_requires=['numpy', 'scipy', ]
      )
