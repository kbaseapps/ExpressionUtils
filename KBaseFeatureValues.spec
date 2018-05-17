

/*

The KBaseFeatureValues set of data types and service provides a mechanism for
representing numeric values associated with genome features and conditions, together
with some basic operations on this data.  Essentially, the data is stored as a simple
2D matrix of floating point numbers.  Currently, this is exposed as support for
expression data and single gene knockout fitness data.  (Fitness data being growth
rate relative to WT growth with the specified single gene knockout in a specified
condition).

The operations supported on this data is simple clustering of genes and clustering 
related tools.

*/
module KBaseFeatureValues {

    /* 
        The workspace ID for a Genome data object.
        @id ws KBaseGenomes.Genome
    */
    typedef string ws_genome_id;

    /* 
        The workspace ID for a ConditionSet data object (Note: ConditionSet objects
        do not yet exist - this is for now used as a placeholder).
        @id ws KBaseExperiments.ConditionSet
    */
    typedef string ws_conditionset_id;

    /*
        A simple 2D matrix of floating point numbers with labels/ids for rows and
        columns.  The matrix is stored as a list of lists, with the outer list
        containing rows, and the inner lists containing values for each column of
        that row.  Row/Col ids should be unique.

        row_ids - unique ids for rows.
        col_ids - unique ids for columns.
        values - two dimensional array indexed as: values[row][col]
        @metadata ws length(row_ids) as n_rows
        @metadata ws length(col_ids) as n_cols
    */
    typedef structure {
        list<string> row_ids;
        list<string> col_ids;
        list<list<float>> values;
    } FloatMatrix2D;

    /*
        Indicates true or false values, false = 0, true = 1
        @range [0,1]
    */
    typedef int boolean;

    /*
        A basic report object used for a variety of cases to mark informational
        messages, warnings, and errors related to processing or quality control
        checks of raw data.
    */
    typedef structure {
        string checkTypeDetected;
        string checkUsed;
        list<string> checkDescriptions;
        list<boolean> checkResults;
        list<string> messages;
        list<string> warnings;
        list<string> errors;
    } AnalysisReport;

    /*
        A wrapper around a FloatMatrix2D designed for simple matricies of Expression
        data.  Rows map to features, and columns map to conditions.  The data type 
        includes some information about normalization factors and contains
        mappings from row ids to features and col ids to conditions.

        description - short optional description of the dataset
        type - ? level, ratio, log-ratio
        scale - ? probably: raw, ln, log2, log10
        col_normalization - mean_center, median_center, mode_center, zscore
        row_normalization - mean_center, median_center, mode_center, zscore
        feature_mapping - map from row_id to feature id in the genome
        data - contains values for (feature,condition) pairs, where 
            features correspond to rows and conditions are columns
            (ie data.values[feature][condition])
        diff_expr_matrix_ref - added to connect filtered expression matrix to differential expression matrix
            used for filtering

        @optional description row_normalization col_normalization
        @optional genome_ref feature_mapping conditionset_ref condition_mapping report diff_expr_matrix_ref

        @metadata ws type
        @metadata ws scale
        @metadata ws row_normalization
        @metadata ws col_normalization
        @metadata ws genome_ref as Genome
        @metadata ws conditionset_ref as ConditionSet
        @metadata ws length(data.row_ids) as feature_count
        @metadata ws length(data.col_ids) as condition_count
    */
    typedef structure {

        string description;

        string type;
        string scale;
        string row_normalization;
        string col_normalization;

        ws_genome_id genome_ref;
        mapping<string, string> feature_mapping;

        ws_conditionset_id conditionset_ref;
        mapping<string, string> condition_mapping;

        string        diff_expr_matrix_ref;
        FloatMatrix2D data;
        AnalysisReport report;
    } ExpressionMatrix;


