# ParallelPy

This package facilitates distributed parallel computation using MPI (Message Passing Interface).
To ease development and deployment, this package is able to make use of python multiprocessing for parallelism if MPI is not available.

## License
Copyright 2018 David Matthews

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0


Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.


## Getting started
### Dependencies:
* numpy
* scipy
* mpi4py

Although numpy and scipy can be installed however you want, you will need pay more attention to how you install mpi4py.
You will likely need to install mpi4py from source.

### Installing mpi4py (introduction)

If using generic MPI (i.e. your local machine), feel free to use either:
* >pip install mpi4py
* >conda install mpi4py

The above easy installation will likely not work if you are using a customized MPI install. In cluster environments, MPI installations are often customized, so you will probably need to manually install mpi4py from source. The link to the git repo is as follows: https://bitbucket.org/mpi4py/mpi4py/

#### Installing mpi4py on the Vermont Advanced Computing Core:
You will need to install from source.
1. Use ```switcher mpi --list``` to see which mpi libraries are available for use.
2. Use ```switcher mpi = <MPI LIBRARY>``` to select which MPI library you would like to use. I use ```openmpi-ib-gcc-1.10.3```.
   1. Although the VACC User documentation states that this library requires IB (InfiniBand), I have found it to work on both IB and ethernet. When using this MPI library, I get warning messages because certian IB specific files are missing. These are warning messages and not errors. When these warnings occur, ```openpmpi-ib-gcc-1.10.3``` will default to an ethernet based backend of MPI. This results in higher message latency. This is not an issue for this package because messages account for a small percent of the total computation time.
1. If my memory serves correctly, the commands are as follows. If you run into any errors feel free to ask me for help. I will update these install directions later.
  * cd /install/location
  * git clone https://bitbucket.org/mpi4py/mpi4py.git
  * cd mpi4py
  * python setup.py config
  * python setup.py build
  * python setup.py install

### Install parallelpy
Installation of parallelpy is not required for use. If you want to install feel free to do either of the following:
* > python setup.py install
* > python setup.py develop


### Using parallelpy


## Notes
* When loading the pickled parcels of work, the parallelpy/mpi_deligate.py script needs to be able to resolve the names of all the packages / classes that the parcel of work references.
* Pickling does not support lambda expressions. Make sure to name all functions that are going to be pickled (i.e. all functions in classes that are parcels of Work).

## Examples
### Process Pool
* python helloworld.py

### With MPI
#### One MPI Worker Process per core
* cd into /parallelpy/
* mpiexec -n 2 python examples/helloworld.py
or from anywhere on your system:
* mpiexec -n 2 python /path/to/helloworld.py 

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
This application was developed to allow the for hundreds or thousands of independent pieces of work to be completed in parallel across multiple compute nodes.
Sending messages to different processes on different computers is not instantanious.
If your primary concern is efficent use of every CPU clock cycle then you may want to start by using only 1 node.
Both python's multiprocess pool and MPI typically have good preformance when running on a single computer.
If you *really* care about efficiency and preformance, you probably should be using a non-python piece of software.
With the addition of additional compute nodes the wall clock time will decrease (up to a point) but the per-work CPU time will increase.
This is to say that when using many compute nodes each cpu core is utilized less efficently than if only using 1 node.
