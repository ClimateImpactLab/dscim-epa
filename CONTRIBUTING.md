# Contributing to the DSCIM model

Welcome to the Data-driven Spatial Climate Impact Model (also know as
`dscim`). First off, thanks for taking the time to contribute and
take care of our library. 

All changes in the code base must be based on Python3+. This repository must
only include code related to the execution of a SC-GHG menu and is not a
place for sector/analysis code; this includes plots or data. Check the
`.gitignore` file and avoid uploading non-code related files to this repository


[[_TOC_]]

##  Code of Conduct

We will abide by the [Contributor Covenant](code_of_conduct.md)

## Before you start

The integration code base is currently based on Python3.x and depends heavily on
distributed systems supported by the
[Dask-Jobqueue](https://jobqueue.dask.org/en/latest/) library. If you wish to
contribute, you will have to clone this repository and install a set of testing
conda environments that will help you to execute the code and run the necessary
tests. 

You can install the test-bed environment: `integration_notebooks` by running:

```bash 
conda env create -f env/integration_env.yml 
``` 
And then proceed to activate the environment by: 
```bash 
conda activate integration_notebooks 
```

We recommend JupyterLab for debugging and general coding, with the addition of
the [Dask-labextension](https://github.com/dask/dask-labextension) which
facilitates the testing of the integration code using a local cluster. For more
details, check the library documentation. 

### For SLURM environments (Berkeley and UChicago’s Midway) Running the
integration code (with all the menu options) is a memory intensive job. For this
reason, you should avoid running any `dscim` related jobs on login
nodes. You can request a on-demand computing node by running the following
command on your login node terminal: 

```bash 
sinteractive --nodes=1 --exclusive --account=<account> --time=HH:MM:SS
```

Once granted, a new computing node will be available for you to use freely. Use
this as a new terminal and load your `conda` environment on it. 

**Please follow you system administrator documentation related to the limits
of interactive jobs in the cluster**


## How can I contribute? 

All contributions to the repo have to follow the following guidelines:

- All bugs/fixes to code should always use a pull request. Changes should
  never be committed directly to the `main` branch (previously known as `master`
branch). 
- Changes to the code base must follow the style guide and be correctly
  documented following the instructions in this section (see the [Style Guides
section](##Style Guide))
- Open PRs must be always tested either by the submitter, either by using the
- unit-test suite or by asserting continuity in the output values. 
- As explained in the Code of Conduct, we expect honest and thorough review of
  the code and expect that the submitter abides by the comments of the reviewer
	and avoids merging without permission. 

### Contributions and testing

All new contributions to the repo must be tested by either building unit test
cases or checking individual SCC values. For simplicity and overall testing we
prefer the use of unit tests for all new function in the menu. Unit testing must
follow this simple guidelines: 

- Unit tests must follow `pytest` case testing and use library dependent testing
  environments.
- Unit tests must follow a common naming convention adding `test` at the start
  of the function name to be tested (i.e. `my_function` and `test_my_function`). 
- Fixtures must be used if data cannot be generated or if the function is
validating intermediate products such as the SCC. See more on pytest about this.

A more naive test can be done by comparing the SCC values from one SSP and
sector just checking the they are coinciding correctly to the version produced
by the main branch. This solution is an easy way of checking the menu, but is
far from being comprehensive and automatic testing should be preferred over
naive testing. 

We expect replication to the 4th or greater decimal place.

```python
# For pandas

# In read_files.py
def read_files(lst): 
    """ Read files from list and concatenate 
    Parameters
    ---------- 
    lst : lst of pd.DataFrames 
    	List of data frames
    
    Returns 
    ------- 
    pd.DataFrame 
    	A concatenated DataFrame """
    
    try: 
	df = pd.concat(lst)
    except KeyError: 
	cols = [x.columns for x in lst]
	raise KeyError(f'No align in columns: {cols}')

    return df

# In test_read_files.py
import pytest 
import pandas as pd 
from pandas.testing import assert_frame_equal

from read_files import read_files

def test_read_files(): 
    df1 = pd.DataFrame({'a':[1,2,3,4,5]})
    df2 = pd.DataFrame({'a':[6,7,8,9,10]}) 
    expected = pd.DataFrame({
        'a': [[1,2,3,4,5],[6,7,8,9,10]] 
    })

    exp = read_files([df1, df2])
    assert_frame_equal(exp, expected) 
```

A more naive test can be done by comparing the SCC values from one SSP and
sector just checking the they are coinciding correctly to the version produced
by the main branch. This solution is an easy way of checking the menu, but is
far from being comprehensive and automatic testing should be preferred over
naive testing. 

## Style guide

### Commits and Github/Gitlab Commits should be traceable and allow the user to
go back in time with ease. The following style must be follow in commit messages
and PRs: 

- Commit messages must always be in long format: 
``` 
    Head of commit message (80 characters)
    
    This commit: 
     * Explain change here with detail and explain which script or module has
     * changed.  Add more bullets as needed.
    
    Bugs or problems:
     * Explain bugs with the code or inconsistencies in the commit. 
```

Avoid at all costs the use of `git commit -m` `"``short message``"` .

- Use the present tense (“Add feature” not “Added feature”)
- Limit the first line to 80 characters or less
- Reference issues and pull requests after the first line (use PR and Issue
  numerals)
- Consider starting the commit message with an applicable emoji:

     - 🎨 `:art:` when improving the format/structure of the code
     -  `:racehorse:` when improving performance
     - 🚱 `:non-potable_water:` when plugging memory leaks
     - 📝 `:memo:` when writing docs
     - 🐧 `:penguin:` when fixing something on Linux
     - 🐛 `:bug:` when fixing a bug
     -  🔥`:fire:` when removing code or files
     - 💚 `:green_heart:` when fixing the CI build
     - ✅ `:white_check_mark:` when adding tests
     - 🔒 `:lock:` when dealing with security
     - ⬆️ `:arrow_up:` when upgrading dependencies
     - ⬇️ `:arrow_down:` when downgrading dependencies
     - 👕 `:shirt:` when removing linter warnings

Pull requests must also include a similar structure. By default, Gitlab/Github
will include the first commit message in the branch as the default PR message.
Be aware of this behavior and change your PR message accordingly. 

### Python Style code

We follow the [Google Python Style
guide](https://google.github.io/styleguide/pyguide.html) and the [Numpy
documentation style](https://numpydoc.readthedocs.io/en/latest/format.html). 

### Documentation is 🔑 Every new method or function should always follow the
above style guides, and no object should be added without proper documentation.
For example, all functions or class methods should have a `docstring` like the
following:

```python 
def read_files(lst, **kwargs): 
    """" Read files in list 
    Parameters:
    ----------- 
    lst : list 
	A list of paths to read in **kwargs Options to pass to the pd.read_csv
	function

    Returns
    -------- 
    pd.DataFrame 
	A pandas dataframe 
    """" 
```

This is also true for class properties: 
```python 
   @property 
   def number_of_files(self): 
   """ Number of files passed to class 
   """ 
```