    /*
        A wrapper around a FloatMatrix2D designed for simple matricies of Differential
        Expression data.  Rows map to features, and columns map to conditions.  The 
        data type includes some information about normalization factors and contains
        mappings from row ids to features and col ids to conditions.

        description - short optional description of the dataset
        type - ? level, ratio, log-ratio
        scale - ? probably: raw, ln, log2, log10
        col_normalization - mean_center, median_center, mode_center, zscore
        row_normalization - mean_center, median_center, mode_center, zscore
        feature_mapping - map from row_id to feature id in the genome
        data - contains values for (feature,condition) pairs, where 
            features correspond to rows and conditions are columns
            (ie data.values[feature][condition])

        @optional description row_normalization col_normalization
        @optional genome_ref feature_mapping conditionset_ref condition_mapping report

        @metadata ws type
        @metadata ws scale
        @metadata ws row_normalization
        @metadata ws col_normalization
        @metadata ws genome_ref as Genome
        @metadata ws conditionset_ref as ConditionSet
        @metadata ws length(data.row_ids) as feature_count
        @metadata ws length(data.col_ids) as condition_count
    */
    typedef structure {

        string description;

        string type;
        string scale;
        string row_normalization;
        string col_normalization;

        ws_genome_id genome_ref;
        mapping<string, string> feature_mapping;

        ws_conditionset_id conditionset_ref;
        mapping<string, string> condition_mapping;

        FloatMatrix2D data;
        AnalysisReport report;
    } DifferentialExpressionMatrix;


    /*
        A wrapper around a FloatMatrix2D designed for simple matricies of Fitness data
        for single gene/feature knockouts.  Generally fitness is measured as growth rate
        for the knockout strain relative to wildtype.  This data type only supports
        single feature knockouts.

        description - short optional description of the dataset
        type - ? level, ratio, log-ratio
        scale - ? probably: raw, ln, log2, log10
        col_normalization - mean_center, median_center, mode_center, zscore
        row_normalization - mean_center, median_center, mode_center, zscore
        feature_mapping - map from row_id to feature id in the genome
        data - contains values for (feature,condition) pairs, where 
            features correspond to rows and conditions are columns
            (ie data.values[feature][condition])

        @optional description row_normalization col_normalization
        @optional genome_ref feature_ko_mapping conditionset_ref condition_mapping report

        @metadata ws type
        @metadata ws scale
        @metadata ws row_normalization
        @metadata ws col_normalization
        @metadata ws genome_ref as Genome
        @metadata ws length(data.row_ids) as feature_count
        @metadata ws length(data.col_ids) as condition_count

    */
    typedef structure {
        string description;

        string type;
        string scale;
        string row_normalization;
        string col_normalization;

        ws_genome_id genome_ref;
        mapping<string, string> feature_ko_mapping;

        ws_conditionset_id conditionset_ref;
        mapping<string, string> condition_mapping;

        FloatMatrix2D data;
        AnalysisReport report;
    } SingleKnockoutFitnessMatrix;

    /* 
        A workspace ID that references a Float2DMatrix wrapper data object.
        @id ws KBaseFeatureValues.ExpressionMatrix KBaseFeatureValues.SingleKnockoutFitnessMatrix
    */
    typedef string ws_matrix_id;

    /*
        id_to_pos - simple representation of a cluster, which maps features/conditions of the cluster to the
        row/col index in the data (0-based index).  The index is useful for fast lookup of data
        for a specified feature/condition in the cluster.
        @optional meancor msec
    */
    typedef structure { 
        mapping<string, int> id_to_pos;
        float meancor;
        float msec;
    } labeled_cluster;

