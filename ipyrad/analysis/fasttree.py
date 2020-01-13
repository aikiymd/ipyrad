#!/usr/bin/python 

""" wrapper to use fasttree v.1"""
#caml aug-2019

from __future__ import print_function

import os
import glob
import subprocess
from ipyrad.analysis.utils import Params
from ipyrad.assemble.utils import IPyradError

## alias
OPJ = os.path.join


class Fasttree(object):
    """
    Description
    Tool to run FastTree with ipyrad assemblies in Jupyter notebooks. This tool facilitate the command line string creation, fasta converstion (FastTree only read interleave phylip format) and submit it as a job. Finally it make easy access the results to plot it with toytree tool in ipyrad. Call .run() to submith the job.
    
    Parameters:
    -----------
    data: str
        The phylip sequencial formated sequence file (.phy from ipyrad). A fasta file will be generated by this tool (this will be used by FastTree).
    name: str
        The name of this run.
    workdir: str
        The output directory for results.

    Additional optional parameters
    -------------------------------
    advanced: str
        (empty) Allow user includes other advanced option for FastTree. These must be included in a string like: "-cat 4 -pseudo". Review FastTree manual.
    gamma: bool
        (False) Set gamma for GTR model.
    m: str
        (gtr) The model to use. FastTree accepts only ('gtr') GTR+CAT, WAG+CAT ('wag') or LG+CAT ('lg') models (aminoacid only). If is empty or space, FastTree will use the Jukes-Cantor + CAT model.
    overwrite: bool
        (False) Control overwrite fasta file.
    t: str
        (nt) Type of data analyzed, FastTree accept 'nt' for nucleotides or 'aa' for aminoacids.
    T: int
        (1) Set number of threads used by FastTreeMP, take into account you must use MP version of FastTree (get it from http://www.microbesonline.org/fasttree/) and OpenMP also installed (get it from conda install -c conda-forge openmp)
    


    Attributes:
    -----------
    params: dict
        parameters for this FastTree run 
    command:
        returns the command string ro run FastTree

    Functions:
    ----------
    run()
        submit FastTree as a job
    """    

    ## init object for params
    def __init__(self,
        data,
        name="test",
        workdir="analysis-fasttree", 
        *args, 
        **kwargs):

        ## path attributes
        self._kwargs = {
            "T": 1,   
            "t": "nt",
            "m": "gtr",
            "binary": "",
            "advanced": "",
            "gamma": False,
            "overwrite": False,
            }

        # update kwargs for user args and drop key if value is None
        self._kwargs.update(kwargs)
        self._kwargs = {i: j for (i, j) in self._kwargs.items() if j is not None}

        # check workdir
        if workdir:
            workdir = os.path.abspath(os.path.expanduser(workdir))
        else:
            workdir = os.path.abspath(os.path.curdir)
        if not os.path.exists(workdir):
            os.makedirs(workdir)

        ## entered args
        self.params = Params()
        self.params.n = name
        self.params.w = workdir
        self.params.s = os.path.abspath(os.path.expanduser(data))
        self.params.f = OPJ(workdir, name + ".fasta")

        ## find the binary
        if not self._kwargs["binary"]:
            self.params.binary = _find_binary(self._kwargs["T"])

        ## set params
        notparams = set(["workdir", "name", "data", "binary"])
        for key in set(self._kwargs.keys()) - notparams:
            self.params[key] = self._kwargs[key]

        ## check binary
        self._get_binary()

        ## attributesx
        self.rasync = None
        self.stdout = None
        self.stderr = None

        ## results files        
#         self.trees = Params()
        self.tree = OPJ(workdir, "FastTree_Tree." + name)
        self.log = OPJ(workdir, "FastTree." + name + ".log")


        # Convert phylip into fasta cause fasttree only read interleaved phylyp (or fasta) and not sequential phylip
        if os.path.exists(str(self.params.f)) and not self.params.overwrite:
            print("Fasta file already exist in: {}".format(str(self.params.f)), end='\n')
        else:
            open(str(self.params.f), 'w').close() #clean fasta file in case it exist (useful for overwrite parameter)
            print("Converting phylip file to fasta...", end='\r')
            with open(str(self.params.s), 'r') as f: #open phy file to convert in fasta file
                for nline, line in enumerate(f, start=1): #move line by line
                    if nline != 1: #skip first line 
                        with open (str(self.params.f), 'a') as fw:
                            fw.write(">" + line.split()[0] + "\n" + line.split()[1] +  "\n")#add > at the beggining and split line by spaces, first is name and second is sequence (If name contain space can be a problem)
            print("Temporal fasta file saved in: {}".format(str(self.params.f)), end='\n')


          # Set enviromental variable to control OpenMP  (OMP_NUM_THREADS)
        if self._kwargs["T"] > 1:
            os.environ["OMP_NUM_THREADS"] = str(self._kwargs["T"])
            print("FastTree will use {} threads, be sure have installed OpenMP".format(self._kwargs["T"]), end='\n')
                                                                                                                 

    @property
    def _command_list(self):
        """ build the command list """
        cmd = [
            self.params.binary, 
            "-" + str(self.params.t), 
            "-" + str(self.params.m), 
            str(self.params.f),          
        ]
        #Add gamma after model if true
        if self.params.gamma:
            cmd.insert(3, "-gamma")
        #Add other parameters as string for advance options
        if self.params.advanced:
            cmd[len(cmd)-1:len(cmd)-1] = self.params.advanced.split()
        return cmd


    @property
    def command(self):
        """ returns command as a string """
        return "{} > {}".format(" ".join(self._command_list), self.tree)

    #TODO: test with -out parameter instead of >
    def run(self, 
        ):
        """ runs command """
        #FastTree put tree in stdout, so to emulate bash redirection ">" stdout is put in fp
        with open(self.tree, "w") as ft, open( self.log, "w") as fl: #open for write two files, tree file and log file
            #I am unsure about using subprocess.run or Popen
            proc = subprocess.Popen(self._command_list, stdout=ft, stderr=fl).communicate()
#             #Print line by line of stderr (here is the progress of FastTree)
#             for line in iter(proc.stderr.readline, b''):
#                 print(line.rstrip().decode('ascii'))



    def _get_binary(self):
        """ find binaries available"""

        ## check for binary
        if self.params.T > 1:
            backup_binaries = ["FastTreeMP"]
        else:
            backup_binaries = ["FastTree"]

        ## check user binary first, then backups
        for binary in [self.params.binary] + backup_binaries:
            proc = subprocess.Popen(["which", self.params.binary], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT).communicate()
            ## update the binary
            if proc:
                self.params.binary = binary

        ## if none then raise error
        if not proc[0]:
            raise Exception(BINARY_ERROR.format(self.params.binary))



def _find_binary(T):
    # check for binary with multithread if more than 1 T is defined
    if T > 1:
        list_binaries = ["FastTreeMP"]
        exceptionMsg = "cannot find FastTreeMP; download FastTreeMP from http://www.microbesonline.org/fasttree/"
    else:
        list_binaries = ["FastTreeDbl", "fasttree", "FastTree"]
        exceptionMsg = "cannot find FastTree; try to install it with 'conda install -c bioconda fasttree'"

    # check user binary first, then backups
    for binary in list_binaries:
        proc = subprocess.Popen(["which", binary],
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT).communicate()
        # if a binary was found then stop
        if proc[0]:
            return binary

    # if not binaries found
    raise Exception(exceptionMsg)



BINARY_ERROR = """
  Binary {} not found. 

  Check that you have FastTree installed. If you have a different binary
  installed you can select it using the argument 'binary'. 
"""
