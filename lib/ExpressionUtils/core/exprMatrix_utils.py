import os
import uuid
import re
import numpy
from pprint import pprint, pformat


from installed_clients.WorkspaceClient import Workspace
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.baseclient import ServerError as DFUError
from installed_clients.GenomeAnnotationApiClient import GenomeAnnotationAPI

class ExprMatrixUtils:
    """
     Constains a set of functions for expression levels calculations.
    """

    PARAM_IN_WS_NAME = 'workspace_name'
    PARAM_IN_OBJ_NAME = 'output_obj_name'
    PARAM_IN_EXPSET_REF = 'expressionset_ref'

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.scratch = os.path.join(config['scratch'], 'EM_' + str(uuid.uuid4()))
        self.ws_url = config['workspace-url']
        self.ws_client = Workspace(self.ws_url)
        self.dfu = DataFileUtil(self.callback_url)
        self.gaa = GenomeAnnotationAPI( self.callback_url )
        pass

    def process_params(self, params):
        """
        validates params passed to gen expression matrix method
        """
        for p in [self.PARAM_IN_EXPSET_REF,
                  self.PARAM_IN_OBJ_NAME,
                  self.PARAM_IN_WS_NAME
                 ]:
            if p not in params:
                raise ValueError('"{}" parameter is required, but missing'.format(p))

        ws_name_id = params.get(self.PARAM_IN_WS_NAME)
        if not isinstance(ws_name_id, int):
            try:
                ws_name_id = self.dfu.ws_name_to_id(ws_name_id)
            except DFUError as se:
                prefix = se.message.split('.')[0]
                raise ValueError(prefix)
        self.ws_id = ws_name_id

    def get_expressionset_data(self, expressionset_ref):

        expr_set_obj = self.ws_client.get_objects2(
            {'objects': [{'ref': expressionset_ref}]})['data'][0]

        expr_set_obj_type = expr_set_obj.get('info')[2]
        expr_set_data = dict()
        expr_set_data['ws_name'] = expr_set_obj.get('info')[7]
        expr_set_data['obj_name'] = expr_set_obj.get('info')[1]

        if re.match('KBaseRNASeq.RNASeqExpressionSet-\d.\d', expr_set_obj_type):
            expr_set_data['genome_ref'] = expr_set_obj['data']['genome_id']
            expr_obj_refs = list()
            for expr_obj in expr_set_obj['data']['mapped_expression_ids']:
                expr_obj_refs.append(expr_obj.values()[0])
            expr_set_data['expr_obj_refs'] = expr_obj_refs

        elif re.match('KBaseSets.ExpressionSet-\d.\d', expr_set_obj_type):
            items = expr_set_obj.get('data').get('items')
            expr_obj_refs = list()
            for item in items:
                expr_obj_refs.append(item['ref'])
            expr_obj = self.ws_client.get_objects2(
                {'objects': [{'ref': expr_obj_refs[0]}]})['data'][0]
            expr_set_data['genome_ref'] = expr_obj['data']['genome_id']
            expr_set_data['expr_obj_refs'] = expr_obj_refs
        else:
            raise TypeError(self.PARAM_IN_EXPSET_REF + ' should be of type ' +
                            'KBaseRNASeq.RNASeqExpressionSet ' +
                            'or KBaseSets.ExpressionSet')
        return expr_set_data

    def save_expression_matrix(self, tables, expr_set_data, em_obj_name, hidden = 0):

        all_rows = {}    # build a dictionary of keys only which is a union of all row ids (gene_ids)
        self.logger.info( '***** length of tables is {0}'.format( len( tables )))
        for table in tables:
            for r in table.keys():
                all_rows[r] = []

        for gene_id in all_rows.keys():
            row = []
            for table in tables:
                if ( gene_id in table ):
                    #logger.info( 'append ' + gene_id )
                    #logger.info( pformat( table[gene_id]))
                               #all_rows[gene_id].append( table[gene_id] )
                    row.append( table[gene_id] )
                else:
                    #logger.info( 'append  0' )
                    row.append( 0 )
                all_rows[gene_id] = row
                #logger.info( all_rows[gene_id])

        em_data = {
                    'genome_ref': expr_set_data['genome_ref'],
                    'scale': 'log2',
                    'type': 'level',
                    'data': {
                            'row_ids': [],
                            'values': [],
                            'col_ids': expr_set_data['expr_obj_names']
                            },
                    'feature_mapping' : {},
                    'condition_mapping': expr_set_data['condition_map']
                   }

        # we need to load row-by-row to preserve the order
        self.logger.info('loading expression matrix data')

        for gene_id in all_rows.keys():
            em_data['feature_mapping'][gene_id] = gene_id
            em_data['data']['row_ids'].append(gene_id)
            em_data['data']['values'].append(all_rows[gene_id])

        try:
            self.logger.info( 'saving em_data em_name {0}'.format(em_obj_name))
            obj_info = self.dfu.save_objects({'id': self.ws_id,
                                              'objects': [
                                                          { 'type': 'KBaseFeatureValues.ExpressionMatrix',
                                                            'data': em_data,
                                                            'name': em_obj_name,
                                                            'hidden': hidden,
                                                            'extra_provenance_input_refs': [
                                                                em_data.get('genome_ref'),
                                                                self.params[self.PARAM_IN_EXPSET_REF]]
                                                          }
                                                    ]})[0]
            self.logger.info('ws save return:\n' + pformat(obj_info))
        except Exception as e:
            self.logger.exception(e)
            raise Exception('Failed Saving Expression Matrix to Workspace')

        return str(obj_info[6]) + '/' + str(obj_info[0]) + '/' + str(obj_info[4])

    def get_expression_matrix(self, params):

        self.process_params(params)
        self.params = params

        expressionset_ref = params.get(self.PARAM_IN_EXPSET_REF)

        expr_set_data = self.get_expressionset_data(expressionset_ref)
        expr_obj_names = list()
        fpkm_tables = list()
        tpm_tables = list()
        condition_map = dict()
        tpm_table = None
        for expr_obj_ref in expr_set_data['expr_obj_refs']:
            try:
                self.logger.info('*** getting expression set {0} from workspace ****'
                                 .format(expr_obj_ref))

                expr = self.ws_client.get_objects2(
                                            {'objects':
                                            [{'ref': expr_obj_ref}]})['data'][0]

            except Exception, e:
                self.logger.exception(e)
                raise Exception('Unable to download expression object {0} from workspace {1}'.
                                format(expr_obj_ref, expr_set_data['ws_name']))

            expr_name = expr.get('info')[1]
            expr_obj_names.append(expr_name)
            condition_map.update({expr_name: expr.get('data').get('condition')})
            num_interp = expr.get('data').get('numerical_interpretation')
            if num_interp != 'FPKM':
                raise Exception(
                    'Did not get expected FPKM value from numerical interpretation key from \
                     Expression object {0}, instead got '.format(expr_obj_ref, num_interp))

            pr_comments = expr.get('data').get('processing_comments', None)  # log2 Normalized
            if pr_comments is not None:
                self.logger.info('pr_comments are {0}'.format(pr_comments))

            fpkm_table = expr.get('data').get('expression_levels') # QUESTION: is this really FPKM levels?
            self.logger.info('FPKM keycount: {0}'.format(len(fpkm_table.keys())))
            fpkm_tables.append(fpkm_table)

            tpm_table = None  # Cufflinks doesn't generate TPM
            if 'tpm_expression_levels' in expr['data']:  # so we need to check for this key
                tpm_table = expr.get('data').get('tpm_expression_levels')
                self.logger.info('TPM keycount: {0}'.format(len(tpm_table.keys())))
                tpm_tables.append(tpm_table)

        expr_set_data['expr_obj_names'] = expr_obj_names
        expr_set_data['condition_map'] = condition_map
        output_obj_name = params.get(self.PARAM_IN_OBJ_NAME)
        fpkm_ref = self.save_expression_matrix(fpkm_tables,
                                               expr_set_data,
                                               '{0}_FPKM_ExpressionMatrix'.format(output_obj_name))
        tpm_ref = None
        if tpm_table is not None:
            tpm_ref = self.save_expression_matrix(tpm_tables,
                                                  expr_set_data,
                                                  '{0}_TPM_ExpressionMatrix'.format(output_obj_name))
        return fpkm_ref, tpm_ref


    def get_matrix_stats( self, raw_row ):
        """
        returns a list of [ min, max, mean, std.dev, is_data_missing] for one row of conditional 
        expression values
        """
        has_missing = "No"
        row = []
        for r in raw_row:
            if r == None or numpy.isnan( r ):     # careful here - r can be 0 which is a legitimate value
                has_missing = "Yes"
            else:
                row.append(r)

        if len( row ) < 1:
            return( [ 'NA', 'NA', 'NA', 'NA', 'Yes' ] )

        if len( row ) == 1:
           sd = 0
        else:
           sd = numpy.std( row, ddof=1 )
        return( [ min( row ), max( row ), numpy.mean( row ), sd, has_missing ] )


    def convert_dem_to_dict( self, dem ):
        """
        returns a dict that maps feature_id -> [ fc, q ]
        """
        row_ids = dem.get( 'row_ids' )
        vals = dem.get( 'values' )
  
        n_rows = len( row_ids )
        if ( len( vals ) != n_rows ):
            raise Exception( "length discrepancy in differential expression matrix: {0} row_ids but {1} values".format( n_rows, len( fvals ) ) )

        dem_dict = {}
        for _id, val in zip(row_ids, vals):
            dem_dict[_id] = [ val[0], val[2] ]  # [fc,q]. (not bothering to check for dups here)

        return dem_dict


    def get_enhancedFEM( self, params ):
        """
        implements get_enhancedFilteredExpressionMatrix() method
        """

        if 'fem_object_ref' not in params:
            raise ValueError( "fem_object_ref parameter not given to get_enhancedFilteredExpressionMatrix" )

        fem_object_ref = params.get( 'fem_object_ref' )

        fem_obj_ret = self.ws_client.get_objects2(
                       {'objects': [{'ref': fem_object_ref }]})['data'][0]
        fem = fem_obj_ret.get( 'data' )
        prov = fem_obj_ret.get( 'provenance')[0]

        # create the enhanced FEM, starting with the FEM

        efem = {}
        for k in [ 'genome_ref', 'scale', 'type' ]:
            efem[k] = fem.get( k )

        efem['data'] = {}
        efem['data']['col_ids'] = [ "description", 
                                    "fold-change",
                                    "q-value",
                                    "min",
                                    "max",
                                    "mean",
                                    "std_dev",
                                    "is_missing_values" ]
        efem['data']['column_labels'] =[ "Description", 
                                         "Fold change",
                                         "Q value",
                                         "Min. expression",
                                         "Max. expression",
                                         "Mean expression",
                                         "Std. dev.",
                                         "Missing values?" ]
        fm = fem.get('data')
        efem['data']['row_ids'] = fm.get('row_ids')
        efem['data']['values' ] = []
        n_efem_rows = len( efem['data']['row_ids'] )
        fvals = fm.get('values')
        if ( len( fvals ) != n_efem_rows ):
            raise Exception( "length discrepancy in filtered expression matrix: {0} row_ids but {1} values".format( n_efem_rows, len( fvals ) ) )

        # Get genome object and feature descriptions as a handy feature-indexed dict

        feat_dict = self.gaa.get_feature_functions( { 'ref': fem.get( 'genome_ref' ), 'feature_id_list': None } )

        # if this FEM has a "resolved_ws_objects" record in its provenance,
        # then that should be a list of one DEM reference from which we get the FC and q values
        # as a feature (=row_id) -indexed dict.

        #if prov.get( 'resolved_ws_objects' ):
        #    dem_ref = prov.get( 'resolved_ws_objects' )[0]
        #    dem_obj_ret = self.dfu.get_objects( {'object_refs': [ dem_ref ] } ).get('data')[0]
        #    dem = dem_obj_ret.get( 'data' )
        #    dem_dict = self.convert_dem_to_dict( dem.get('data') )  # convert to dictionary for quick lookups
        if fem.get( 'diff_expr_matrix_ref' ):
            dem_ref = fem.get( 'diff_expr_matrix_ref' )
            dem_obj_ret = self.dfu.get_objects( {'object_refs': [ dem_ref ] } ).get('data')[0]
            dem = dem_obj_ret.get( 'data' )
            dem_dict = self.convert_dem_to_dict( dem.get('data') )  # convert to dictionary for quick lookups
        else:
            dem_dict = {}   # empty dictionary

        # for each row

        for row_id, fm_val_row in zip( fm.get('row_ids'), fvals ):

            # make a new row with NA for description, FC and q

            new_values_row =  [ 'NA', 'NA', 'NA' ] + self.get_matrix_stats( fm_val_row )

            # if we have a description for this feature (row_id) put it in the first column

            desc = feat_dict.get( row_id )
            if desc:
                new_values_row[0] = desc     # leave as 'NA' if no entry in feat_dict

            # if we have a DEM entry for this row, put FC and q into 2nd and 3rd columns
            d = dem_dict.get( row_id )
            if d:
                new_values_row[1], new_values_row[2] = d

            # finally, add this row to the eFEM

            efem['data']['values'].append( new_values_row )


        return efem

