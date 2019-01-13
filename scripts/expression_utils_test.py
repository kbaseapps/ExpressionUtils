# -*- coding: utf-8 -*-
import logging
import os  # noqa: F401
import sys
import time
import unittest
from configparser import ConfigParser
from os import environ
from unittest.mock import patch

from ExpressionUtils.ExpressionUtilsServer import MethodContext
from ExpressionUtils.authclient import KBaseAuth as _KBaseAuth
from ExpressionUtils.core.expression_utils import ExpressionUtils
from installed_clients.WorkspaceClient import Workspace as workspaceService


class GFFUtilsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__LOGGER = logging.getLogger('ExpressionUtils_test')
        cls.__LOGGER.setLevel(logging.INFO)
        streamHandler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s")
        formatter.converter = time.gmtime
        streamHandler.setFormatter(formatter)
        cls.__LOGGER.addHandler(streamHandler)
        cls.__LOGGER.info("Logger was set")

        token = environ.get('KB_AUTH_TOKEN', None)
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('ExpressionUtils'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'ExpressionUtils',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        cls.cfg['SDK_CALLBACK_URL'] = cls.callback_url
        cls.wsClient = workspaceService(cls.wsURL)
        cls.serviceImpl = ExpressionUtils(cls.cfg)
        cls.scratch = cls.cfg['scratch']

    def mock_get_feature_ids(genome_ref):
        print('Mocking _get_feature_ids')

        feature_ids = []
        # includes feature ids in stringtie.genes.fpkm_tracking
        stringtie_feature_ids = ['AT1G01010', 'AT1G01020', 'AT1G01030', 'AT1G01040', 'AT1G01050', 
                                 'AT1G01060', 'AT1G01070', 'AT1G01080', 'AT1G01090', 'AT1G01100']

        feature_ids += stringtie_feature_ids

        # includes feature ids in cufflinks.genes.fpkm_tracking
        cufflinks_feature_ids = ['AT1G29740', 'AT1G29730', 'RKF1', 'SEI2', 'AT1G29770',
                                 'AT1G29775', 'AT1G29780', 'AT1G29790', 'AT1G29800', 'AT1G29810']

        feature_ids += cufflinks_feature_ids

        # incudes ids in novel_transcripts.gtf
        feature_ids += ['mRNA_1', 'mRNA_2', 'mRNA_3', 'gene_1_mRNA',
                        'MSTRG.1.1', 'MSTRG.1.2', 'MSTRG.2.1', 'MSTRG.2.2',
                        'MSTRG.3.1']

        return feature_ids

    @patch.object(ExpressionUtils, "_get_feature_ids", side_effect=mock_get_feature_ids)
    def test_bad_run_stringtie_app_params(self, _get_feature_ids):

        exp_utils = ExpressionUtils(self.__class__.cfg)  # no logger specified

        with self.assertRaisesRegex(ValueError, 'Line does not include a known feature'):
            exp_utils.get_expression_levels(filepath='data/expression_utils/missing_gene.genes.fpkm_tracking',
                                            genome_ref='')

    @patch.object(ExpressionUtils, "_get_feature_ids", side_effect=mock_get_feature_ids)
    def test_get_expression_levels_cufflinks(self, _get_feature_ids):

        exp_utils = ExpressionUtils(self.__class__.cfg, self.__class__.__LOGGER)

        fpkm_dict, tpm_dict = exp_utils.get_expression_levels(
            filepath='data/expression_utils/cufflinks.genes.fpkm_tracking',
            genome_ref='')

        self.assertEqual(10, len(fpkm_dict))
        self.assertEqual(10, len(tpm_dict))

    @patch.object(ExpressionUtils, "_get_feature_ids", side_effect=mock_get_feature_ids)
    def test_get_expression_levels_stringtie(self, _get_feature_ids):
        exp_utils = ExpressionUtils(self.__class__.cfg)  # no logger specified

        fpkm_dict, tpm_dict = exp_utils.get_expression_levels(
            filepath='data/expression_utils/stringtie.genes.fpkm_tracking',
            genome_ref='')

        self.assertEqual(10, len(fpkm_dict))
        self.assertEqual(10, len(tpm_dict))

    @patch.object(ExpressionUtils, "_get_feature_ids", side_effect=mock_get_feature_ids)
    def test_get_expression_levels_zero_sum_fpkm(self, _get_feature_ids):
        exp_utils = ExpressionUtils(self.__class__.cfg)  # no logger specified

        fpkm_dict, tpm_dict = exp_utils.get_expression_levels(
            filepath='data/expression_utils/zero_sum_fpkm.genes.fpkm_tracking',
            genome_ref='')

        self.assertEqual(10, len(fpkm_dict))
        self.assertEqual(10, len(tpm_dict))

        sum_tpm = 0.0
        for tpm in tpm_dict.values():
            sum_tpm += tpm
        self.assertEqual(0.0, sum_tpm)

    @patch.object(ExpressionUtils, "_get_feature_ids",
                  side_effect=mock_get_feature_ids)
    def test_get_transcript_expression_levels(self, _get_feature_ids):
        exp_utils = ExpressionUtils(self.__class__.cfg)  # no logger specified

        fpkm_dict, tpm_dict = exp_utils.get_expression_levels(
            filepath='data/expression_utils/t_data.ctab',
            genome_ref='', id_col=5)

        print(fpkm_dict, tpm_dict)

        expected_fpkm = {'MSTRG.1.1': 17.276905044091045, 'mRNA_1': 0.0,
                         'MSTRG.1.2': 15.496161235946962, 'mRNA_3': 0.0,
                         'MSTRG.2.2': 15.833910686877843, 'mRNA_2': 0.0,
                         'MSTRG.2.1': 16.618558913364847,
                         'MSTRG.3.1': 19.127090666492997, 'gene_1_mRNA': 0.0}
        expected_tpm = {'MSTRG.1.1': 17.37137277377277, 'mRNA_3': 0.0,
                        'MSTRG.1.2': 15.590627562938757, 'mRNA_1': 0.0,
                        'MSTRG.2.2': 15.928377426832572, 'mRNA_2': 0.0,
                        'MSTRG.2.1': 16.713026310072223,
                        'MSTRG.3.1': 19.22155881227908, 'gene_1_mRNA': 0.0}

        self.assertEqual(fpkm_dict, expected_fpkm)
        self.assertEqual(tpm_dict, expected_tpm)
