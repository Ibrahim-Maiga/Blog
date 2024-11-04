---
layout: post
title: "Building an Analytics Solution for Effective AML Transaction Monitoring"
subtitle: "Streamlining Data Migration, Transformation, and Querying"
description: ""
author: "Ibrahim Maïga"
date: 2024-11-01
image: "/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/IMG_1624.JPG"
published: true
tags: [ETL Pipeline, PostgreSQL, DMS, RDS, Aurora MySQL, Glue, Athena, S3]
categories: [Tech]
showtoc: true
---
<center>Osaka City Skyline, Taken in Osaka, Japan, Summer 2024</center>

> This project stems from my desire to reconcile two of my core interests: data science and finance. Designed to be fully reproducible, it’s perfect for anyone looking to gain hands-on experience with data engineering or add a robust, real-world project to their portfolio. Each decision in this project was guided by a trade-off between enhancing security and controlling costs, while strictly adhering to the principle of least privilege.

![](/img/2024-10-01-Building-an-Analytics-Solution-for-Effective-AML-Transaction-Monitoring/AML Project Architecture Diagram.png)
<center>Architecture Diagram</center>

# Context 

At the start of a customer relationship, banks gather personal data to verify the customer’s identity through Know Your Customer (KYC) procedures. These records form the basis for monitoring future transactions.
Financial institutions use automated software to monitor transactions in real-time, flagging those that exceed predefined thresholds or show unusual patterns. Suspicious Activity Reports (SARs) are generated if a transaction is deemed questionable. 

Anti-Money Laundering (AML) regulations require institutions to keep records of transactions for a minimum period. This includes details of transactions, customer profiles, and the SARs filed.
When a transaction or series of transactions trigger suspicion (such as structuring, large cash deposits, or transfers to high-risk countries), institutions are required to file SARs with regulators. These reports often include transaction details, customer information, and reasons for suspicion.

# Project Scenario

A financial institution processes thousands of transactions daily. To ensure regulatory compliance, the company must periodically review its AML systems and transaction records. Regulators may conduct audits to ensure that the organization is effectively tracking and reporting suspicious transactions. To mitigate non-compliance risk, the institution wants to strengthen its governance by periodically querying AML transaction data without straining the primary transactional database, which runs on Amazon Aurora MySQL.

As the company’s data engineer, I will design and implement an ETL pipeline using AWS Glue to extract, transform, and load data from Aurora MySQL into an Amazon S3 bucket designated as the ETL-output-bucket. A second S3 bucket will be set up to store query results. Finally, I’ll test the system using Amazon Athena to query the data stored in the ETL-output-bucket, ensuring AML analysts have seamless access to transaction data, enhancing the AML monitoring framework.

# Financial Cost

The total cost of this project was just over 10 USD, primarily due to an initial misconfiguration of partition settings in the Glue job. This led to the unintended creation of thousands of small tables during its first 10-minute run, consuming substantial compute resources and occupying over 300 MB in the ETL-output-bucket. However,  I eventually identified the issue, halted the Glue job, and corrected the partitioning error. Following my detailed guide carefully and completing the project in a single attempt could potentially bring costs down to around half of this amount.

![](/img/2024-10-01-Building-an-Analytics-Solution-for-Effective-AML-Transaction-Monitoring/cost1.png)
<center>Services cost and usage graph</center>

![](/img/2024-10-01-Building-an-Analytics-Solution-for-Effective-AML-Transaction-Monitoring/cost2.png)
<center>Instance type cost and usage graph</center>

![](/img/2024-10-01-Building-an-Analytics-Solution-for-Effective-AML-Transaction-Monitoring/cost3.png)
<center>Usage type cost and usage graph</center>

![](/img/2024-10-01-Building-an-Analytics-Solution-for-Effective-AML-Transaction-Monitoring/cost4.png)
<center>API operations cost and usage graph</center>

![](/img/2024-10-01-Building-an-Analytics-Solution-for-Effective-AML-Transaction-Monitoring/cost5.png)
<center>Free tier offers in use</center>
/img/2024-10-01-Building-an-Analytics-Solution-for-Effective-AML-Transaction-Monitoring/Create PostgreSQL DB, load aml_transactions table, & preprocessing.JPG

# Prerequisites

