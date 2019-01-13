import logging
from .script_utils import runProgram, log


class TableMaker:
    """
    A wrapper to the leekgroup tablemaker. See
    https://github.com/leekgroup/tablemaker
    """

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        pass

    def build_ctab_files(self, ref_genome_path, alignment_path, output_dir, num_threads=2):
        """
        Runs tablemaker and generates the ctab files in the specified output_dir

        :param ref_genome_path: File path to a reference genome or transcriptome assembly in GTF
                                 format
        :param alignment_path: File path to a reads alignment in BAM format
        :param output_dir: directory to which the ctab files need to be written
        :param num_threads: Number of prcessing threads (default=2)

        :returns 0 if successful, else 1
        """
        print('Running tablemaker...')
        print("Args passed : ref_genome_path: {0} , alignment_path: {1} , output_dir: {2} , " \
              "num_threads: {3} ".format(ref_genome_path, alignment_path, output_dir, num_threads))
        tm_args = " -p {0} -o {1} -q -W -G {2} {3}".format(str(num_threads), output_dir,
                                                           ref_genome_path, alignment_path)
        try:
            print("Executing: tablemaker {0}".format(tm_args))
            runProgram(logger=self.logger, progName="tablemaker", argStr=tm_args)
        except Exception as ex:
            log("Error executing tablemaker {0}. {1}".format(tm_args, ex.message), logging.ERROR)
            return 1

        return 0