    /*
        A set of clusters, typically generated for a Float2DMatrix wrapper, such as Expression
        data or single feature knockout fitness data.

        feature_clusters - list of labeled feature clusters
        condition_clusters - (optional) list of labeled condition clusters
        feature_dendrogram - (optional) maybe output from hierchical clustering approaches
        condition_dendogram - (optional) maybe output from hierchical clustering approaches
        original_data - pointer to the original data used to make this cluster set
        report - information collected during cluster construction.

        @metadata ws original_data as source_data_ref
        @metadata ws length(feature_clusters) as n_feature_clusters
        @metadata ws length(condition_clusters) as n_condition_clusters
        @optional condition_clusters 
        @optional feature_dendrogram condition_dendrogram
        @optional original_data report
    */
    typedef structure {
        list<labeled_cluster> feature_clusters;
        list<labeled_cluster> condition_clusters;
        string feature_dendrogram;
        string condition_dendrogram;
        ws_matrix_id original_data;
        AnalysisReport report;
    } FeatureClusters;


    /* 
        The workspace ID of a FeatureClusters data object.
        @id ws KBaseFeatureValues.FeatureClusters
    */
    typedef string ws_featureclusters_id;


    /* note: this needs review from Marcin */
    typedef structure {
        int best_k;
        list<tuple<int,float>> estimate_cluster_sizes;
    } EstimateKResult;

    typedef structure {
        ws_matrix_id input_matrix;
        int min_k;
        int max_k;
        int max_iter;
        int random_seed;
        int neighb_size;
        int max_items;
        string out_workspace;
        string out_estimate_result;
    } EstimateKParams;

    /*
        Used as an analysis step before generating clusters using K-means clustering, this method
        provides an estimate of K by [...]
    */
    funcdef estimate_k(EstimateKParams params)
        returns () authentication required;

     typedef structure {
        ws_matrix_id input_matrix;
        int min_k;
        int max_k;
        string criterion;
        boolean usepam;
        float alpha;
        boolean diss;
        int random_seed;
        string out_workspace;
        string out_estimate_result;
    } EstimateKParamsNew;

    /*
        Used as an analysis step before generating clusters using K-means clustering, this method
        provides an estimate of K by [...]
    */
    funcdef estimate_k_new(EstimateKParamsNew params)
        returns () authentication required;



    typedef structure {
        int k;
        ws_matrix_id input_data;
        int n_start;
        int max_iter;
        int random_seed;
        string algorithm;
        string out_workspace;
        string out_clusterset_id;
    } ClusterKMeansParams;

    /*
        Clusters features by K-means clustering.
    */
    funcdef cluster_k_means(ClusterKMeansParams params)
        returns () authentication required;


    typedef structure {
        string distance_metric;
        string linkage_criteria;
        float feature_height_cutoff;
        float condition_height_cutoff;
        int max_items;
        ws_matrix_id input_data;
        string algorithm;
        string out_workspace;
        string out_clusterset_id;
    } ClusterHierarchicalParams;

    /*
        Clusters features by hierarchical clustering.
    */
    funcdef cluster_hierarchical(ClusterHierarchicalParams params)
        returns () authentication required;


    typedef structure {
        float feature_height_cutoff;
        float condition_height_cutoff;
        ws_featureclusters_id input_data;
        string out_workspace;
        string out_clusterset_id;
    } ClustersFromDendrogramParams;

    /*
        Given a FeatureClusters with a dendogram built from a hierarchical clustering
        method, this function creates new clusters by cutting the dendogram at
        a specific hieght or by some other approach.
    */
    funcdef clusters_from_dendrogram(ClustersFromDendrogramParams params)
        returns () authentication required;


    typedef structure {
        ws_featureclusters_id input_clusterset;
        string out_workspace;
        string out_report_id;
    } EvaluateClustersetQualityParams;

    /*
        Given a FeatureClusters with a dendogram built from a hierarchical clustering
        method, this function creates new clusters by cutting the dendogram at
        a specific hieght or by some other approach.
    */
    funcdef evaluate_clusterset_quality(EvaluateClustersetQualityParams params)
        returns () authentication required;


    /*
        method - optional field specifying special type of validation
            necessary for particular clustering method.
    */
    typedef structure {
        string method;
        ws_matrix_id input_data;
    } ValidateMatrixParams;

