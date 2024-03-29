### Version 0.1.9
- add return Expression object data only ability
- add support for RNASeqAligment with AnnotatedMetagenomeAssembly reference

### Version 0.1.8
- Changed SHOCK upload in unit tests to DataFileUtil.file_to_shock()

### Version 0.1.5
- Update the baseclients for all modules used to resolve _check_job BADSTATUSCODE failure

### Version 0.1.4
- Unquote urlencoded lines in expression files

### Version 0.0.1
__Initial version of the module to upload, download and export RNASeq Expression.__
- Saves and retrieves the expression data files generated either by the StringTie or Cufflinks App.
- The files are saved as a single compressed file in tar.gz format.
- All the required files (gtf, FPKM with TPM and ctab) saved by this module are generated by StringTie.
- The TPM and ctab files which are absent in Cufflinks' output are generated by this module.
_ This module also generates and saves expression levels and tpm expression levels from the
  files provided for upload.
- Uses KBaseRNASeq.RNASeqExpression-8.0
https://ci.kbase.us/#spec/type/KBaseRNASeq.RNASeqExpression-8.0

/*
Id for KBaseRNASeq.GFFAnnotation
@id ws KBaseRNASeq.GFFAnnotation
*/
typedef string ws_referenceAnnotation_id;

/*
The workspace id for a RNASeqAlignment object
@id ws KBaseRNASeq.RNASeqAlignment
*/
typedef string ws_samplealignment_id;

/*
Id for the handle object
@id handle
*/
typedef string HandleId;

/*
@optional hid file_name type url remote_md5 remote_sha1
*/
typedef structure {
  HandleId hid;
  string file_name;
  string id;
  string type;
  string url;
  string remote_md5;
  string remote_sha1;
} Handle;

/*
The workspace object for a RNASeqExpression
@optional description platform tool_opts data_quality_level original_median external_source_date source file processing_comments mapped_sample_id tpm_expression_levels
@metadata ws type
@metadata ws numerical_interpretation
@metadata ws description
@metadata ws genome_id
@metadata ws platform
*/
typedef structure {
        string id;
        string type;
        string numerical_interpretation;
        string description;
        int data_quality_level;
        float original_median;
        string external_source_date;
        mapping<string feature_id,float feature_value> expression_levels;
        mapping<string feature_id,float feature_value> tpm_expression_levels;
        /*ws_genome_annotation_id genome_id;*/
	    string genome_id;
        ws_referenceAnnotation_id annotation_id;
	    string condition;
	    mapping<string sample_id,ws_samplealignment_id alignment_id> mapped_rnaseq_alignment;
        mapping<string condition,mapping<string sample_id , string replicate_id>> mapped_sample_id;
        string  platform;
        string source;
        Handle file;
        string processing_comments;
        string tool_used;
        string tool_version;
	    mapping<string opt_name, string opt_value> tool_opts;
    }RNASeqExpression;

-----------------------------------------------------------------------------------------------

### Version 0.0.2

- uses updated RNASeqExpression
    - changes: annotation_ref has been made optional
    - id, type, tool_used, tool_version and tool_opts have been removed
- genome_ref to be saved in the object is gotten from the alignment_ref input parameter of
  upload_expression(). If the alignment_ref does not contain a genome_ref then this value
  should be provided in the optional genome_ref input parameter to the upload_expression()

Updated RNASeqExpression type - KBaseRNASeq.RNASeqExpression-9.0
https://ci.kbase.us/#spec/type/KBaseRNASeq.RNASeqExpression-9.0

/*
Id for KBaseRNASeq.GFFAnnotation
@id ws KBaseRNASeq.GFFAnnotation
*/
typedef string ws_referenceAnnotation_id;

/*
The workspace id for a RNASeqAlignment object
@id ws KBaseRNASeq.RNASeqAlignment
*/
typedef string ws_samplealignment_id;

/*
  The workspace id for a KBaseGenomes.Genome object
  @id ws KBaseGenomes.Genome
*/
typedef string ws_genome_ref;

/*
Id for the handle object
@id handle
*/
typedef string HandleId;

/*
@optional hid file_name type url remote_md5 remote_sha1
*/
typedef structure {
  HandleId hid;
  string file_name;
  string id;
  string type;
  string url;
  string remote_md5;
  string remote_sha1;
} Handle;

/*
  The workspace object for a RNASeqExpression
  @optional description platform data_quality_level original_median external_source_date source annotation_ref processing_co\
mments mapped_sample_id tpm_expression_levels
  @metadata ws numerical_interpretation
  @metadata ws description
  @metadata ws genome_ref
  @metadata ws platform
*/
typedef structure {
        string numerical_interpretation;
        string description;
        int data_quality_level;
        float original_median;
        string external_source_date;
        mapping<string feature_id,float feature_value> expression_levels;
        mapping<string feature_id,float feature_value> tpm_expression_levels;
        ws_genome_ref genome_ref;
        ws_referenceAnnotation_id annotation_ref;
	    string condition;
	    mapping<string sample_id,ws_samplealignment_id alignment_id> mapped_rnaseq_alignment;
        mapping<string condition,mapping<string sample_id , string replicate_id>> mapped_sample_id;
        string  platform;
        string source;
        Handle file;
        string processing_comments;
}RNASeqExpression;
-----------------------------------------------------------------------------------------

### Version 0.1.2

 - Added new method get_enhancedFilteredExpressionMatrix() which serves to the javascript viewer code a version of the specified filtered expression matrix, joined with functional descriptions and the fold change and q-values from the differential expression matrix that was used to filter the matrix rows.
