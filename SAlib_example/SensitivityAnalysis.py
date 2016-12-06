
# coding: utf-8

# # Using Sensitivity Analysis to Interrogate Models
# 
# Original notebook: Will Usher, UCL Energy Institute, 10th December 2015 <br/>
# Updates to demonstrate running array jobs on a cluster: Richard West, 2016
# 
# In this version, most of the background and detail have been removed. Please refer to the original at https://github.com/SALib/SATut if you are not familiar with the system.

# In[1]:

from ipywidgets import widgets, interact
from IPython.display import display
get_ipython().magic('matplotlib inline')
import seaborn as sbn
import matplotlib.pyplot as plt
import numpy as np
from IPython.core.pylabtools import figsize
figsize(12, 10)
sbn.set_context("talk", font_scale=1)

# The model used for this seminar is contained in the file model.py
from model import cost_of_vehicle_to_grid, compute_profit, annualized_capital_cost, battery_lifetime, max_vehicle_power


# In[2]:

# Uncomment and execute the following line to see the contents of the `model.py` file
# %load model.py


# ## Using SALib to run a Sensitivity Analysis
# 
# As we saw earlier, SALib is a **free** **open-source** **Python** library which you can install by running the command
# 
# ```python
# pip install SALib
# ```
# 
# [Documentation](http://salib.readthedocs.org/) is available online.
# 

# ### Import the package

# In[3]:

from SALib.sample import morris as ms
from SALib.analyze import morris as ma
from SALib.plotting import morris as mp


# ### Define a problem file
# 
# In the code below, a problem file is used to define the variables we wish to explore

# In[4]:

morris_problem = {
    # There are six variables
    'num_vars': 7,
    # These are their names
    'names': ['conn', 'batt', 'dist', 'range', 'dri_eff', 'inv_eff', 'dispatch_time'],
    # These are their plausible ranges over which we'll move the variables
    'bounds': [[2.3, 22], # connection_power (kW)
               [50, 100], # battery size (kWh)
               [0, 80], # distance driven (km)
               [0, 80], # range buffer (km)
               [4,5.5], # driving efficiency (kWh/km)
               [0.87,0.97], # inverter efficienct (%)
               [0.5, 24] # dispatch time - hours of the day in which the energy is dispatched
              ],
    # I don't want to group any of these variables together
    'groups': None
    }


# ### Generate a Sample
# 
# We then generate a sample using the `morris.sample()` procedure from the SALib package.

# In[5]:

number_of_trajectories = 1000
sample = ms.sample(morris_problem, number_of_trajectories, num_levels=4, grid_jump=2)
print("The sample array is ",sample.shape)
print("Here are the first 10 rows:")
for j in range(10):
    print(' '.join(['{:10.3f}'.format(i) for i in sample[j]]))


# Now we're going to save the parameters to a file, so we can run the jobs separately not in this notebook.

# In[6]:

np.savetxt("parameter_values.txt", sample)

# This creates a blank file to store results in:
with open("results.txt", 'w') as result_file:  # 'w' is write mode, and will clear the file.
    result_file.write('')


# # Stop!  
# ## Now (pretend) we need to run the simulations on Discovery
# 
# To run this on Discovery, you will need to copy the `parameter_values.txt` file on to Discovery, along with a Python script file (eg. `script.py`) that looks like the cell a few lines below.  Use an SCP or SFTP program, as described earlier in the tutorial.
# 
# This is how many simulations we will need to run:

# In[7]:

len(sample)


# ...but the Slurm on Discovery is configured with a maximum job array size of 1001. (Run `scontrol show config | grep MaxArraySize` on Discovery to check). So we will run 1000 jobs, each of which runs 8 simulations.  (In real life, split into as few jobs as reasonable, to avoid clogging Slurm with thousands of needless jobs. i.e. 100 jobs each of 80 simulations would be better, or 10 jobs of 800).

# *The following cell contains the script.py. To update it uncomment the first `%load script.py` line and execute it - that will load in the `script.py` file which lives alongside this notebook and is where you should make changes if you are editing this tutorial.*

# In[8]:

