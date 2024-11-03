import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Script generated for node AWS Glue Data Catalog
AWSGlueDataCatalog_node1728995960465 = glueContext.create_dynamic_frame.from_catalog(database="meta_catalog_db", table_name="public_aml_transactions", transformation_ctx="AWSGlueDataCatalog_node1728995960465")

# Script generated for node Change Schema
ChangeSchema_node1728995977283 = ApplyMapping.apply(frame=AWSGlueDataCatalog_node1728995960465, mappings=[("date", "date", "date", "date"), ("amount", "decimal", "amount", "decimal"), ("receiver_bank_location", "string", "receiver_bank_location", "string"), ("receiver_account", "string", "receiver_account", "string"), ("sender_bank_location", "string", "sender_bank_location", "string"), ("is_laundering", "int", "is_laundering", "int"), ("received_currency", "string", "received_currency", "string"), ("laundering_type", "string", "laundering_type", "string"), ("payment_currency", "string", "payment_currency", "string"), ("payment_type", "string", "payment_type", "string"), ("sender_account", "string", "sender_account", "string"), ("time", "timestamp", "time", "timestamp")], transformation_ctx="ChangeSchema_node1728995977283")

# Script generated for node Amazon S3
AmazonS3_node1728995988593 = glueContext.getSink(path="s3://elt-output-bucket", connection_type="s3", updateBehavior="LOG", partitionKeys=[], enableUpdateCatalog=True, transformation_ctx="AmazonS3_node1728995988593")
AmazonS3_node1728995988593.setCatalogInfo(catalogDatabase="meta_catalog_db",catalogTableName="aml_transactions")
AmazonS3_node1728995988593.setFormat("glueparquet", compression="snappy")
AmazonS3_node1728995988593.writeFrame(ChangeSchema_node1728995977283)
job.commit()