    funcdef validate_matrix(ValidateMatrixParams params)
        returns () authentication optional;

    /*
        transform_type - type of matrix change (one of: add, multiply,
            normalize, missing, ?).
        transform_value - optional field defining volume of change if
            it's necessary for chosen transform_type.
    */
    typedef structure {
        string transform_type;
        float transform_value;
        ws_matrix_id input_data;
        string out_workspace;
        string out_matrix_id;
    } CorrectMatrixParams;

    funcdef correct_matrix(CorrectMatrixParams params)
        returns () authentication required;

    /*
        out_matrix_id - optional target matrix object name (if not specified 
            then target object overwrites input_data).
    */
    typedef structure {
        ws_matrix_id input_data;
        ws_genome_id genome_ref;
        string out_workspace;
        string out_matrix_id;
    } ReconnectMatrixToGenomeParams;
    
    funcdef reconnect_matrix_to_genome(ReconnectMatrixToGenomeParams params)
        returns () authentication required;

    /* 
        The workspace ID of a FeatureSet data object.
        @id ws KBaseCollections.FeatureSet
    */
    typedef string ws_featureset_id;

    /*
        base_feature_set - optional field,
        description - optional field.
    */
    typedef structure {
        ws_genome_id genome;
        string feature_ids;
        string feature_ids_custom;
        ws_featureset_id base_feature_set;
        string description;
        string out_workspace;
        string output_feature_set;
    } BuildFeatureSetParams;

    funcdef build_feature_set(BuildFeatureSetParams params) 
        returns () authentication required;


	/*******************************************
	* data API: data transfer objects (DTOs) *
	******************************************/    
	
	/*
		Introduction:
		
		Data transfer objects (DTO) are needed to package data to readliy vizualize data by UI widgets.
		The methods bellow are aimed to operate on expression matrices, but later we should have similar methods
		to work with fitness data, etc. Thus, methods can be data specific, but output can be designed in a generic way,
		since approcahes to visualize these types of data are similar. In the very end all of them are based on Float2DMatrix.
		
		But we probably can think more broadly... Float2DMatrix is jsut another complex subtype of a Collection. So, speaking about 
		output data, let us think in terms of Items, Sets, etc...  
		
		On the other hand,  functions and params should be data specific, since we do not support polymorphism. Thus functions and params 
		will have "Matrix" in their names. 
	
		In relation to the ExpressionMatrix and Float2DMatrix, Item can be either row (feature) or column (condtion).
		
		We will first define several atomic datatypes that can be queried individually. Then we will define several types for bulk queires 
		(typically required for UI widgets) taht may comprise several individaul data types to optimmize data preparation and transfer. 		
	*/
	

 	 /*
		General info about matrix, including genome name that needs to be extracted from the genome object
		
	*/	
  	
	typedef structure{
		string matrix_id;
		string matrix_name;
		string matrix_description;
		string genome_id;
		string genome_name;
		int rows_count;
		int columns_count;
		string scale;
		string type;
		string row_normalization;
		string col_normalization;
	} MatrixDescriptor;	
	
	
	/*
		Basic information about a particular item in a collection. 
		
    	index - index of the item
    	id - id of the item
    	name - name of the item
    	description - description of the item			
    	properties - additinal proerties: key - property type, value - value. For instance, if item represents a feature, the property type can be a type of feature annotation in a genome, e.g. 'function', 'strand', etc	
	*/
	
	typedef structure{
    	int index;
    	string id;
    	string name;
    	string description;
    	mapping<string,string> properties;
	} ItemDescriptor;
		