Before running the pipeline, we need data in the transactional database. While multiple methods can be used to load data into it, I chose to incorporate a database migration phase to add depth to the project. This process involves configuring an on-premises PostgreSQL server, creating a database on it, and storing the AML transaction data locally. We’ll then use AWS Database Migration Service (DMS) to transfer the database from our local PostgreSQL server to an Aurora MySQL cluster in the cloud, setting the stage for ETL operations.

It should be noted that AWS DMS is currently incompatible with PostgreSQL versions 16 and 17. Therefore, I opted for PostgreSQL version 15, ensuring full compatibility with DMS and a smooth migration process.

# Step-by-Step Guide

## Step 1: Setup Your Postgres Database 

First, install PostgreSQL version 15 on your local machine (which creates a server by default), and then you can manage the server settings and databases using the pgAdmin tool or by executing SQL commands through <code>psql</code>. While I executed the project using PowerShell on a Windows device, the following commands can easily be adapted for use in any command-line interface (CLI).

To connect to your PostgreSQL instance using the <code>psql</code> command-line tool, from the Windows Command Prompt or PowerShell, execute the following command:

```powershell
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres
```

During the PostgreSQL installation, you defined a password for the <code>postgres</code> superuser account. Enter this password after executing the previous command and press Enter to launch <code>psql</code>.

```psql
\l       -- List all the databases that are available in the PostgreSQL server
```
```psql
create database aml_transactions_db;
```
```psql
\c aml_transactions_db;      -- Connect to aml_transactions_db database
```
```psql
create table aml_transactions (
    Time TIME,
    Date DATE,
    Sender_account VARCHAR(10),
    Receiver_account VARCHAR(10),
    Amount DECIMAL(10,2),
    Payment_currency VARCHAR(10),
    Received_currency VARCHAR(10),
    Sender_bank_location VARCHAR(15),
    Receiver_bank_location VARCHAR(15),
    Payment_type VARCHAR(15),
    Is_laundering BOOLEAN,
    Laundering_type VARCHAR(25),
    Sender_dob DATE,
    Receiver_dob DATE
);
```
```psql
\copy aml_transactions(Time, Date, Sender_account, Receiver_account, Amount, Payment_currency, Received_currency, Sender_bank_location, Receiver_bank_location, Payment_type, Is_laundering, Laundering_type, Sender_dob, Receiver_dob) FROM 'path/to/sample_AML.csv' DELIMITER ',' CSV HEADER;      -- Insert data from the sample_AML.csv file into the aml_transactions table in your aml_transactions_db database
```
```psql
select * from aml_transactions limit 5;     -- Show 5 first rows within the aml_transactions table
```
```psql
ALTER TABLE aml_transactions
ALTER COLUMN Is_laundering TYPE integer USING CASE 
    WHEN Is_laundering THEN 1
    ELSE 0
END;             -- Change the column type from boolean to integer
```
```psql
select * from aml_transactions limit 5;     -- Check the changes
```

Step 2: Set Up Amazon RDS Aurora MySQL

<iframe src="https://scribehow.com/embed/Creating_an_RDS_Aurora_MySQL_Database_on_AWS__Fa2K9uj2RCCnGVnwSDbkqw?as=video" width="100%" height="640" allowfullscreen frameborder="0"></iframe>

Step 3: Use AWS Database Migration Service (DMS)
3.1 Configure AWS DMS to migrate data from Postgres to Aurora:

In the AWS Console, go to AWS DMS.
Set up a replication instance:
Create a new Replication Instance with the appropriate size.
Create source and target endpoints:
Source: Postgres database (ensure the VPC and security group settings allow connectivity to your Postgres database).
Target: Aurora MySQL database.
Create a migration task:
Use Full load to migrate the entire dataset from Postgres to Aurora MySQL.
Make sure you map the tables and columns correctly.
Potential Issues:

Endpoint connectivity: Test both endpoints before migration to ensure Postgres and Aurora MySQL are accessible from the DMS instance.
Replication Instance Size: If migration takes too long, consider increasing the size of the replication instance.
Step 4: Set Up S3 Buckets
4.1 Create S3 Buckets for ETL outputs:

In the AWS Console, go to Amazon S3.
Create two buckets:
One for storing the ETL output data (etl-output-bucket).
Another for saving query results (query-output-bucket).
Potential Issues:

Permissions: Ensure both buckets have the proper IAM roles and bucket policies so AWS Glue and Athena can write to and read from these buckets.
Step 5: Set Up AWS Glue for ETL
5.1 Create a Glue Crawler to catalog your data:

