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
There modes that parallelpy can run in : pool, Inter Node, and Intra Node.
The latter two make use of MPI and require the program to be started using mpi (i.e. mpiexec).

#### The Modes
##### Pool (PARALLEL_MODE_POOL)
This mode uses a python multiprocessing pool to evaluate work. It it primarly useful when developing code on your machine.

##### Inter Node (PARALLEL_MODE_MPI_INTER)
This mode typically will be used when you start one management process on each CPU core.
The main process then sends each parcel of work to one worker bee to be evaluated.
Since python's multiprocessing pool is not used the latency in this mode is slightly lower than in the other modes.

##### Intra Node (PARALLEL_MODE_MPI_INTRA)
This mode should only be used on compute clusters. If you only have *one* computer please use either Pool or Inter Node.

This mode typically will be used when you start one management process on each compute node.
Each management process on each compute node then starts up it's own python multiprocessing pool.
This mode is useful when you are evaluating very large amounts of work.
Since there is one management on each computer as apposed to one per core, we can send work in batches thus reducing the number of messages that we need to send.

#### Your code

```
# Import the things you need.
from parallelpy.utils import Work, Letter
from parallelpy.parallel_evaluate import setup, batch_complete_work, cleanup, THE_MODE_YOU_WANT.

# Construct a child class of Work
class HelloWorld(Work):
    def __init__(self):
    def compute_work(self, serial=False):
        # What work do I compute?
        
    def write_letter(self):
        # What information needs to be sent back home (a different instance of the class!)?
        # Send a tuple of the data and the destination.
        # You can use None for dest if you are unsure of what to put.
        return Letter(data, dest)

    def open_letter(self, letter):
        # recieve the letter and save the results of the completed computation.
        results = letter.get_data()

if __name__ == "__main__":

   # request which mode you want. If the request is unable to be fulfilled it will choose a different mode. The choosen mode is returned.
   setup(THE_MODE_YOU_WANT)
   
   # construct an iterable of work to complete
   work = [HelloWorld(i) for i in range 100]
   
   batch_complete_work(work) # send work to other processes which will run compute_work() then write_letter() then return the letter. When all letters are back, batch_complete_work() will run open_letter() on each and return None.
   
   cleanup() # tell the other processes to exit
```

## Notes
* When loading the pickled parcels of work, the parallelpy/mpi_deligate.py script needs to be able to resolve the names of all the packages / classes that the parcel of work references.
* Pickling does not support lambda expressions. Make sure to name all functions that are going to be pickled (i.e. all functions in classes that are parcels of Work).

## Examples
TODO: Update the below with what I use on the VACC.

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
