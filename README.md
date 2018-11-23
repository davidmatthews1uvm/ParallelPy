# ParallelPy

This library can be used to accomplish generic work in parallel.
If you have MPI installed, and start a program which uses this library using MPI (ex. mpiexec), this program will distribute the work across a network of compute nodes.
If MPI is not available, it defaults to using python's multiprocessing package.


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
   1. ALthough the VACC User documentation states that this library requires IB, I have found it to work on both IB and ethernet. When using this MPI library, I get warning messages but do not appear to be an issue.

### Install parallelpy
I typically use:
* >python setup.py develop

## Notes
* When loading the pickled parcels of work, the parallelpy/mpi_deligate.py script needs to be able to resolve the names of all the packages / classes that the parcel of work references.
* To ensure that this will work, either:
    * import all of the needed python packages and modules so that the parcel of work can be loaded from the serialized format, or
    * modify the sys.path.insert(index, path) in the parallelpy/mpi_deligate.py script so that it looks in the same location as your main script.

## Examples
* python parallelpy/examples/hello_world.py (to run using process pool)
* mpiexec -n 1 python paralelpy/examples/hello_world.py : -n <N> python parallelpy/mpi_deligate.py
    * where you want N processes computing the parcels of work

### Running on the VACC

To request N cores: ```#PBS -l procs=<N>```

For example, to request 11 cores: ```#PBS -l procs=11```


## Limitations
* Depending on the application, you may find that the time complete each parcel of "Work" is either roughly the same as when done on a single node, or you may find it to be slower 
* This tool is mainly useful when you are evaluating many different parcels of work, and can make use of multiple compute nodes