In the AWS Console, go to AWS Glue.
Create a Crawler that connects to your Aurora MySQL database:
Set up a JDBC connection to your Aurora MySQL cluster.
The Crawler will automatically discover the schema from Aurora and create a table in the Glue Data Catalog.
Run the Crawler and ensure the schema is properly reflected in Glue Data Catalog.
5.2 Create an AWS Glue job to transform the data:

Use Glue Studio to create a new visual job.

Set the source as the table in the Glue Data Catalog (from Aurora).

Apply transformations, such as removing PII data:

Example transformation script to remove date of birth columns:

python
Copy code
import pyspark.sql.functions as F

def transform_data(df):
    return df.drop("Sender_dob", "Receiver_dob")
Write the output to the ETL output bucket.

Potential Issues:

Glue Crawler Connectivity: Ensure the JDBC connection has the right security group and access permissions.
Job Failure: Check CloudWatch Logs for job failures. Adjust memory and worker node configurations if the job runs out of memory.
Step 6: Use Amazon Athena for Queries
6.1 Configure Athena to query the data:

In the AWS Console, go to Amazon Athena.
Set the query result output location to the query-output-bucket.
Use Athena’s query editor to run SQL queries on the transformed data stored in the S3 bucket.
Here’s an example of how to query laundering transactions (SQL from earlier):

sql
Copy code
SELECT *
FROM "etl-output-bucket"."aml_transactions"
WHERE Is_laundering = 1;
Potential Issues:

Schema Issues: Ensure that the table schema in Glue Data Catalog is correctly defined, especially after the ETL process.
Query Execution Limits: Athena charges per query, so optimize your queries to avoid high costs.
Step 7: Run On-Demand Queries for AML Analysts
AML analysts can now use Athena to run ad-hoc queries for on-demand reporting. They can access transaction data efficiently without burdening the primary OLTP database.

## ClientTrafficPolicy: Managing Traffic Between Clients and Envoy

ClientTrafficPolicy is a Policy Attachment resource in Envoy Gateway designed to configure traffic between the client and Envoy. The diagram below illustrates how ClientTrafficPolicy works:
![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/2.png)
<center> How ClientTrafficPolicy Works</center>

As shown in the diagram, ClientTrafficPolicy is applied before Envoy processes request routing. This means ClientTrafficPolicy can only be applied to Gateway resources and cannot be used with HTTPRoute or GRPCRoute resources.

ClientTrafficPolicy provides the following configuration for the client-Envoy connection:

* TCP settings: TCP Keepalive, TCP Timeout, Connection Limit, Socket Buffer Size, and Connection Buffer Size.
* TLS settings: TLS Options (including TLS Version, Cipher Suites, ALPN), and whether to enable client certificate verification.
* HTTP settings: HTTP Request Timeout, HTTP Idle Timeout, and HTTP1/HTTP2/HTTP3-specific settings (e.g., HTTP2 stream window size).
* Other settings: support for Proxy Protocol and options for retrieving the client’s original IP address (via XFF Header or Proxy Protocol).

Below is an example of a ClientTrafficPolicy:

![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/3.png)
<center>ClientTrafficPolicy Example</center>

The `client-traffic-policy-gateway` is a ClientTrafficPolicy resource attached to the `eg` Gateway resource. It configures traffic between the client and Envoy, setting various parameters including TCP Keepalive, Connection Buffer Size, HTTP Request Timeout, HTTP Idle Timeout, and how to obtain the client’s original IP address. Since the `eg` Gateway resource has two Listeners—http and https—this ClientTrafficPolicy will apply to both.

Additionally, the `client-traffic-policy-https-listener` is another ClientTrafficPolicy resource linked directly to the `https` Listener (by specifying the sectionName field in its targetRef). It overrides the `client-traffic-policy-gateway` configuration for the `https` Listener, allowing specific TLS-related parameters to be applied.

# BackendTrafficPolicy：Managing Traffic Between Envoy and Backends

BackendTrafficPolicy is similar to ClientTrafficPolicy but focuses on configuring traffic between Envoy and backend services. The diagram below illustrates how BackendTrafficPolicy works:

![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/4.png)
<center>How BackendTrafficPolicy Wors</center>

The BackendTrafficPolicy is applied during the request routing stage, allowing it to be used with both the Gateway and the HTTPRoute and GRPCRoute resources.