    /*
		Statistics for a given item in a collection (defined by index) , calculated on the associated vector of values. 
		Typical example is 2D matrix: item is a given row, and correposnding values from all columns is an associated vector.   
    	
    	In relation to ExpressionMatrix we can think about a gene (defined by row index in Float2DMatrix) and a vector of expression 
    	values across all (or a subset of) conditions. In this case, index_for - index of a row representing a gene in the Float2DMatrix,  
    	indeces_on - indeces of columns represnting a set of conditions on which we want to calculate statistics. 
    	 
    	index_for - index of the item in a collection FOR which all statitics is collected
    	indeces_on - indeces of items in the associated vector ON which the statistics is calculated
    	size - number of elements in the associated vector
    	avg - mean value for a given item across all elements in the associated vector 
    	min - min value for a given item across all elements in the associated vector 
    	max - max value for a given item across all elements in the associated vector 
    	std - std value for a given item across all elements in the associated vector 
    	missing_values - number of missing values for a given item across all elements in the associated vector 

    */
    typedef structure{
    	int index_for;
    	list<int> indeces_on;
    	int size;
    	float avg;
    	float min;
    	float max;
    	float std;
    	int missing_values;
    } ItemStat;	
    

	
    /*
		Same as ItemStat, but for a set of Items. Actually it can be modeled as a list<ItemStat>, but this way we can optimize data transfer in two ways:
		1. In parameters we can specify that we need a subset of properties, e.g. only "avgs". 
		2. No field names in json (avg, min, max, etc) for each element in the list
		
		
    	indeces_for - indeces of items in a collection FOR which all statitics is collected
    	indeces_on - indeces of items in the associated vector ON which the statistics is calculated
    	size - number of elements defined by indeces_on (expected to be the same for all items defined by indeces_for)
    	avgs - mean values for each item defined by indeces_for across all elements defined by indeces_on 
    	mins - min values for each item defined by indeces_for across all elements defined by indeces_on 
    	maxs - max values for each item defined by indeces_for across all elements defined by indeces_on 
    	stds - std values for each item defined by indeces_for across all elements defined by indeces_on 
    	missing_values - number of missing values for each item defined by indeces_for across all elements defined by indeces_on 
    */	
    typedef structure{
    	list<int> indeces_for;
    	list<int> indeces_on;
    	
    	int size;    	
		list<float> avgs;	
		list<float> mins;	
		list<float> maxs;
		list<float> stds;
		list<int>	missing_values;
    } ItemSetStat;

	
 	 /*
		To represent a pairwise comparison of several elements defined by 'indeces'.  
		This data type can be used to model represent pairwise correlation of expression profiles for a set of genes.		 
		
		indeces - indeces of elements to be compared
		comparison_values - values representing a parituclar type of comparison between elements. 
			Expected to be symmetric: comparison_values[i][j] = comparison_values[j][i].
			Diagonal values: comparison_values[i][i] = 0
			
		avgs - mean of comparison_values for each element	
		mins - min of comparison_values for each element
		maxs - max of comparison_values for each element
		stds - std of comparison_values for each element
	*/		
	typedef structure{
		list<int> indeces;
		list<list<float>> comparison_values;
		list<float> avgs;	
		list<float> mins;	
		list<float> maxs;
		list<float> stds;
	} PairwiseComparison;
	
	
 	/*
		Data type for bulk queries. It provides all necessary data to visulize basic properties of ExpressionMatrix 
		
		mtx_descriptor - decriptor of the matrix as a whole
		row_descriptors - descriptor for each row in the matrix (provides basic properties of the features)
		column_descriptors - descriptor for each column in the matrix (provides basic properties of the conditions)
		row_stats - basic statistics for each row (feature) in the matrix, like mean, min, max, etc acorss all columns (conditions)
		column_stats - basic statistics for each row (feature) in the matrix, like mean, min, max, etc across all rows (features)	
	*/		
	typedef structure{
		MatrixDescriptor mtx_descriptor;
		list<ItemDescriptor> row_descriptors;
		list<ItemDescriptor> column_descriptors;
		list<ItemStat> row_stats;
		list<ItemStat> column_stats;		
	} MatrixStat;
	
	
 	/*
		Data type for bulk queries. It provides various statistics calculated on sub-matrix. The sub-matrix is defined by a subset of rows and columns via parameters.
		Parameters will also define the required types of statics.
				
		mtx_descriptor - basic properties of the source matrix
		
		row_descriptors - descriptor for each row in a subset defined in the parameters
		column_descriptors - descriptor for each column in a subset defined in the parameters
		
		row_set_stats - basic statistics for a subset of rows calculated on a subset of columns 
		column_set_stat - basic statistics for a subset of columns calculated on a subset of rows
		
		mtx_row_set_stat - basic statistics for a subset of rows calculated on ALL columns in the matrix (can be used as a backgound in comparison with row_set_stats)
		mtx_column_set_stat - basic statistics for a subset of columns calculated on ALL rows in the matrix (can be used as a backgound in comparison with column_set_stat)
		
		row_pairwise_correlation - pariwise perason correlation for a subset of rows (features)  
		column_pairwise_correlation - pariwise perason correlation for a subset of columns (conditions)
		
		values - sub-matrix representing actual values for a given subset of rows and a subset of columns														
	*/		
	typedef structure{	
		MatrixDescriptor mtx_descriptor;
		
		list<ItemDescriptor> row_descriptors;
		list<ItemDescriptor> column_descriptors;
		
		ItemSetStat row_set_stats;
		ItemSetStat column_set_stat;
		
		ItemSetStat mtx_row_set_stat;
		ItemSetStat mtx_column_set_stat;
		
		PairwiseComparison row_pairwise_correlation;
		PairwiseComparison column_pairwise_correlation;
		
		list<list<float>> values;						
	} SubmatrixStat;
	
	
	
