# -*- coding: utf-8 -*-
import glob
import logging
import os  # noqa: F401
import sys
import time
import unittest
from configparser import ConfigParser
from os import environ

from ExpressionUtils.ExpressionUtilsImpl import ExpressionUtils
from ExpressionUtils.ExpressionUtilsServer import MethodContext
from ExpressionUtils.authclient import KBaseAuth as _KBaseAuth
from ExpressionUtils.core.table_maker import TableMaker
from installed_clients.WorkspaceClient import Workspace as workspaceService


class TableMakerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__LOGGER = logging.getLogger('TableMaker_test')
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
        cls.wsClient = workspaceService(cls.wsURL)
        cls.serviceImpl = ExpressionUtils(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']

    def test_build_ctab_files(self):
        output_dir = '/kb/module/work/tablemaker_test'

        try:
            os.mkdir(output_dir)
        except OSError:
            pass  # dir already exists

        map(os.remove, glob.glob(output_dir + '/*.ctab'))

        tablemaker = TableMaker(self.__class__.cfg, self.__class__.__LOGGER)

        # ref_genome_path, alignment_path, output_dir
        result = tablemaker.build_ctab_files(
            ref_genome_path='data/tablemaker/at_chrom1_section.gtf',
            alignment_path='data/tablemaker/accepted_hits_sorted.bam',
                            output_dir=output_dir)

        self.assertEqual(result, 0)
        self.assertTrue(os.path.exists(os.path.join(output_dir, 'e2t.ctab')))
        self.assertTrue(os.path.exists(os.path.join(output_dir, 'e_data.ctab')))
        self.assertTrue(os.path.exists(os.path.join(output_dir, 'i2t.ctab')))
        self.assertTrue(os.path.exists(os.path.join(output_dir, 'i_data.ctab')))
        self.assertTrue(os.path.exists(os.path.join(output_dir, 't_data.ctab')))
