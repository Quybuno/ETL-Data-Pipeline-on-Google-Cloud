<!-- Kiến trúc Cloud-Native Real Estate Data Crawler -->

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
│  │ Cloud Scheduler │  │ Cloud Function  │  │    BigQuery     │                  │
│  │ (Job Trigger)   │  │ (ETL Logic)     │  │ (Data Warehouse)│                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        ▲
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                IaaS Layer                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Cloud Run     │  │ Cloud Storage   │  │    Terraform    │                  │
│  │ (Crawler Engine)│  │   (Data Lake)   │  │   (IaC)         │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

##  Data Flow Pipeline (Hướng: Cloud Run crawler định kỳ)

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Cloud       │───▶ │ Cloud Run     │───▶│ Cloud Storage │───▶│ Cloud Function│
│ Scheduler   │     │ (Crawler Job) │     │   (Raw Data)  │     │   (ETL Logic) │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                │
                                                                ▼
                                                        ┌──────────────┐
                                                        │   BigQuery    │
                                                        │(Data Warehouse)│
                                                        └──────────────┘
                                                                │
                                                                ▼
                                                        ┌──────────────┐
                                                        │ Looker Studio│
                                                        │ (Dashboard)  │
                                                        └──────────────┘
```

##  Component Details

###  IaaS Layer
- **Cloud Run**: Serverless container cho crawler, chạy định kỳ theo lịch.
- **Cloud Storage**: Data lake cho raw và clean data.
- **Terraform**: Infrastructure as Code (quản lý hạ tầng tự động).

###  PaaS Layer  
- **Cloud Scheduler**: Gửi HTTP request kích hoạt Cloud Run định kỳ.
- **Cloud Function**: Serverless ETL processing (transform data).
- **BigQuery**: Serverless data warehouse để lưu và phân tích dữ liệu.

###  SaaS Layer
- **Looker Studio**: Data visualization.
- **Cloud Monitoring**: System observability.
- **BigQuery Console**: Data management interface.

##  Key Benefits

1. **Cloud-Native & Serverless**: Không cần quản lý server, auto-scale theo tải.  
2. **Scheduled Automation**: Thu thập dữ liệu định kỳ, không phụ thuộc trigger upload.  
3. **Modular Architecture**: Tách riêng phần crawl, ETL, phân tích.  
4. **Cost-Effective**: Cloud Run tự tắt khi xong, chỉ trả tiền khi chạy.  
5. **Scalable**: Hỗ trợ từ vài KB tới hàng GB dữ liệu.  
6. **Observable**: Có log, alert, và monitoring tích hợp sẵn.  
