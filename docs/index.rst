
Welcome to DSCIM!
=================

**DSCIM** is a python library to calculate the Social Cost of Carbon. It reads results
from damage projections corresponding to one or more climate impact pathways (also known
as sectors, in DSCIM parlance) and allows the user to value (in welfare terms),
aggregate, and calculate the social cost of carbon dioxide (SCC) and other greenhouse gasses
(SC-GHG).

DSCIM offers an easy framework to load and quickly analyze data.
Most of the code relies heavily on ``xarray`` and ``dask``. The first is essential
to do different operations based on labels, while the second one allows
larger-than-memory calculations, while offering a generalizable interface that
can be executed on a local machine, an HPC system, or a cloud computing service.


Documentation Sections
=====================

.. toctree::
   :maxdepth: 2

   README
   CONTRIBUTING.rst
   modules


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
