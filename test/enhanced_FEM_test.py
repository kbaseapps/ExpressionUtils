# -*- coding: utf-8 -*-
import unittest
import os  # noqa: F401
import time
import inspect
import shutil
import json

from os import environ

try:
    from ConfigParser import ConfigParser  # py2
except BaseException:
    from configparser import ConfigParser  # py3

from pprint import pprint, pformat  # noqa: F401

from biokbase.workspace.client import Workspace as workspaceService
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.GenomeFileUtilClient import GenomeFileUtil
from ExpressionUtils.ExpressionUtilsImpl import ExpressionUtils
from ExpressionUtils.ExpressionUtilsServer import MethodContext
from ExpressionUtils.authclient import KBaseAuth as _KBaseAuth
from installed_clients.GenomeAnnotationAPIClient import GenomeAnnotationAPI

class ExprMatrixUtilsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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
        suffix = int(time.time() * 1000)
        cls.wsName = "test_exprMatrixUtils_" + str(suffix)
        cls.wsClient.create_workspace({'workspace': cls.wsName})
        cls.serviceImpl = ExpressionUtils(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        cls.dfu = DataFileUtil( cls.callback_url )
        cls.ws_id = cls.dfu.ws_name_to_id(cls.wsName)
        cls.gaa = GenomeAnnotationAPI( cls.callback_url )
        cls.gfu = GenomeFileUtil(cls.callback_url)
        cls.setupdata()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def getWsClient(self):
        return self.__class__.wsClient

    def getWsName(self):
        return self.__class__.wsName

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    @classmethod
    def setupdata(cls):

        # 
        # load genome first
        #
        genome_file_name = 'eFEM_test_genome.json'
        genome_file_path = os.path.join('data', genome_file_name)

        with open( genome_file_path ) as genome_file:  
            genome = json.load( genome_file )

            gen_info = cls.gaa.save_one_genome_v1( { 'workspace': cls.wsName,
                                                     'data': genome,
                                                     'name': 'at'
                                                 } ).get('info')
            cls.genome_ref = "{0}/{1}/{2}".format( gen_info[6], gen_info[0], gen_info[4] )

        # Read DEM test object and save

        dem_file_name = "eFEM_test_dem.json"
        dem_file_path = os.path.join('data', dem_file_name)
        with open( dem_file_path ) as dem_file:  
            dem = json.load( dem_file )
            dem["genome_ref"] = cls.genome_ref

            dem_info = cls.dfu.save_objects( { 'id': cls.ws_id, 
                                               'objects': [ {'type': 'KBaseFeatureValues.DifferentialExpressionMatrix', 
                                                             'data': dem, 
                                                             'name': 'dem'} ]
                                           } )[0]
            cls.dem_ref = "{0}/{1}/{2}".format( dem_info[6], dem_info[0], dem_info[4] )

        # Read FEM test object and save

        fem_file_name = "eFEM_test_fem.json"
        fem_file_path = os.path.join('data', fem_file_name)
        with open( fem_file_path ) as fem_file:
            fem = json.load( fem_file )
            fem["genome_ref"] = cls.genome_ref

            # fem data should not have diff_expr_matrix_ref, so we'll save without first
            # Save without DEM provenance

            fem_info = cls.dfu.save_objects( { 'id': cls.ws_id, 
                                               'objects': [ {'type': 'KBaseFeatureValues.ExpressionMatrix', 
                                                             'data': fem, 
                                                             'name': 'fem_no_dem',
                                                             'extra_provenance_input_refs': [cls.dem_ref]
                                                            } ]
                                           } )[0]
            cls.fem_no_dem_ref = "{0}/{1}/{2}".format( fem_info[6], fem_info[0], fem_info[4] )

            # and now save WITH DEM  rever

            fem["diff_expr_matrix_ref"] = cls.dem_ref
            fem_info = cls.dfu.save_objects( { 'id': cls.ws_id, 
                                               'objects': [ {'type': 'KBaseFeatureValues.ExpressionMatrix', 
                                                             'data': fem, 
                                                             'name': 'fem',
                                                             'extra_provenance_input_refs': [cls.dem_ref]
                                                          } ]
                                           } )[0]
            cls.fem_dem_ref = "{0}/{1}/{2}".format( fem_info[6], fem_info[0], fem_info[4] )


    def fc_and_q_columns_are_all_NA( self, efem ):

        for valrow in efem.get('data').get('values'):
            if ( valrow[1] != 'NA' or valrow[2] != 'NA' ):
                return( False )
        return( True )
        
    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa

    def get_enhancedFEM_tests( self ):

        print "### running enhanced FEM tests...."

        # this should succeed - good provenance link to DEM
        
        print "### testing good provenance...."
        ret = self.getImpl().get_enhancedFilteredExpressionMatrix( self.ctx, 
                                                            {'fem_object_ref': self.fem_dem_ref} )
        self.assertFalse( self.fc_and_q_columns_are_all_NA( ret[0].get('enhanced_FEM' ) ) )
        print "### ret is {0}".format( pformat( ret ) )

        # this should succeed - no provenance link to DEM

        print "### testing, no provenance...."
        ret = self.getImpl().get_enhancedFilteredExpressionMatrix( self.ctx, 
                                                            {'fem_object_ref': self.fem_no_dem_ref} )
        self.assertTrue( self.fc_and_q_columns_are_all_NA( ret[0].get('enhanced_FEM' ) ) )
        print "### ret is {0}".format( pformat( ret ) )

        # this should fail: the one input parameter is missing..

        print "### fail check on missing parameter field...."
        with self.assertRaisesRegexp(
                      ValueError, 'fem_object_ref parameter not given to get_enhancedFilteredExpressionMatrix' ):
             self.getImpl().get_enhancedFilteredExpressionMatrix( self.ctx, 
                                                            {'nope': 'nope'} )
        print "### finished running enhanced FEM tests...."