	/*******************************************
	* data API: parameters and functions      *
	******************************************/    
	
   /*
		Parameters to retrieve MatrixDescriptor		
	*/        
    typedef structure{
        ws_matrix_id input_data;        
    } GetMatrixDescriptorParams;  
      
    funcdef get_matrix_descriptor(GetMatrixDescriptorParams)
    	returns (MatrixDescriptor) authentication required;
    	    	
	
    /*
    	Parameters to get basic properties for items from the Float2D type of matrices. 
    	
    	input_data - worskapce reference to the ExpressionMatrix object (later we should allow to work with other Float2DMatrix-like matrices, e.g. fitness)
    	item_indeces - indeces of items for whch descriptors should be built. Either item_indeces or item_ids should be provided. If both are provided, item_indeces will be used.
    	item_ids - ids of items for whch descriptors should be built. Either item_indeces or item_ids should be provided. If both are provided, item_indeces will be used.
    	requested_property_types - list of property types to be populated for each item. Currently supported property types are: 'function'      	
    */  	
	typedef structure{
        ws_matrix_id input_data;        
    	list<int> item_indeces;
    	list<string> item_ids;
    	list<string> requested_property_types;
	} GetMatrixItemDescriptorsParams;
	
	
    funcdef get_matrix_row_descriptors(GetMatrixItemDescriptorsParams) 
    	returns (list<ItemDescriptor>) authentication required;
    		
    funcdef get_matrix_column_descriptors(GetMatrixItemDescriptorsParams) 
    	returns (list<ItemDescriptor>) authentication required;
	
    /*
    	Parameters to get statics for a set of items from the Float2D type of matrices. 
    	
    	input_data - worskapce reference to the ExpressionMatrix object (later we should allow to work with other Float2DMatrix-like matrices, e.g. fitness)
    	item_indeces_for - indeces of items FOR whch statistics should be calculated 
    	item_indeces_on - indeces of items ON whch statistics should be calculated
    	fl_indeces_on - defines whether the indeces_on should be populated in ItemStat objects. The default value = 0. 
    	    	
    */       
    typedef structure{
        ws_matrix_id input_data;
    	list<int> item_indeces_for;
    	list<int> item_indeces_on;
    	boolean fl_indeces_on;
    } GetMatrixItemsStatParams;
            
