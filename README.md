# ParallelPy

This library can be used to accomplish generic work in parallel.
If you have MPI installed, and start a program which uses this library using MPI (ex. mpiexec), this program will distribute the work across a network of compute nodes.
If MPI is not available, it defaults to using python's multiprocessing package.

## License
Copyright 2018 David Matthews

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0


Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.

## Installation instructions
### Install mpi4py

If using generic MPI, feel free to use either:
* >pip install mpi4py
* >conda install mpi4py

If you are using this on a custom system you probably will need to build mpi4py from source.
I will document more later on how to do this.
The link to the git repo is as follows: https://bitbucket.org/mpi4py/mpi4py/

#### If installing on the Vermont Advanced Computing Core:
You will need to install from source.
1. Use ```switcher mpi --list``` to see which mpi libraries are available for use.
2. Use ```switcher mpi = <MPI LIBRARY>``` to select which MPI library you would like to use. I use ```openmpi-ib-gcc-1.10.3```.
   1. Although the VACC User documentation states that this library requires IB, I have found it to work on both IB and ethernet. When using this MPI library, I get warning messages but these warnings do not appear to be an issue.

### Install parallelpy
I typically use:
* >python setup.py develop

## Notes
* When loading the pickled parcels of work, the parallelpy/mpi_deligate.py script needs to be able to resolve the names of all the packages / classes that the parcel of work references.
* Pickling does not support lambda expressions. Make sure to name all functions that are going to be pickled (i.e. all functions in classes that are parcels of Work).

## Examples
### Process Pool
* python hello_world.py

### With MPI
#### One MPI Worker Process per core
* cd into /parallelpy/
* mpiexec -n 2 python examples/helloworld.py
or from anywhere on your system:
* mpiexec -n 2 python /path/to/hello_world.py 

#### One MPI Worker Process per node
If you use the multi_node methods in ParallelPy, you will not be able to use a process pool instead of MPI.
* cd into /parallelpy/
* mpiexec -n 2 python examples/helloworld.py 
or from anywhere on your system:
* mpiexec -n 2 python /path/to/helloworld.py

### Running on the VACC

To request N cores: ```#PBS -l procs=<N>```

For example, to request 11 cores: ```#PBS -l procs=11```


## Limitations
* Depending on the application, you may find that the time complete each parcel of "Work" is either roughly the same as when done on a single node, or you may find it to be slower 
* This tool is mainly useful when you are evaluating many different parcels of work, and can make use of multiple compute nodes
