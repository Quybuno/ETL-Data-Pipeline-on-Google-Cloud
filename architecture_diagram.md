<!-- Kiến trúc Cloud-Native ETL Pipeline -->

<!-- Sơ đồ kiến trúc tổng thể -->

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                SaaS Layer                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Looker Studio  │  │ Cloud Monitoring│  │  BigQuery       │                  │
│  │   Dashboard     │  │    Alerts       │  │   Console       │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        ▲
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                PaaS Layer                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Cloud Function  │  │ Cloud Composer  │  │    BigQuery     │                  │
│  │   (ETL Logic)   │  │ (Orchestration) │  │ (Data Warehouse)│                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        ▲
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                IaaS Layer                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Cloud Run     │  │ Cloud Storage   │  │    Terraform    │                  │
│  │   (Crawler)     │  │   (Data Lake)   │  │   (IaC)         │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

##  Data Flow Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Website   │───▶│  Cloud Run  │───▶│Cloud Storage│───▶│Cloud Function│───▶│Cloud Storage│
│  (Source)   │    │ (Crawler)   │    │   (Raw)     │    │   (ETL)     │    │  (Clean)    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                                
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│ Looker      │◀───│BigQuery     │◀───│Cloud        │◀───│Cloud        │─────────┘
│ Studio      │    │(Data        │    │Function     │    │Storage      │
│(Dashboard)  │    │ Warehouse)  │    │(ETL)        │    │(Clean)      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

##  Component Details

###  IaaS Layer
- **Cloud Run**: Serverless container cho crawler
- **Cloud Storage**: Data lake cho raw và clean data
- **Terraform**: Infrastructure as Code
- **IAM**: Identity and Access Management

###  PaaS Layer  
- **Cloud Function**: Serverless ETL processing
- **Cloud Composer**: Managed Apache Airflow
- **BigQuery**: Serverless data warehouse

###  SaaS Layer
- **Looker Studio**: Data visualization
- **Cloud Monitoring**: System observability
- **BigQuery Console**: Data management interface

##  Key Benefits

1. ** Cloud-Native**: Fully serverless và auto-scaling
2. ** Event-Driven**: Trigger-based processing
3. ** Real-time**: Near real-time data processing
4. ** Cost-Effective**: Pay-as-you-go pricing
5. ** Secure**: IAM và network security
6. ** Scalable**: Handle từ KB đến TB data

