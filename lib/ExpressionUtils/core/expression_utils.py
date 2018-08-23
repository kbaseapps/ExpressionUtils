import math
import logging
import time
import sys
import urllib

from GenomeSearchUtil.GenomeSearchUtilClient import GenomeSearchUtil


def get_logger():
    logger = logging.getLogger('ExpressionUtils.core.expression_utils')
    logger.setLevel(logging.INFO)
    streamHandler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s")
    formatter.converter = time.gmtime
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    logger.info("Logger was set")
    return logger


class ExpressionUtils:
    """
     Constains a set of functions for expression levels calculations.
    """

    def _get_feature_ids(self, genome_ref):
        """
        _get_feature_ids: get feature ids from genome
        """
        self.logger.info("Matching to features from genome {}"
                         .format(genome_ref))

        feature_num = self.gsu.search({'ref': genome_ref})['num_found']

        genome_features = self.gsu.search({'ref': genome_ref,
                                           'limit': feature_num,
                                           'sort_by': [['feature_id', True]]})['features']

        features_ids = map(lambda genome_feature: genome_feature.get('feature_id'),
                           genome_features)

        return list(set(features_ids))

    def __init__(self, config, logger=None):
        self.config = config
        if logger is not None:
            self.logger = logger
        else:
            self.logger = get_logger()

        callback_url = self.config['SDK_CALLBACK_URL']
        self.gsu = GenomeSearchUtil(callback_url)

    def get_expression_levels(self, filepath, genome_ref, id_col=0):
        """
         Returns FPKM and TPM expression levels.
         # (see discussion @ https://www.biostars.org/p/160989/)

        :param filename: An FPKM tracking file
        :return: fpkm and tpm expression levels as dictionaries
        """
        fpkm_dict = {}
        tpm_dict = {}

        # get FPKM col index
        try:
            with open(filepath, 'r') as file:
                header = file.readline()
                fpkm_col = header.strip().split('\t').index('FPKM')
                self.logger.info('Using FPKM at col ' + str(fpkm_col) + ' in ' + str(filepath))
        except:
            self.logger.error('Unable to find an FPKM column in the specified file: ' + str(filepath))

        feature_ids = self._get_feature_ids(genome_ref)

        sum_fpkm = 0.0
        with open(filepath) as f:
            next(f)
            for line in f:
                larr = urllib.unquote(line).split("\t")

                if larr[id_col] in feature_ids:
                    gene_id = larr[id_col]
                elif larr[1] in feature_ids:
                    gene_id = larr[1]
                else:
                    error_msg = 'Line does not include a known feature: {}'.format(line)
                    raise ValueError(error_msg)

                if gene_id != "":
                    fpkm = float(larr[fpkm_col])
                    sum_fpkm = sum_fpkm + fpkm
                    fpkm_dict[gene_id] = math.log(fpkm + 1, 2)
                    tpm_dict[gene_id] = fpkm

        if sum_fpkm == 0:
            self.logger.error("Unable to compute TPM values as sum of FPKM values is 0")
        else:
            for g in tpm_dict:
                tpm_dict[g] = math.log((tpm_dict[g] / sum_fpkm) * 1e6 + 1, 2)

        return fpkm_dict, tpm_dict