Note: When a BackendTrafficPolicy is applied to the Gateway, it will effectively impact all HTTPRoute and GRPCRoute resources associated with that Gateway.

BackendTrafficPolicy provides the following configuration options for managing traffic between Envoy and backend services:
* Global and local rate limiting: Envoy Gateway supports both global and local rate limiting. Global rate limiting applies a single rate limiting policy to all instances of a service, while local rate limiting applies a unique rate limiting policy to each instance.
* Load balancing: Envoy Gateway supports various load balancing algorithms, including Consistent Hashing, Least Request, Random, and Round Robin. It also supports Slow Start, which gradually introduces new backend service instances to the load balancing pool to avoid the new instance being overwhelmed by sudden traffic spikes.
* Circuit breaking: Envoy Gateway supports circuit breaking based on connection numbers, connection requests, maximum concurrent requests, and concurrent retries.
* TCP settings: TCP Keepalive, TCP Timeout, Socket Buffer Size, and Connection Buffer Size.
* HTTP settings: HTTP Request Timeout, HTTP Idle Timeout, and other HTTP-related configurations.
* Other settings: Whether to enable Proxy Protocol, use the same HTTP version as the client connection, etc.

Below is an example of BackendTrafficPolicy:

![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/5.png)
<center>BackendTraffic Example</center>

The `backend-traffic-policy-http-route` is a BackendTrafficPolicy resource attached to an HTTPRoute named `http-route`. It is used to configure traffic between Envoy and backend services. This BackendTrafficPolicy configures global rate limiting, load balancing strategies, and circuit breaker policies for the backend connections.