# %load script.py
# This is a script that you should run on Discovery,
# as part of a Slurm Array job, with 1000 jobs.
import numpy as np
import os
from model import max_vehicle_power
big_parameter_list = np.loadtxt("parameter_values.txt")
job_number = int(os.getenv('SLURM_ARRAY_TASK_ID', default='0'))
assert 0<=job_number<1000, "Job number should run from 0 to 999"
for i in range(8):
    parameter_number = (8 * job_number) + i
    parameters = big_parameter_list[parameter_number]
    result = max_vehicle_power(*parameters)
    """
    Because we don't know what order the jobs will complete in,
    the results may be written out of order!
    To deal with this, we will write the job number in the results file
    as well as the result:
    """
    with open("results.txt", 'a') as result_file: # 'a' is append mode, and will add to the file.
        result_file.write('{} {}\n'.format(parameter_number, result)) # the '\n' is a new line


# Then create a `submit.sh` script to run it as an Array job, to fill the `results.txt` file with results.
# But realize that your Python script above expects the job number to start at zero, so you'll probably want something like
# ```
# #SBATCH --array=0-999%40
# ```
# in your submit file. eg. your `submit.sh` may look something like this:
# 
# ```
# #!/bin/sh
# #SBATCH -n 1
# #SBATCH -N 1
# #SBATCH --job-name=SA
# #SBATCH --array=0-999
# #SBATCH -p ser-par-10g
# python3 script.py
# ```
# 
# Once your jobs have all finished, copy the `results.txt` back to your computer and put it alongside this Notebook. Hopefully we can import it like this:

# In[ ]:

np.loadtxt("results.txt")


# In an ideal world, that would have worked. But computers aren't ideal, and it probably didn't. Open the `results.txt` file in a text editor and take a look at it carefully. My results file starts out looking OK:
# 
# ```
# 0 0.0
# 1 0.0
# 2 0.0
# 3 0.0
# 4 15.433333333333334
# 5 0.0
# 6 0.0
# ```
# 
# but there are some blank lines:
# 
# ```
# 36 2.3
# 37 2.3
# 38 15.433333333333334
# 
# 113 3.2741205154998254
# 39 15.433333333333334
# 114 3.472446888816995
# ```
# 
# and occasionally really weird things:
# 
# ```
# 75 0.0
# 
# 138 0.0
# 139 0.0
# 5227552275525
# 78 5.979226458931255
# 141 0.0
# 658266513936
# ```
# 
# The problem is (probably) that the different compute nodes running different processes all trying to write to the same file, which is stored on a networked file system on yet another computer, are conflicting, instead of waiting their turn to write to the file. This is notoriously difficult to manage, as there are all sorts of levels of cacheing involved. 
# 
# What we'll try next is to split the 8000 jobs into 100 jobs each running 80 parameter sets, and have each job print the results into its standard output file, which Slurm will collect into 100 separate files. Then we'll concatenate the 100 output files when the jobs are all done.

# ## Importing and analyzing the results 
# Then come back here to load the results and continue the sensitivy analysis.
# Because our results file may not be in order, but contains the job number at the start of each line, we need to do a little manipulation to get the `output` array as needed

# In[ ]:

results_array = np.loadtxt("results.txt")
results_dict = dict()
for number, value in results_array:
    results_dict[int(number)] = value
results_dict
output = np.array([results_dict[i] for i in range(len(results_dict))])


# ### Factor Prioritisation
# 
# We'll run a sensitivity analysis to see which is the most influential parameter.
# 
# The results parameters are called **mu**, **sigma** and **mu_star**.
# 
# * **Mu** is the mean effect caused by the input parameter being moved over its range.
# * **Sigma** is the standard deviation of the mean effect.
# * **Mu_star** is the mean absolute effect.

# In[ ]:

Si = ma.analyze(morris_problem, sample, output, print_to_console=False)
print("{:20s} {:>7s} {:>7s} {:>7s}".format("Name", "mu", "mu_star", "sigma"))
for name, s1, st, mean in zip(morris_problem['names'], Si['mu'], Si['mu_star'], Si['sigma']):
    print("{:20s} {:=7.2f} {:=7.2f} {:=7.2f}".format(name, s1, st, mean))


# We can plot the results

# In[ ]:

fig, (ax1, ax2) = plt.subplots(1,2)
mp.horizontal_bar_plot(ax1, Si, param_dict={})
mp.covariance_plot(ax2, Si, {})


# In[ ]:




# In[ ]:


