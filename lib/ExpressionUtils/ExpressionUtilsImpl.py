# -*- coding: utf-8 -*-
#BEGIN_HEADER
import glob
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pprint import pformat
from pprint import pprint

from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.ReadsAlignmentUtilsClient import ReadsAlignmentUtils
from installed_clients.WorkspaceClient import Workspace
from installed_clients.baseclient import ServerError as DFUError
from installed_clients.baseclient import ServerError as WorkspaceError
from .core.exprMatrix_utils import ExprMatrixUtils
from .core.expression_utils import ExpressionUtils as Expression_Utils
from .core.table_maker import TableMaker


#END_HEADER


class ExpressionUtils:
    '''
    Module Name:
    ExpressionUtils

    Module Description:
    
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.1.2"
    GIT_URL = "git@github.com:sean-mccorkle/ExpressionUtils.git"
    GIT_COMMIT_HASH = "d18d7ff875c006e2b6cb6a3888a3e8d507e3269d"

    #BEGIN_CLASS_HEADER

    PARAM_IN_SRC_DIR = 'source_dir'
    PARAM_IN_SRC_REF = 'source_ref'
    PARAM_IN_DST_REF = 'destination_ref'
    PARAM_IN_ALIGNMENT_REF = 'alignment_ref'

    PARAM_IN_GENOME_REF = 'genome_ref'
    PARAM_IN_ANNOTATION_ID = 'annotation_id'
    PARAM_IN_BAM_FILE_PATH = 'bam_file_path'
    PARAM_IN_DESCRIPTION = 'description'
    PARAM_IN_DATA_QUAL_LEVEL = 'data_quality_level'
    PARAM_IN_PROC_COMMENTS = 'processing_comments'
    PARAM_IN_PLATFORM = 'platform'
    PARAM_IN_MAPPED_SAMPLE_ID = 'mapped_sample_id'
    PARAM_IN_ORIG_MEDIAN = 'original_median'
    PARAM_IN_EXT_SRC_DATE = 'external_source_date'
    PARAM_IN_TRANSCRIPTS = 'transcripts'
    PARAM_IN_SRC = 'source'

    def _check_required_param(self, in_params, param_list):
        """
        Check if each of the params in the list are in the input params
        """
        for param in param_list:
            if param not in in_params or not in_params[param]:
                raise ValueError(f'{param} parameter is required')

    def _proc_ws_obj_params(self, ctx, params):
        """
        Check the validity of workspace and object params and return them
        """
        dst_ref = params.get(self.PARAM_IN_DST_REF)

        ws_name_id, obj_name_id = os.path.split(dst_ref)

        if not bool(ws_name_id.strip()) or ws_name_id == '/':
            raise ValueError("Workspace name or id is required in " + self.PARAM_IN_DST_REF)

        if not bool(obj_name_id.strip()):
            raise ValueError("Object name or id is required in " + self.PARAM_IN_DST_REF)

        if not isinstance(ws_name_id, int):

            try:
                ws_name_id = self.dfu.ws_name_to_id(ws_name_id)
            except DFUError as se:
                prefix = se.message.split('.')[0]
                raise ValueError(prefix)

        self.__LOGGER.info('Obtained workspace name/id ' + str(ws_name_id))

        return ws_name_id, obj_name_id

    def _proc_upload_expression_params(self, ctx, params):
        """
        Check the presence and validity of upload expression params
        """
        self._check_required_param(params, [self.PARAM_IN_DST_REF,
                                            self.PARAM_IN_SRC_DIR,
                                            self.PARAM_IN_ALIGNMENT_REF
                                            ])

        ws_name_id, obj_name_id = self._proc_ws_obj_params(ctx, params)

        source_dir = params.get(self.PARAM_IN_SRC_DIR)

        if not (os.path.isdir(source_dir)):
            raise ValueError('Source directory does not exist: ' + source_dir)

        if not os.listdir(source_dir):
            raise ValueError('Source directory is empty: ' + source_dir)

        return ws_name_id, obj_name_id, source_dir

    def _get_ws_info(self, obj_ref):

        ws = Workspace(self.ws_url)
        try:
            info = ws.get_object_info_new({'objects': [{'ref': obj_ref}]})[0]
        except WorkspaceError as wse:
            self.__LOGGER.error('Logging workspace exception')
            self.__LOGGER.error(str(wse))
            raise
        return info

    def _get_genome_ref(self, assembly_or_genome_ref, params):
        if self.PARAM_IN_GENOME_REF in params and params[self.PARAM_IN_GENOME_REF] is not None:
            return params[self.PARAM_IN_GENOME_REF]

        obj_type = self._get_ws_info(assembly_or_genome_ref)[2]
        if obj_type.startswith('KBaseGenomes.Genome'):
            return assembly_or_genome_ref

        raise ValueError('Alignment object does not contain genome_ref; '
                         '"{}" parameter is required'.format(self.PARAM_IN_GENOME_REF))

    def _get_expression_levels(self, source_dir, genome_ref, transcripts=False):

        fpkm_file_path = os.path.join(source_dir, 'genes.fpkm_tracking')
        if transcripts:
            fpkm_file_path = os.path.join(source_dir, 't_data.ctab')

        if not os.path.isfile(fpkm_file_path):
            raise ValueError('{} file is required'.format(fpkm_file_path))

        id_col = 5 if transcripts else 0
        self.__LOGGER.info('Generating expression levels from {}'
                           .format(fpkm_file_path))
        return self.expression_utils.get_expression_levels(fpkm_file_path,
                                                           genome_ref, id_col)

    def _gen_ctab_files(self, params, alignment_ref):

        source_dir = params.get(self.PARAM_IN_SRC_DIR)
        if len(glob.glob(source_dir + '/*.ctab')) < 5:

            self.__LOGGER.info(' =======  Generating ctab files ==========')
            gtf_file = os.path.join(source_dir, 'transcripts.gtf')
            if not os.path.isfile(gtf_file):
                raise ValueError("{} file is required to generate ctab files, found missing".
                                 format(gtf_file))

            if self.PARAM_IN_BAM_FILE_PATH in params and \
               params[self.PARAM_IN_BAM_FILE_PATH] is not None:
                bam_file_path = params[self.PARAM_IN_BAM_FILE_PATH]
            else:
                self.__LOGGER.info('Downloading bam file from alignment object')
                rau = ReadsAlignmentUtils(self.callback_url)
                alignment_retVal = rau.download_alignment({'source_ref': alignment_ref})
                alignment_dir = alignment_retVal.get('destination_dir')

                allbamfiles = glob.glob(alignment_dir + '/*.bam')
                if len(allbamfiles) == 0:
                    raise ValueError(f'bam file does not exist in {alignment_dir}')
                elif len(allbamfiles) == 1:
                    bam_file_path = allbamfiles[0]
                elif len(allbamfiles) > 1:
                    tmp_file_path = os.path.join(alignment_dir, 'accepted_hits.bam')
                    if os.path.isfile(tmp_file_path):
                        bam_file_path = tmp_file_path
                    else:
                        tmp_file_path = os.path.join(alignment_dir, 'accepted_hits_sorted.bam')
                        if os.path.isfile(tmp_file_path):
                            bam_file_path = tmp_file_path
                        else:
                            raise ValueError(f'accepted_hits.bam, accepted_hits_sorted.bam or '
                                             f'other bam file not found in {alignment_dir}')

            result = self.table_maker.build_ctab_files(
                ref_genome_path=gtf_file,
                alignment_path=bam_file_path,
                output_dir=source_dir)
            if result != 0:
                raise ValueError('Tablemaker failed')

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.__LOGGER = logging.getLogger('ExpressionUtils')
        self.__LOGGER.setLevel(logging.INFO)
        streamHandler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s")
        formatter.converter = time.gmtime
        streamHandler.setFormatter(formatter)
        self.__LOGGER.addHandler(streamHandler)
        self.__LOGGER.info("Logger was set")

        self.config = config
        self.scratch = config['scratch']
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.ws_url = config['workspace-url']
        self.config['SDK_CALLBACK_URL'] = self.callback_url
        self.expression_utils = Expression_Utils(self.config)
        self.dfu = DataFileUtil(self.callback_url)
        self.table_maker = TableMaker(config, self.__LOGGER)
        self.expr_matrix_utils = ExprMatrixUtils(config, self.__LOGGER)
        #END_CONSTRUCTOR
        pass


    def upload_expression(self, ctx, params):
        """
        Uploads the expression  *
        :param params: instance of type "UploadExpressionParams" (*   
           Required input parameters for uploading a reads expression data
           string   destination_ref        -   object reference of expression
           data. The object ref is 'ws_name_or_id/obj_name_or_id' where
           ws_name_or_id is the workspace name or id and obj_name_or_id is
           the object name or id string   source_dir             -  
           directory with the files to be uploaded string   alignment_ref    
           -   alignment workspace object reference *) -> structure:
           parameter "destination_ref" of String, parameter "source_dir" of
           String, parameter "alignment_ref" of String, parameter
           "genome_ref" of String, parameter "annotation_id" of String,
           parameter "bam_file_path" of String, parameter "transcripts" of
           type "boolean" (A boolean - 0 for false, 1 for true. @range (0,
           1)), parameter "data_quality_level" of Long, parameter
           "original_median" of Double, parameter "description" of String,
           parameter "platform" of String, parameter "source" of String,
           parameter "external_source_date" of String, parameter
           "processing_comments" of String
        :returns: instance of type "UploadExpressionOutput" (*     Output
           from upload expression    *) -> structure: parameter "obj_ref" of
           String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN upload_expression

        self.__LOGGER.info('Starting upload expression, parsing parameters ')
        pprint(params)

        ws_name_id, obj_name_id, source_dir = self._proc_upload_expression_params(ctx, params)

        alignment_ref = params.get(self.PARAM_IN_ALIGNMENT_REF)
        try:
            alignment_obj = self.dfu.get_objects({'object_refs': [alignment_ref]})['data'][0]
        except DFUError as e:
            self.__LOGGER.error('Logging stacktrace from workspace exception:\n' + e.data)
            raise

        alignment = alignment_obj['data']
        assembly_or_genome_ref = alignment['genome_id']

        genome_ref = self._get_genome_ref(assembly_or_genome_ref, params)

        expression_levels, tpm_expression_levels = self._get_expression_levels(
            source_dir, genome_ref, params.get(self.PARAM_IN_TRANSCRIPTS))

        self._gen_ctab_files(params, alignment_ref)

        uploaded_file = self.dfu.file_to_shock({'file_path': source_dir,
                                                'make_handle': 1,
                                                'pack': 'zip'
                                                })
        """
        move the zipfile created in the source directory one level up
        """
        path, dir = os.path.split(source_dir)
        zipfile = dir + '.zip'
        if os.path.isfile(os.path.join(source_dir, zipfile)):
            shutil.move(os.path.join(source_dir, zipfile), os.path.join(path, zipfile))

        file_handle = uploaded_file['handle']
        file_size = uploaded_file['size']

        expression_data = {
                           'numerical_interpretation': 'FPKM',
                           'genome_id': genome_ref,
                           'mapped_rnaseq_alignment': {alignment['read_sample_id']: alignment_ref},
                           'condition': alignment['condition'],
                           'file': file_handle,
                           'expression_levels': expression_levels,
                           'tpm_expression_levels': tpm_expression_levels
                           }
        additional_params = [self.PARAM_IN_ANNOTATION_ID,
                             self.PARAM_IN_DESCRIPTION,
                             self.PARAM_IN_DATA_QUAL_LEVEL,
                             self.PARAM_IN_PLATFORM,
                             self.PARAM_IN_PROC_COMMENTS,
                             self.PARAM_IN_MAPPED_SAMPLE_ID,
                             self.PARAM_IN_ORIG_MEDIAN,
                             self.PARAM_IN_EXT_SRC_DATE,
                             self.PARAM_IN_SRC
                             ]

        for opt_param in additional_params:
            if opt_param in params and params[opt_param] is not None:
                expression_data[opt_param] = params[opt_param]

        extra_provenance_input_refs = list()
        extra_provenance_input_refs.append(params.get(self.PARAM_IN_ALIGNMENT_REF))
        if self.PARAM_IN_GENOME_REF in params and params.get(self.PARAM_IN_GENOME_REF) is not None:
            extra_provenance_input_refs.append(params.get(self.PARAM_IN_GENOME_REF))

        self.__LOGGER.info('===========   Adding extra_provenance_refs')
        self.__LOGGER.info(str(extra_provenance_input_refs))
        self.__LOGGER.info('==========================================')

        res = self.dfu.save_objects(
            {"id": ws_name_id,
             "objects": [{
                          "type": "KBaseRNASeq.RNASeqExpression",
                          "data": expression_data,
                          "name": obj_name_id,
                          "extra_provenance_input_refs": extra_provenance_input_refs
                         }
                         ]})[0]

        self.__LOGGER.info('save complete')

        returnVal = {'obj_ref': str(res[6]) + '/' + str(res[0]) + '/' + str(res[4])}

        self.__LOGGER.info('Uploaded object: ')
        print(returnVal)
        #END upload_expression

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method upload_expression return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def download_expression(self, ctx, params):
        """
        Downloads expression *
        :param params: instance of type "DownloadExpressionParams" (*
           Required input parameters for downloading expression string
           source_ref         -       object reference of expression source.
           The object ref is 'ws_name_or_id/obj_name_or_id' where
           ws_name_or_id is the workspace name or id and obj_name_or_id is
           the object name or id *) -> structure: parameter "source_ref" of
           String
        :returns: instance of type "DownloadExpressionOutput" (*  The output
           of the download method.  *) -> structure: parameter
           "destination_dir" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN download_expression

        self.__LOGGER.info('Running download_expression with params:\n' +
                 pformat(params))

        inref = params.get(self.PARAM_IN_SRC_REF)
        if not inref:
            raise ValueError(self.PARAM_IN_SRC_REF + ' parameter is required')

        try:
            expression = self.dfu.get_objects({'object_refs': [inref]})['data']
        except DFUError as e:
            self.__LOGGER.error('Logging stacktrace from workspace exception:\n' + e.data)
            raise

        # set the output dir
        timestamp = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds() * 1000)
        output_dir = os.path.join(self.scratch, 'download_' + str(timestamp))
        os.mkdir(output_dir)

        file_ret = self.dfu.shock_to_file({
                                           'shock_id': expression[0]['data']['file']['id'],
                                           'file_path': output_dir,
                                           'unpack': 'unpack'
                                           })

        if not os.listdir(output_dir):
            raise ValueError('No files were downloaded: ' + output_dir)

        for f in glob.glob(output_dir + '/*.zip'):
            os.remove(f)

        returnVal = {'destination_dir': output_dir}

        #END download_expression

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method download_expression return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def export_expression(self, ctx, params):
        """
        Wrapper function for use by in-narrative downloaders to download expressions from shock *
        :param params: instance of type "ExportParams" (* Required input
           parameters for exporting expression string   source_ref         - 
           object reference of expression source. The object ref is
           'ws_name_or_id/obj_name_or_id' where ws_name_or_id is the
           workspace name or id and obj_name_or_id is the object name or id
           *) -> structure: parameter "source_ref" of String
        :returns: instance of type "ExportOutput" -> structure: parameter
           "shock_id" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN export_expression

        inref = params.get(self.PARAM_IN_SRC_REF)
        if not inref:
            raise ValueError(self.PARAM_IN_SRC_REF + ' parameter is required')

        try:
            expression = self.dfu.get_objects({'object_refs': [inref]})['data']
        except DFUError as e:
            self.__LOGGER.error('Logging stacktrace from workspace exception:\n' + e.data)
            raise

        output = {'shock_id': expression[0]['data']['file']['id']}

        #END export_expression

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method export_expression return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def get_expressionMatrix(self, ctx, params):
        """
        :param params: instance of type "getExprMatrixParams" (* Following
           are the required input parameters to get Expression Matrix *) ->
           structure: parameter "workspace_name" of String, parameter
           "output_obj_name" of String, parameter "expressionset_ref" of
           String
        :returns: instance of type "getExprMatrixOutput" -> structure:
           parameter "exprMatrix_FPKM_ref" of String, parameter
           "exprMatrix_TPM_ref" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN get_expressionMatrix
        fpkm_ref, tpm_ref = self.expr_matrix_utils.get_expression_matrix(params)

        returnVal = {'exprMatrix_FPKM_ref': fpkm_ref,
                     'exprMatrix_TPM_ref': tpm_ref}
        #END get_expressionMatrix

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method get_expressionMatrix return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def get_enhancedFilteredExpressionMatrix(self, ctx, params):
        """
        :param params: instance of type "getEnhancedFEMParams" (* Input
           parameters and method for getting the enhanced Filtered Expresion
           Matrix for viewing *) -> structure: parameter "fem_object_ref" of
           String
        :returns: instance of type "getEnhancedFEMOutput" -> structure:
           parameter "enhanced_FEM" of type "ExpressionMatrix" (A wrapper
           around a FloatMatrix2D designed for simple matricies of Expression
           data.  Rows map to features, and columns map to conditions.  The
           data type includes some information about normalization factors
           and contains mappings from row ids to features and col ids to
           conditions. description - short optional description of the
           dataset type - ? level, ratio, log-ratio scale - ? probably: raw,
           ln, log2, log10 col_normalization - mean_center, median_center,
           mode_center, zscore row_normalization - mean_center,
           median_center, mode_center, zscore feature_mapping - map from
           row_id to feature id in the genome data - contains values for
           (feature,condition) pairs, where features correspond to rows and
           conditions are columns (ie data.values[feature][condition])
           @optional description row_normalization col_normalization
           @optional genome_ref feature_mapping conditionset_ref
           condition_mapping report @metadata ws type @metadata ws scale
           @metadata ws row_normalization @metadata ws col_normalization
           @metadata ws genome_ref as Genome @metadata ws conditionset_ref as
           ConditionSet @metadata ws length(data.row_ids) as feature_count
           @metadata ws length(data.col_ids) as condition_count) ->
           structure: parameter "description" of String, parameter "type" of
           String, parameter "scale" of String, parameter "row_normalization"
           of String, parameter "col_normalization" of String, parameter
           "genome_ref" of type "ws_genome_id" (The workspace ID for a Genome
           data object. @id ws KBaseGenomes.Genome), parameter
           "feature_mapping" of mapping from String to String, parameter
           "conditionset_ref" of type "ws_conditionset_id" (The workspace ID
           for a ConditionSet data object (Note: ConditionSet objects do not
           yet exist - this is for now used as a placeholder). @id ws
           KBaseExperiments.ConditionSet), parameter "condition_mapping" of
           mapping from String to String, parameter "data" of type
           "FloatMatrix2D" (A simple 2D matrix of floating point numbers with
           labels/ids for rows and columns.  The matrix is stored as a list
           of lists, with the outer list containing rows, and the inner lists
           containing values for each column of that row.  Row/Col ids should
           be unique. row_ids - unique ids for rows. col_ids - unique ids for
           columns. values - two dimensional array indexed as:
           values[row][col] @metadata ws length(row_ids) as n_rows @metadata
           ws length(col_ids) as n_cols) -> structure: parameter "row_ids" of
           list of String, parameter "col_ids" of list of String, parameter
           "values" of list of list of Double, parameter "report" of type
           "AnalysisReport" (A basic report object used for a variety of
           cases to mark informational messages, warnings, and errors related
           to processing or quality control checks of raw data.) ->
           structure: parameter "checkTypeDetected" of String, parameter
           "checkUsed" of String, parameter "checkDescriptions" of list of
           String, parameter "checkResults" of list of type "boolean"
           (Indicates true or false values, false = 0, true = 1 @range
           [0,1]), parameter "messages" of list of String, parameter
           "warnings" of list of String, parameter "errors" of list of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN get_enhancedFilteredExpressionMatrix

        efem = self.expr_matrix_utils.get_enhancedFEM( params )

        returnVal = { 'enhanced_FEM': efem }

        #END get_enhancedFilteredExpressionMatrix

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method get_enhancedFilteredExpressionMatrix return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