    funcdef get_matrix_rows_stat(GetMatrixItemsStatParams) 
    	returns (list<ItemStat>) authentication required;
    	
    funcdef get_matrix_columns_stat(GetMatrixItemsStatParams) 
    	returns (list<ItemStat>) authentication required;
    
    /*
		Parameters to get statistics for a set of items from the Float2D type of matrices in a form of ItemSetStat. 
		This version is more flexible and will be later used to retrieve set of sets of elements.		  
    	
    	input_data - worskapce reference to the ExpressionMatrix object (later we should allow to work with other Float2DMatrix-like matrices, e.g. fitness)
    	item_indeces_for - indeces of items FOR wich statistics should be calculated 
    	item_indeces_on - indeces of items ON wich statistics should be calculated
    	fl_indeces_on - defines whether the indeces_on should be populated in SetStat objects. The default value = 0. 
    	fl_indeces_for - defines whether the indeces_for should be populated in SetStat objects. The default value = 0.    	 
    	fl_avgs - defines whether the avgs should be populated in SetStat objects. The default value = 0. 
    	fl_mins - defines whether the mins should be populated in SetStat objects. The default value = 0. 
    	fl_maxs - defines whether the maxs should be populated in SetStat objects. The default value = 0. 
    	fl_stds - defines whether the stds should be populated in SetStat objects. The default value = 0. 
    	fl_missing_values - defines whether the missing_values should be populated in SetStat objects. The default value = 0. 
    */       
    typedef structure{
        ws_matrix_id input_data;
        
    	list<int> item_indeces_for;
    	list<int> item_indeces_on;
        
        boolean fl_indeces_on;
        boolean fl_indeces_for;
        boolean fl_avgs;
        boolean fl_mins;
        boolean fl_maxs;
        boolean fl_stds;
        boolean fl_missing_values;
        
    } GetMatrixSetStatParams;

    /*
		Parameters to retrieve statistics for set of sets of elements. 
		
		In relation to ExpressionMatrix, these parameters can be used to retrive sparklines for several gene clusters generated on the 
		same ExpressionMatrix in one call.  
		
		params - list of params to retrive statistics for a set of items from the Float2D type of matrices.
	*/
    typedef structure{
		list<GetMatrixSetStatParams> params;
    } GetMatrixSetsStatParams;

    
    funcdef get_matrix_row_sets_stat(GetMatrixSetsStatParams)
    	returns (list<ItemSetStat>) authentication required;
    
    funcdef get_matrix_column_sets_stat(GetMatrixSetsStatParams)
    	returns (list<ItemSetStat>) authentication required;

    	    
   /*
		Parameters to retrieve MatrixStat		
	*/        
    typedef structure{
        ws_matrix_id input_data;        
    } GetMatrixStatParams;  
      
    funcdef get_matrix_stat(GetMatrixStatParams)
    	returns (MatrixStat) authentication required;


