# Parallel Python

This library can be used to accomplish generic work in parallel.
If you have MPI installed, and start a program which uses this library using MPI (ex. mpiexec or mpirun), this program will distribute the work across a network of compute nodes.
If MPI is not available, it defaults to using python's multiprocessing package.



## Installation instructions
### Install mpi4py
If using generic MPI, feel free to use either:
* >pip install mpi4py
* >conda install mpi4py

If you are using this on a custom system you probably will need to build mpi4py from source.
I will document more later on how to do this.
The link to the git repo is as follows: https://bitbucket.org/mpi4py/mpi4py/


### Install parallelpy
I typically use:
* >python setup.py develop

## Example Code
* python examples/hello_world.py (to run using process pool)
* mpiexec -n 1 python examples/hello_world : -n PROCESS_COUNT python parallelpy/mpi_deligate.py

## Known Bugs
* Per Work evaluation time is typically slower than if done on a single node, so mainly useful for usecases where there is a lot of work to do.
