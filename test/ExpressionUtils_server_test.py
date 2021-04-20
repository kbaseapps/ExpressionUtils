# -*- coding: utf-8 -*-
import hashlib
import inspect
import os  # noqa: F401
import shutil
import tempfile
import time
import unittest
from configparser import ConfigParser  # py3
from datetime import datetime
from distutils.dir_util import copy_tree
from os import environ
from pprint import pprint
from unittest.mock import patch
from zipfile import ZipFile

import requests

from ExpressionUtils.ExpressionUtilsImpl import ExpressionUtils
from ExpressionUtils.ExpressionUtilsServer import MethodContext
from ExpressionUtils.authclient import KBaseAuth as _KBaseAuth
from ExpressionUtils.core.expression_utils import ExpressionUtils as Expression_Utils
from installed_clients.AbstractHandleClient import AbstractHandle as HandleService
from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.GenomeAnnotationApiServiceClient import GenomeAnnotationAPI
from installed_clients.GenomeFileUtilClient import GenomeFileUtil
from installed_clients.ReadsAlignmentUtilsClient import ReadsAlignmentUtils
from installed_clients.ReadsUtilsClient import ReadsUtils
from installed_clients.WorkspaceClient import Workspace
from installed_clients.WorkspaceClient import Workspace as workspaceService


def dictmerge(x, y):
    z = x.copy()
    z.update(y)
    return z


def mock_get_feature_ids(_):
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

    # includes features in t_data.ctab
    feature_ids += ['AT1G01010.1', 'AT1G01020.1', 'AT1G01020.2',
                    'AT1G01030.1', 'AT1G01040.1', 'AT1G01046.1']

    return feature_ids


class ExpressionUtilsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = environ.get('KB_AUTH_TOKEN', None)
        cls.callbackURL = environ.get('SDK_CALLBACK_URL')
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('ExpressionUtils'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(cls.token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': cls.token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'ExpressionUtils',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.shockURL = cls.cfg['shock-url']
        cls.wsURL = cls.cfg['workspace-url']
        cls.service_wizard_url = cls.cfg['srv-wiz-url']
        cls.wsClient = workspaceService(cls.wsURL)
        cls.ws = Workspace(cls.wsURL, token=cls.token)
        cls.hs = HandleService(url=cls.cfg['handle-service-url'],
                               token=cls.token)
        # create workspace
        wssuffix = int(time.time() * 1000)
        wsname = "test_expression_" + str(wssuffix)
        cls.wsinfo = cls.wsClient.create_workspace({'workspace': wsname})
        print('created workspace ' + cls.getWsName())

        cls.serviceImpl = ExpressionUtils(cls.cfg)
        cls.readUtils = ReadsUtils(cls.callbackURL)
        cls.dfu = DataFileUtil(cls.callbackURL)
        cls.assemblyUtil = AssemblyUtil(cls.callbackURL)
        cls.gfu = GenomeFileUtil(cls.callbackURL)
        cls.gaAPI = GenomeAnnotationAPI(cls.service_wizard_url)
        cls.rau = ReadsAlignmentUtils(cls.callbackURL)
        cls.scratch = cls.cfg['scratch']

        cls.staged = {}
        cls.nodes_to_delete = []
        cls.handles_to_delete = []
        # cls.setupTestData()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')
        if hasattr(cls, 'nodes_to_delete'):
            for node in cls.nodes_to_delete:
                cls.delete_shock_node(node)
        # if hasattr(cls, 'handles_to_delete'):
        #     cls.hs.delete_handles(cls.hs.ids_to_handles(cls.handles_to_delete))
        #     print('Deleted handles ' + str(cls.handles_to_delete))

    def getWsClient(self):
        return self.wsClient

    @classmethod
    def getWsName(cls):
        return cls.wsinfo[1]

    @classmethod
    def getImpl(cls):
        return cls.serviceImpl

    def getContext(self):
        return self.ctx

    @classmethod
    def make_ref(cls, objinfo):
        return str(objinfo[6]) + '/' + str(objinfo[0]) + '/' + str(objinfo[4])

    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.token)}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
        print('Deleted shock node ' + node_id)

    @classmethod
    def upload_file_to_shock(cls, file_path):
        """
        Use DataFileUtil.file_to_shock() save a file to a SHOCK instance.
        """

        if file_path is None:
            raise Exception("No file given for upload to SHOCK!")

        # copy file to where DFU can see it (can only see scratch)
        src_file_basename = os.path.basename(file_path)
        shared_file_path = os.path.join(cls.scratch, src_file_basename)
        shutil.copy2(file_path, shared_file_path)

        # Upload files to shock
        try:
            shock_info = cls.dfu.file_to_shock({
                'file_path': shared_file_path,
                'make_handle': 1
            })
        except Exception as e:
            raise ValueError('Unable to store ' + file_path + str(e))

        # remember shock info
        if not hasattr(cls, 'shock_ids'):
            cls.shock_ids = []
        cls.shock_ids.append(shock_info['shock_id'])
        return shock_info

    @classmethod
    def upload_file_to_shock_and_get_handle(cls, test_file):
        """
        Uploads the file in test_file to shock and returns the node and a
        handle to the node.
        """
        print('loading file to shock: ' + test_file)
        node = cls.upload_file_to_shock(test_file)
        pprint(node)
        cls.nodes_to_delete.append(node['shock_id'])

        print('creating handle for shock id ' + node['shock_id'])
        handle_id = cls.hs.persist_handle({'id': node['shock_id'],
                                           'type': 'shock',
                                           'url': cls.shockURL
                                           })
        cls.handles_to_delete.append(handle_id)

        md5 = node['handle']['remote_md5']
        return node['shock_id'], handle_id, md5, node['size']

    @classmethod
    def upload_reads(cls, wsobjname, object_body, fwd_reads,
                     rev_reads=None, single_end=False, sequencing_tech='Illumina',
                     single_genome='1'):

        ob = dict(object_body)  # copy
        ob['sequencing_tech'] = sequencing_tech
        #        ob['single_genome'] = single_genome
        ob['wsname'] = cls.getWsName()
        ob['name'] = wsobjname
        if single_end or rev_reads:
            ob['interleaved'] = 0
        else:
            ob['interleaved'] = 1
        print('uploading forward reads file ' + fwd_reads['file'])
        fwd_id, fwd_handle_id, fwd_md5, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(fwd_reads['file'])

        ob['fwd_id'] = fwd_id
        rev_id = None
        rev_handle_id = None
        if rev_reads:
            print('uploading reverse reads file ' + rev_reads['file'])
            rev_id, rev_handle_id, rev_md5, rev_size = \
                cls.upload_file_to_shock_and_get_handle(rev_reads['file'])
            ob['rev_id'] = rev_id
        obj_ref = cls.readUtils.upload_reads(ob)
        objdata = cls.wsClient.get_object_info_new({
            'objects': [{'ref': obj_ref['obj_ref']}]
        })[0]
        cls.staged[wsobjname] = {'info': objdata,
                                 'ref': cls.make_ref(objdata),
                                 'fwd_node_id': fwd_id,
                                 'rev_node_id': rev_id,
                                 'fwd_handle_id': fwd_handle_id,
                                 'rev_handle_id': rev_handle_id
                                 }

    @classmethod
    def upload_genome(cls, wsobj_name, file_name):
        genbank_file_path = os.path.join(cls.scratch, file_name)
        shutil.copy(os.path.join('data', file_name), genbank_file_path)
        genome_obj = cls.gfu.genbank_to_genome({'file': {'path': genbank_file_path},
                                                'workspace_name': cls.getWsName(),
                                                'genome_name': wsobj_name,
                                                'source': 'Ensembl',
                                                'generate_ids_if_needed': 1,
                                                'generate_missing_genes': 1
                                                })
        cls.staged[wsobj_name] = {'info': genome_obj['genome_info'],
                                  'ref': genome_obj['genome_ref']}

    @classmethod
    def upload_assembly(cls, wsobj_name, file_name):
        fasta_path = os.path.join(cls.scratch, file_name)
        shutil.copy(os.path.join('data', file_name), fasta_path)
        assembly_ref = cls.assemblyUtil.save_assembly_from_fasta({'file': {'path': fasta_path},
                                                                  'workspace_name': cls.getWsName(),
                                                                  'assembly_name': wsobj_name
                                                                  })

        objinfo = cls.wsClient.get_object_info_new({'objects': [{'ref': assembly_ref}]})[0]

        cls.staged[wsobj_name] = {'info': None,
                                  'ref': assembly_ref}

    @classmethod
    def upload_alignment_with_genome(cls, wsobjname, file_name):
        align_path = os.path.join(cls.scratch, file_name)
        shutil.copy(os.path.join('data', file_name), align_path)
        align_info = cls.rau.upload_alignment({'file_path': align_path,
                                               'destination_ref': cls.getWsName() + '/' + wsobjname,
                                               'read_library_ref': cls.getWsName() + '/test_reads',
                                               'condition': 'test_condition',
                                               #'assembly_or_genome_ref': cls.getWsName()+'/test_genome'
                                               'assembly_or_genome_ref': cls.getWsName() + '/test_genome'
                                               })
        cls.staged[wsobjname] = {'info': align_info,
                                 'ref': align_info['obj_ref']}

    @classmethod
    def upload_alignment_with_assembly(cls, wsobjname, file_name):
        align_path = os.path.join(cls.scratch, file_name)
        shutil.copy(os.path.join('data', file_name), align_path)
        align_info = cls.rau.upload_alignment({'file_path': align_path,
                                               'destination_ref': cls.getWsName() + '/' + wsobjname,
                                               'read_library_ref': cls.getWsName() + '/test_reads',
                                               'condition': 'test_condition',
                                               # 'assembly_or_genome_ref': cls.getWsName()+'/test_genome'
                                               'assembly_or_genome_ref': cls.getWsName() + '/test_assembly'
                                               })
        cls.staged[wsobjname] = {'info': align_info,
                                 'ref': align_info['obj_ref']}

    @classmethod
    def upload_empty_data(cls, wsobjname):
        objdata = cls.wsClient.save_objects({
            'workspace': cls.getWsName(),
            'objects': [{'type': 'Empty.AType',
                         'data': {},
                         'name': 'empty'
                         }]
        })[0]
        cls.staged[wsobjname] = {'info': objdata,
                                 'ref': cls.make_ref(objdata),
                                 }

    @classmethod
    def save_ws_obj(cls, obj, objname, objtype):

        return cls.ws.save_objects({
            'workspace': cls.getWsName(),
            'objects': [{'type': objtype,
                         'data': obj,
                         'name': objname
                         }]
        })[0]

    @classmethod
    def upload_annotation(cls, wsobjname, file_name):
        id, handle_id, md5, size = cls.upload_file_to_shock_and_get_handle(os.path.join('data', file_name))

        a_handle = {
            'hid': handle_id,
            'file_name': file_name,
            'id': id,
            "type": "KBaseRNASeq.GFFAnnotation",
            'url': cls.shockURL,
            'type': 'shock',
            'remote_md5': md5
        }
        obj = {
                "size": size,
                "handle": a_handle,
                "genome_id": "test_genome_GTF_Annotation",
                "genome_scientific_name": "scientific name"
              }
        res = cls.save_ws_obj(obj, wsobjname, "KBaseRNASeq.GFFAnnotation")
        return cls.make_ref(res)

    @classmethod
    @patch.object(Expression_Utils, "_get_feature_ids", side_effect=mock_get_feature_ids)
    def setupTestData(cls, _get_feature_ids):
        """
        sets up files for upload
        """
        timestamp = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds() * 1000)
        cls.upload_stringtie_dir = 'upload_stringtie_' + str(timestamp)
        cls.upload_stringtie_dir_path = os.path.join(cls.scratch, cls.upload_stringtie_dir)
        cls.uploaded_stringtie_zip = cls.upload_stringtie_dir + '.zip'

        cls.upload_cufflinks_dir = 'upload_cufflinks_' + str(timestamp)
        cls.upload_cufflinks_dir_path = os.path.join(cls.scratch, cls.upload_cufflinks_dir)
        cls.uploaded_cufflinks_zip = cls.upload_cufflinks_dir + '.zip'

        copy_tree('data/stringtie_output', cls.upload_stringtie_dir_path)
        copy_tree('data/cufflinks_output', cls.upload_cufflinks_dir_path)

        # uploads reads, genome and assembly to be used as input parameters to upload_expression

        cls.upload_genome('test_genome', 'minimal.gbff')
        annotation_ref = cls.upload_annotation('test_annotation', 'test.gtf')

        int_reads = {'file': 'data/interleaved.fq',
                     'name': '',
                     'type': ''}
        cls.upload_reads('test_reads', {'single_genome': 1}, int_reads)
        cls.upload_empty_data('empty')

        cls.upload_assembly('test_assembly', 'test.fna')
        cls.upload_alignment_with_genome('test_alignment_genome', 'alignment.bam')
        cls.upload_alignment_with_assembly('test_alignment_assembly', 'alignment.bam')

        cls.more_upload_stringtie_params = {
                                  'alignment_ref': cls.getWsName() + '/test_alignment_genome'
                                 }
        cls.more_upload_cufflinks_params = {
                                'alignment_ref': cls.getWsName() + '/test_alignment_genome'
        }
        cls.stringtie_params = {'destination_ref': cls.getWsName() + '/test_stringtie_expression',
                                'source_dir': cls.upload_stringtie_dir_path,
                                'alignment_ref': cls.getWsName() + '/test_alignment_genome'
                                }

        cls.cufflinks_params = {'destination_ref': cls.getWsName() + '/test_cufflinks_expression',
                                'source_dir': cls.upload_cufflinks_dir_path,
                                'alignment_ref': cls.getWsName() + '/test_alignment_genome'
                                }
        cls.transcript_params = {
            'destination_ref': cls.getWsName() + '/test_transcript_expression',
            'source_dir': cls.upload_stringtie_dir_path,
            'alignment_ref': cls.getWsName() + '/test_alignment_genome',
            'transcripts': 1
            }

        cls.getImpl().upload_expression(cls.ctx, cls.stringtie_params)
        cls.getImpl().upload_expression(cls.ctx, cls.cufflinks_params)
        cls.getImpl().upload_expression(cls.ctx, cls.transcript_params)

        cls.upload_ret_data_only = cls.getImpl().upload_expression(
                                    cls.ctx,
                                    {**cls.stringtie_params, **{'generate_data_only': True}})[0]

    @classmethod
    def getSize(cls, filename):
        return os.path.getsize(filename)

    @classmethod
    def md5(cls, filename):
        with open(filename, 'rb') as file_:
            hash_md5 = hashlib.md5()
            buf = file_.read(65536)
            while len(buf) > 0:
                hash_md5.update(buf)
                buf = file_.read(65536)
            return hash_md5.hexdigest()

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa

    def upload_expression_success(self, params, expected_zip):

        test_name = inspect.stack()[1][3]
        print('\n**** starting expected upload expression success test: ' + test_name + ' ***\n')
        print('---------------------------------------------------------------------------------')
        obj = self.dfu.get_objects(
            {'object_refs': [params.get('destination_ref')]})['data'][0]

        print("============ GET OBJECTS OUTPUT ==============")
        pprint(obj)
        print("==============================================")

        self.assertEqual(obj['info'][2].startswith('KBaseRNASeq.RNASeqExpression'), True)
        d = obj['data']
        #self.assertEqual(d['genome_ref'], self.getWsName() + '/test_genome')
        self.assertEqual(d['condition'], 'test_condition')
        self.assertEqual(list(d['mapped_rnaseq_alignment'].keys())[0],
                         self.getWsName() + '/test_reads')
        f = d['file']
        self.assertEqual(f['file_name'], expected_zip)
        self.assertEqual(f['remote_md5'], self.md5(os.path.join(self.scratch, expected_zip)))

        self.handles_to_delete.append(f['id'])

    def check_files(self, new_dir, orig_dir):

        self.assertEqual(len(os.listdir(new_dir)),
                         len(os.listdir(orig_dir)))

        for new_file in os.listdir(new_dir):
            new_file_path = os.path.join(new_dir, new_file)
            orig_file_path = os.path.join(orig_dir, new_file)

            self.assertEqual(self.getSize(new_file_path), self.getSize(orig_file_path))
            self.assertEqual(self.md5(new_file_path), self.md5(orig_file_path))

            print("Files checked: " + new_file_path + ', ' + orig_file_path)

    def download_expression_success(self, obj_name, upload_dir_path):

        test_name = inspect.stack()[1][3]
        print('\n**** starting expected download expression success test: ' + test_name + ' ***\n')

        params = {'source_ref': self.getWsName() + '/' + obj_name}

        ret = self.getImpl().download_expression(self.ctx, params)[0]
        print("=================  DOWNLOADED FILES =================== ")
        pprint(ret)
        print("========================================================")

        self.check_files(ret['destination_dir'], upload_dir_path)

    def test__get_feature_ids(self):

        name_ref = "KBaseTestData/metagenome_badabing.assembly.fa_metagenome/1"
        ref = self.wsClient.get_objects2({'objects': [{'ref': name_ref}]})['data'][0]['path'][0]

        expression_utils = Expression_Utils(self.cfg)
        features_ids = expression_utils._get_feature_ids(ref)

        expected_sub_feature_ids = ['Ga0065724_100001.1', 'Ga0065724_100001.100',
                                    'Ga0065724_100001.1000_gene', 'Ga0065724_100001.1007',
                                    'Ga0065724_100001.1003', 'Ga0065724_100001.1000',
                                    'Ga0065724_100001.1003_gene', 'Ga0065724_100001.1007_gene',
                                    'Ga0065724_100001.100_gene', 'Ga0065724_100001.1010']
        self.assertTrue(set(expected_sub_feature_ids) < set(features_ids))
        self.assertEqual(len(features_ids), 265441)

    # def test_upload_stringtie_expression_success(self):

    #     self.upload_expression_success(self.stringtie_params, self.uploaded_stringtie_zip)

    # def test_upload_return_data_only_success(self):

    #     self.assertFalse('obj_ref' in self.upload_ret_data_only)

    #     self.assertTrue('obj_data' in self.upload_ret_data_only)
    #     obj_data = self.upload_ret_data_only['obj_data']

    #     self.assertTrue('tpm_expression_levels' in obj_data)
    #     self.assertTrue('expression_levels' in obj_data)
    #     self.assertEqual(len(obj_data['tpm_expression_levels'].keys()), 10)
    #     self.assertCountEqual(obj_data['tpm_expression_levels'].keys(),
    #                           obj_data['expression_levels'].keys())

    # def test_upload_stringtie_assembly_expression_success(self):

    #     params = {'destination_ref': self.getWsName() + '/test_stringtie_expression',
    #               'source_dir': self.upload_stringtie_dir_path,
    #               'alignment_ref': self.getWsName() + '/test_alignment_assembly',
    #               'genome_ref': self.getWsName() + '/test_genome'}
    #     self.upload_expression_success(params, self.uploaded_stringtie_zip)

    # def test_upload_stringtie_transcripts_expression_success(self):

    #     self.upload_expression_success(self.transcript_params, self.uploaded_stringtie_zip)

    # def test_upload_cufflinks_expression_success(self):
    #     self.upload_expression_success(self.cufflinks_params, self.uploaded_cufflinks_zip)

    # def test_download_stringtie_expression_success(self):
    #     self.download_expression_success('test_stringtie_expression', self.upload_stringtie_dir_path)

    # def test_download_cufflinks_expression_success(self):
    #     self.download_expression_success('test_cufflinks_expression', self.upload_cufflinks_dir_path)

    # def export_expression_success(self, obj_name, export_params,
    #                               upload_dir, upload_dir_path, uploaded_zip):

    #     test_name = inspect.stack()[1][3]
    #     print('\n*** starting expected export pass test: ' + test_name + ' **')
    #     export_params['source_ref'] = self.getWsName() + '/' + obj_name
    #     shocknode = self.getImpl().export_expression(self.ctx, export_params)[0]['shock_id']
    #     node_url = self.shockURL + '/node/' + shocknode
    #     headers = {'Authorization': 'OAuth ' + self.token}
    #     r = requests.get(node_url, headers=headers, allow_redirects=True)
    #     fn = r.json()['data']['file']['name']
    #     self.assertEqual(fn, uploaded_zip)
    #     temp_dir = tempfile.mkdtemp(dir=self.scratch)
    #     export_dir = upload_dir.replace('upload', 'export')
    #     export_dir_path = os.path.join(temp_dir, export_dir)
    #     export_file_path = export_dir_path + '.zip'
    #     print('export file path: ' + export_file_path)
    #     print('downloading shocknode ' + shocknode)
    #     with open(export_file_path, 'wb') as fhandle:
    #         r = requests.get(node_url + '?download_raw', stream=True,
    #                          headers=headers, allow_redirects=True)
    #         for chunk in r.iter_content(1024):
    #             if not chunk:
    #                 break
    #             fhandle.write(chunk)
    #     with ZipFile(export_file_path) as z:
    #         z.extractall(export_dir_path)

    #     self.check_files(export_dir_path, upload_dir_path)

    # def test_export_stringtie_expression_success(self):

    #     opt_params = {}
    #     self.export_expression_success('test_stringtie_expression',
    #                                    opt_params,
    #                                    self.upload_stringtie_dir,
    #                                    self.upload_stringtie_dir_path,
    #                                    self.uploaded_stringtie_zip)

    # def test_export_cufflinks_expression_success(self):

    #     opt_params = {}
    #     self.export_expression_success('test_cufflinks_expression',
    #                                    opt_params,
    #                                    self.upload_cufflinks_dir,
    #                                    self.upload_cufflinks_dir_path,
    #                                    self.uploaded_cufflinks_zip)

    # def fail_upload_expression(self, params, error, exception=ValueError):

    #     test_name = inspect.stack()[1][3]
    #     print('\n*** starting expected upload fail test: ' + test_name + ' **')

    #     with self.assertRaisesRegex(exception, error):
    #         self.getImpl().upload_expression(self.ctx, params)

    # def test_upload_fail_no_dst_ref(self):
    #     self.fail_upload_expression(
    #         dictmerge({
    #                     'condition': 'bar',
    #                     'source_dir': 'test'
    #                    }, self.more_upload_stringtie_params),
    #         'destination_ref parameter is required')

    # def test_upload_fail_no_ws_name(self):
    #     self.fail_upload_expression(
    #         dictmerge({
    #                      'condition': 'bar',
    #                      'destination_ref': '/foo',
    #                      'source_dir': 'test'
    #                    }, self.more_upload_stringtie_params),
    #         'Workspace name or id is required in destination_ref')

    # def test_upload_fail_no_obj_name(self):
    #     self.fail_upload_expression(
    #         dictmerge({
    #                      'condition': 'bar',
    #                      'destination_ref': self.getWsName() + '/',
    #                      'source_dir': 'test'
    #                    }, self.more_upload_stringtie_params),
    #         'Object name or id is required in destination_ref')

    # def test_upload_fail_no_file(self):
    #     self.fail_upload_expression(
    #         dictmerge({
    #                      'destination_ref': self.getWsName()+'/foo'
    #                    }, self.more_upload_stringtie_params),
    #         'source_dir parameter is required')

    # def test_upload_fail_non_existant_file(self):
    #     self.fail_upload_expression(
    #         dictmerge({
    #                     'destination_ref': self.getWsName()+'/foo',
    #                     'source_dir': 'foo'
    #                   }, self.more_upload_stringtie_params),
    #         'Source directory does not exist: foo')

    # def test_upload_fail_bad_wsname(self):
    #     self.fail_upload_expression(
    #         dictmerge({
    #                     'destination_ref': '&bad' + '/foo',
    #                     'source_dir': 'foo'
    #                       }, self.more_upload_stringtie_params),
    #         'Illegal character in workspace name &bad: &')

    # def test_upload_fail_non_existant_wsname(self):
    #     self.fail_upload_expression(
    #         dictmerge({
    #                     'destination_ref': '1s' + '/foo',
    #                     'source_dir': 'bar'
    #                   }, self.more_upload_stringtie_params),
    #         'No workspace with name 1s exists')

    # def test_upload_fail_no_genome_ref(self):
    #     self.fail_upload_expression(
    #         {
    #             'destination_ref': self.getWsName() + '/test_stringtie_expression',
    #             'source_dir': self.upload_stringtie_dir_path,
    #             'alignment_ref': self.getWsName() + '/test_alignment_assembly'
    #             },
    #         'Alignment object does not contain genome_ref; "genome_ref" parameter is required')