   /*
		Parameters to retrieve SubmatrixStat	
		input_data - reference to the source matrix        
        row_indeces - indeces defining a subset of matrix rows. Either row_indeces (highest priorery) or row_ids should be provided.
        row_ids - ids defining a subset of matrix rows. Either row_indeces (highest priorery) or row_ids should be provided.
        
        column_indeces - indeces defining a subset of matrix columns. Either column_indeces (highest priorery) or column_ids should be provided.
        column_ids - ids defining a subset of matrix columns. Either column_indeces (highest priorery) or column_ids should be provided.
        
        fl_row_set_stats - defines whether row_set_stats should be calculated in include in the SubmatrixStat. Default value = 0
        fl_column_set_stat - defines whether column_set_stat should be calculated in include in the SubmatrixStat. Default value = 0
        
		fl_mtx_row_set_stat - defines whether mtx_row_set_stat should be calculated in include in the SubmatrixStat. Default value = 0
		fl_mtx_column_set_stat - defines whether mtx_column_set_stat should be calculated in include in the SubmatrixStat. Default value = 0
		
		fl_row_pairwise_correlation - defines whether row_pairwise_correlation should be calculated in include in the SubmatrixStat. Default value = 0        
		fl_column_pairwise_correlation - defines whether column_pairwise_correlation should be calculated in include in the SubmatrixStat. Default value = 0
		fl_values - defines whether values should be calculated in include in the SubmatrixStat. Default value = 0	
	*/        
    typedef structure{
        ws_matrix_id input_data;        
        list<int> row_indeces;
        list<string> row_ids;
        
        list<int> column_indeces;
        list<string> column_ids;
        
        boolean fl_row_set_stats;
        boolean fl_column_set_stat;
        
		boolean fl_mtx_row_set_stat;
		boolean fl_mtx_column_set_stat;
		
		boolean fl_row_pairwise_correlation;        
		boolean fl_column_pairwise_correlation;
		boolean fl_values;		        
        
    } GetSubmatrixStatParams;   
     
    funcdef get_submatrix_stat(GetSubmatrixStatParams)
    	returns (SubmatrixStat) authentication required;

    /*
        input_shock_id and input_file_path - alternative intput params,
        genome_ref - optional reference to a Genome object that will be
            used for mapping feature IDs to,
        fill_missing_values - optional flag for filling in missing 
            values in matrix (default value is false),
        data_type - optional filed, value is one of 'untransformed',
            'log2_level', 'log10_level', 'log2_ratio', 'log10_ratio' or
            'unknown' (last one is default value),
        data_scale - optional parameter (default value is '1.0').
    */
    typedef structure {
        string input_shock_id;
        string input_file_path;
        ws_genome_id genome_ref; 
        boolean fill_missing_values;
        string data_type;
        string data_scale;
        string output_ws_name;
        string output_obj_name;
    } TsvFileToMatrixParams;

    typedef structure {
        ws_matrix_id output_matrix_ref;
    } TsvFileToMatrixOutput;

    funcdef tsv_file_to_matrix(TsvFileToMatrixParams params)
        returns (TsvFileToMatrixOutput) authentication required;

    typedef structure {
        ws_matrix_id input_ref;
        boolean to_shock;
        string file_path;
    } MatrixToTsvFileParams;

    typedef structure {
        string file_path;
        string shock_id;
    } MatrixToTsvFileOutput;

    funcdef matrix_to_tsv_file(MatrixToTsvFileParams params)
        returns (MatrixToTsvFileOutput) authentication required;

    typedef structure {
        ws_matrix_id input_ref;
    } ExportMatrixParams;

    typedef structure {
        string shock_id;
    } ExportMatrixOutput;

    funcdef export_matrix(ExportMatrixParams params)
        returns (ExportMatrixOutput) authentication required;

    /*
        format - optional field, can be one of "TSV" or "SIF" ("TSV" is default value).
    */
    typedef structure {
        ws_featureclusters_id input_ref;
        boolean to_shock;
        string file_path;
        string format;
    } ClustersToFileParams;

    typedef structure {
        string file_path;
        string shock_id;
    } ClustersToFileOutput;

    funcdef clusters_to_file(ClustersToFileParams params)
        returns (ClustersToFileOutput) authentication required;

    typedef structure {
        ws_featureclusters_id input_ref;
    } ExportClustersTsvParams;

    typedef structure {
        string shock_id;
    } ExportClustersTsvOutput;

    funcdef export_clusters_tsv(ExportClustersTsvParams params)
        returns (ExportClustersTsvOutput) authentication required;

    typedef structure {
        ws_featureclusters_id input_ref;
    } ExportClustersSifParams;

    typedef structure {
        string shock_id;
    } ExportClustersSifOutput;

    funcdef export_clusters_sif(ExportClustersSifParams params)
        returns (ExportClustersSifOutput) authentication required;

};