If you have ever configured rate limiting in [Envoy](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/other_features/global_rate_limiting) or [Istio](https://istio.io/latest/docs/tasks/policy-enforcement/rate-limit/), you know how complex it can be. You need to write a lot of configuration code to define the rate limiting policy, set up the rate limiting service, and configure the rate limiting filter in Envoy. The configuration is often scattered across multiple files, making it difficult to manage and maintain.

This is where BackendTrafficPolicy comes in. As shown in the example above, you can easily configure global rate limiting with just a few lines of YAML code, significantly reducing complexity for users. BackendTrafficPolicy abstracts the rate limiting configuration into a single resource, making it easier to manage and maintain.

# SecurityPolicy：Access Control for Requests

SecurityPolicy is used for access control, including CORS policies, Basic Auth, OIDC/OAuth, JWT Authentication, IP-based access control, JWT Claims-based access control, and External Authentication, etc. The diagram below illustrates how SecurityPolicy works:

![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/6.png)
<center>How SecurityPolicy Works</center>

Please note that the diagram above is a conceptual representation; there isn’t a dedicated “Access Control” component within Envoy Gateway. Instead, Envoy Gateway leverages Envoy’s filter chain to apply SecurityPolicy configurations for controlling access to backend services.

SecurityPolicy provides the following access control configurations:
* CORS policy: Configures Cross-Origin Resource Sharing (CORS) policies, including allowed origins, allowed headers, allowed methods, etc.
* Authentication: Supports various authentication methods, including JWT Token, OIDC, Basic Auth, etc.
* Authorization: Supports authorization based on the client’s original IP, JWT Token Claims, etc.
* ExtAuth: Supports forwarding requests to an external service for authentication.

Below is an example of SecurityPolicy:
![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/7.png)
<center>SecurityPolicy Example</center>

The `security-policy-http-route` is a SecurityPolicy resource attached to an HTTPRoute named `http-route`, it is configured with OIDC authentication and IP-based access control.

By leveraging SecurityPolicy, you can offload the security policies enforcement—such as user authentication and access control—from your application code to Envoy Gateway, significantly simplifying your application code while  greatly enhancing its security posture. Envoy Gateway offers out-of-the-box security policies that support various user authentication and authorization methods. Addtionaly, if you need to integrate with your legacy auth services, you can easily do so through ExtAuth.

# EnvoyExtensionPolicy: Custom Extensions

While Envoy Gateway offers extensive traffic management features, there may be specific requirements that its built-in capabilities can’t address. In such cases, you can extend Envoy’s functionality using EnvoyExtensionPolicy. This policy allows you to load custom extensions into Envoy to execute user-defined logic for request and response processing.

EnvoyExtensionPolicy supports two types of extensions:
* WebAssembly(Wasm) extensions: WebAssembly is a high-performance binary format that can run within Envoy. Users can implement custom request and response processing using WebAssembly extensions.
* External Process extensions: External Process extensions allow users to process requests and responses through an external process. The external process can be deployed separately, and Envoy Gateway communicates with it via remote procedure calls.

### WebAssembly(Wasm) Extensions

Envoy Gateway enhances Envoy’s native Wasm support by allowing Wasm extensions to be packaged as OCI Images. This means you can bundle your custom Wasm extensions into OCI Images, store them in container registries, and load them through EnvoyExtensionPolicy.

OCI Image support offers version control and enhanced security for Wasm extensions. You can specify the extension’s version via image tags and enforce accee control by storing them in private registries. Plus, you can leverage the broader OCI ecosystem for packaging, distributing, and managing Wasm extensions.

The diagram below illustrates how Wasm OCI Image works in Envoy Gateway:  
![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/8.png)
<center>Envoy Gateway Wasm OCI Image</center>

In addition to OCI Images, Envoy Gateway also supports loading Wasm extensions via HTTP URLs. You can upload your Wasm extensions to an HTTP server and specify the URL in the EnvoyExtensionPolicy.

Below are examples of Wasm extensions, the ExtensionPolicy on the left uses an OCI Image to load the Wasm extension, while the one on the right uses an HTTP URL:
![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/9.png)
<center>Wasm Examples</center>

### External Process Extensions

External Process extensions are another extension mechanism offered by Envoy Gateway. This allows users to process requests and responses through an external service. The external process must be deployed separately, and Envoy Gateway communicates with it via remote procedure calls (RPC) to handle the request and response processing. This provides flexibility for running custom logic outside of Envoy’s core, enabling more advanced use cases.

The diagram below illustrates how External Process extensions work:

![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/10.png)
<center>External Process Extension</center>

When low network latency in the data path is required, you can deploy the External Process extension as a sidecar within the same Pod as Envoy Gateway. This deployment mode allows you to replace remote procedure calls (RPC) with local Unix Domain Socket (UDS) calls, significantly reducing latency.

As shown in the diagram, the External Process extension runs inside the same Pod as Envoy and communicates with Envoy using Unix Domain Sockets (UDS). You’ll need to create a Backend resource to define the UDS address for the External Process, and reference this Backend in the EnvoyExtensionPolicy.

![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/11.png)
<center>Deploying External Process Extension as a Sidecar</center>

### Choosing Between WebAssembly and External Process Extensions

Both WebAssembly (Wasm) and External Process extensions offer powerful ways to extend Envoy Gateway. But how do you choose between them? Here are a few factors to consider:

* Wasm extensions typically offer better performance because they run directly within the Envoy process. External Process extensions, by contrast, rely on network calls, which can lead to slightly lower performance. However, this can be mitigated by deploying the External Process extension as a sidecar, as illustrated in the example above.
* Functionality: Wasm runs in a sandbox environment, which imposes certain restrictions on system calls and access to external resources. External Process extensions have no such restrictions and can be implemented in any programming language with full access to system resources.
* Deployment: Wasm extensions can be loaded directly by Envoy from an OCI registry or HTTP URL. In contrast, External Process extensions require deploying a separate process, introducing additional management overhead.
* Security: Wasm extensions run within Envoy, meaning any bugs in the extension could compromise Envoy’s stability and potentially lead to crashes. By comparison, External Process extensions operate in their own separate process, so even if they fail, Envoy’s functionality remains unaffected.
* Scalability: External Process extensions can scale independently since they run as separate processes, allowing you to manage their resources and scaling separately from Envoy. On the other hand, Wasm extensions are embedded within Envoy and can only scale alongside Envoy itself.

In general, Wasm extensions are a good fit for lightweight, in-path data processing tasks, while External Process extensions are better suited for more complex logic that requires interaction with external systems. Your choice will depend on the specific needs of your application and environment.

In general, Wasm extensions are well-suited for lightweight, data-path processing tasks, while External Process extensions are better for handling more complex logic that involves interaction with external systems. The right choice depends on the specific requirements of your application and environment.

## EnvoyPatchPolicy: Arbitrary Configuration Patches

Envoy Gateway simplifies managing Envoy through the Gateway API and its policy extensions. While these configuration resources handle most use cases, there are always some edge cases that aren’t fully covered. In such instances, users can use EnvoyPatchPolicy to apply arbitrary patches to the generated Envoy configuration to meet specific requirements.


The diagram below illustrates how EnvoyPatchPolicy works:

![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/13.png)
<center>How EnvoyPatchPolicy Works</center>

By default, EnvoyPatchPolicy is disabled and must be explicitly enabled in the Envoy Gateway configuration. Once enabled, it allows users to add arbitrary patches to the Envoy configuration generated by Envoy Gateway, including modifications to Listener, Cluster, and Route configurations.

![](/img/2024-08-31-introducing-envoy-gateways-gateway-api-extensions/14.png)
<center>EnvoyPatchPolicy Example</center>

In this example, the EnvoyPatchPolicy resource modifies the Listener `default/eg/http` in the generated Envoy configuration. It adds the `localReplyConfig` parameter to the first filter in the Listener’s Default Filter Chain, which is the `envoy.http_connection_manager` responsible for handling HTTP traffic. This change updates the response code for 404 errors to 406 and sets the response body to “could not find what you are looking for.”

EnvoyPatchPolicy is a powerful tool, but it can be risky, as it relies on the structure and field naming conventions of the generated Envoy configuration, neither of which are guaranteed to be stable and may change with future updates to Envoy Gateway. Therefore, it should be used judiciously and only when necessary.

EnvoyPatchPolicy is generally recommended in the following scenarios:
* When Envoy Gateway does not yet support a new feature, EnvoyPatchPolicy can be used as a temporary workaround or for prototyping.
* When the generated Envoy configuration doesn’t meet certain specific requirements, EnvoyPatchPolicy can be used to make the necessary modifications.

Before creating an EnvoyPatchPolicy, you can use the `egctl` tool to view the original Envoy configuration. This allows you to identify the places where you need to make changes.

```bash
egctl config envoy-proxy all -oyaml
```

After writing the EnvoyPatchPolicy, you can also use the `egctl` tool to validate whether the patched Envoy configuration meets your expectations.

```bash
egctl experimental translate -f epp.yaml
```

Keep in mind that upgrading Envoy Gateway can lead to changes in the Envoy configuration, which might cause your existing EnvoyPatchPolicy to no longer work as expected. <font color=red>  **When upgrading, it’s important to review and assess whether the current EnvoyPatchPolicy is still applicable or needs to be updated** </font>.

## Key Takeaways

The Gateway API is the next-generation Ingress API in Kubernetes, offering a rich set of features for managing inbound traffic to clusters. Envoy Gateway is an ingress gateway built on Envoy that fully supports the capabilities of the Gateway API while providing a wide range of enhancements through the API’s extension mechanisms.

Envoy Gateway offers several advanced policies—including ClientTrafficPolicy, BackendTrafficPolicy, SecurityPolicy, EnvoyExtensionPolicy, and EnvoyPatchPolicy—which can be attached to Gateway API resources like Gateway, HTTPRoute, and GRPCRoute to enable fine-grained traffic control. With these policies, users can fine-tune the behavior of client and backend connections, enforce access control, and implement custom extensions, unlocking the full power of Envoy to manage edge traffic.


## References
1. [KubeCon China talk: Gateway API and Beyond: Introducing Envoy Gateway's Gateway API Extensions](https://kccncossaidevchn2024.sched.com/event/1eYcX/gateway-api-and-beyond-introducing-envoy-gateways-gateway-api-extensions-jie-api-daeptao-envoyjie-zha-jie-api-huabing-zhao-tetrate)：https://kccncossaidevchn2024.sched.com/event/1eYcX/gateway-api-and-beyond-introducing-envoy-gateways-gateway-api-extensions-jie-api-daeptao-envoyjie-zha-jie-api-huabing-zhao-tetrate
2. [Envoy Gateway GitHub](ttps://github.com/envoyproxy/gateway)：https://github.com/envoyproxy/gateway
3. [Kubernetes Gateway API](https://gateway-api.sigs.k8s.io)：https://gateway-api.sigs.k8s.io
4. [Kubernetes Ingress API](https://kubernetes.io/docs/concepts/services-networking/ingress)：https://kubernetes.io/docs/concepts/services-networking/ingress
5. [Policy Attachment](https://gateway-api.sigs.k8s.io/reference/policy-attachment)：https://gateway-api.sigs.k8s.io/reference/policy-attachment
