from setuptools import setup

setup(name='Parallel Computation',
      author='David Matthews',
      version='0.1dev',
      packages=['parallelpy'],
      description='Tools to support parallel computation of generic work via either MPI or a process pool',
      install_requires=['numpy', 'scipy', ]
      )
