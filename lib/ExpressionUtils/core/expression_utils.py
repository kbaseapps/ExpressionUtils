import logging
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import json

from installed_clients.GenomeSearchUtilClient import GenomeSearchUtil
from installed_clients.MetagenomeAPIClient import MetagenomeAPI
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.WorkspaceClient import Workspace


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

    def _get_feature_ids(self, genome_or_ama_ref):
        """
        _get_feature_ids: get feature ids from genome
        """
        self.logger.info("Matching to features from genome or AMA {}"
                         .format(genome_or_ama_ref))

        ref = self.ws.get_object_subset(
            [{"ref": genome_or_ama_ref, "included": ["features_handle_ref"]}]
        )

        obj_type = ref[0]['info'][2]

        if 'KBaseGenomes.Genome' in obj_type:
            feature_num = self.gsu.search({'ref': genome_or_ama_ref})['num_found']

            genome_features = self.gsu.search({'ref': genome_or_ama_ref,
                                               'limit': feature_num,
                                               'sort_by': [['feature_id', True]]})['features']

            features_ids = [genome_feature.get('feature_id') for genome_feature in genome_features]
        elif 'KBaseMetagenomes.AnnotatedMetagenomeAssembly' in obj_type:
            feature_num = self.msu.search({'ref': genome_or_ama_ref})['num_found']
            self.logger.info('Found {} AMA features'.format(feature_num))

            chunk_size = 300
            chunk_num = feature_num//chunk_size + 1
            features_ids = list()

            for i in range(chunk_num):

                search_params = {
                    'ref': genome_or_ama_ref,
                    'sort_by': [('id', 1)],
                    'start': i*chunk_size,
                    'limit': chunk_size
                }

                try:
                    genome_features = self.msu.search(search_params)['features']
                    chuck_ids = [genome_feature.get('feature_id') for genome_feature in genome_features]
                    features_ids.extend(chuck_ids)
                except Exception:
                    self.logger.warning('Failed to fetch features started at {}'.format(i*chunk_size))
                    # reached to the end of indexed features
                    break

            if len(features_ids) < feature_num or feature_num == 0:
                # try to fetch the rest of features from linked json file
                try:
                    features_handle_ref = ref[0]["data"]["features_handle_ref"]
                    features_handle_file = self.dfu.shock_to_file({'handle_id': features_handle_ref,
                                                                   'file_path': self.config['scratch'],
                                                                   'unpack': 'unpack'})['file_path']

                    with open(features_handle_file) as json_file:
                        data = json.load(json_file)

                    features_ids.extend([feature.get('id') for feature in data])

                except Exception as err:
                    self.logger.warning('Failed to fetch features from features json file\n{}'.format(err))

        return list(set(features_ids))

    def __init__(self, config, logger=None):
        self.config = config
        if logger is not None:
            self.logger = logger
        else:
            self.logger = get_logger()

        callback_url = self.config['SDK_CALLBACK_URL']
        self.gsu = GenomeSearchUtil(callback_url)
        self.msu = MetagenomeAPI(callback_url, service_ver='dev')
        self.dfu = DataFileUtil(callback_url)

        ws_url = self.config['workspace-url']
        self.ws = Workspace(ws_url)

    def get_expression_levels(self, filepath, genome_or_ama_ref, id_col=0):
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
                self.logger.info(f'Using FPKM at col {fpkm_col} in {filepath}')
        except:
            self.logger.error(f'Unable to find an FPKM column in the specified file: {filepath}')

        feature_ids = self._get_feature_ids(genome_or_ama_ref)

        sum_fpkm = 0.0
        with open(filepath) as f:
            next(f)
            for line in f:
                larr = urllib.parse.unquote(line).split("\t")

                if larr[id_col] in feature_ids:
                    gene_id = larr[id_col]
                elif larr[1] in feature_ids:
                    gene_id = larr[1]
                else:
                    error_msg = f'Line does not include a known feature: {line}'
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
