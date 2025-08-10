# Odoo After-Sales Service Module

## 📋 Overview

This project is a comprehensive After-Sales Service Management Module developed for Odoo as part of a thesis project. The module extends Odoo's core functionality to provide robust after-sales service management capabilities, including service requests, warranty tracking, repair management, and customer support workflows.

<img width="1921" height="1023" alt="image" src="https://github.com/user-attachments/assets/a8c16b0f-71e8-46e6-a31b-96b700a28a42" />

<p align="center">
  <img src="https://github.com/user-attachments/assets/0a26d7c4-208b-4495-9771-7e187c790416" width="33%" />
  <img src="https://github.com/user-attachments/assets/d8db2287-b21e-42e8-8f71-c9a75e4f9521" width="33%" /> 
  <img src="https://github.com/user-attachments/assets/ee696f7e-660b-404a-9119-0feac81b012b" width="33%" />
</p>

## 🎯 Project Objectives

- Develop a comprehensive after-sales service management system
- Integrate seamlessly with existing Odoo modules (Sales, Inventory, Accounting)
- Provide efficient service request tracking and resolution
- Implement warranty management and validation
- Create detailed reporting and analytics for service operations

## ✨ Features

### Core Functionality
- **Service Request Management**: Create, track, and manage customer service requests
- **Warranty Tracking**: Automatic warranty validation and expiration alerts
- **Repair Order Management**: Complete repair workflow from diagnosis to completion
- **Technician Management**: Assign and track technician activities
- **Service History**: Complete service history for products and customers

### Advanced Features
- **Customer Portal Integration**: Allow customers to track service requests
- **Automated Notifications**: Email/SMS alerts for service milestones
- **Reporting Dashboard**: Comprehensive analytics and KPI tracking


## 🛠️ Technical Requirements

### Odoo Version
- Compatible with Odoo 14

### Python Requirements
- Python 3.8+
- PostgreSQL 12+

### Dependencies
- `base`
- `sale`
- `stock`
- `account`
- `product`
- `hr` (for employee management)

### Key Models

#### Service Request (`service.request`)
- Customer information
- Product
- Status workflow
- Assigned technician
- Parts used

#### Warranty (`warranty.claim`)
- Product reference
- Customer information
- Warranty start/end dates
- Warranty type and conditions

#### Repair Order (`repair.order`)
- Service request reference
- Parts replacement
- Quality check
- Customer approval

## 📈 Reports and Analytics

The module includes several built-in reports:
- After Sales Operation: Generating ra eport of selected operation types covering submitted requests, products, and statuses
  <img width="1115" height="431" alt="image" src="https://github.com/user-attachments/assets/cbe5468b-6e00-484c-a548-cd67b89b9419" />
  <p align="center">
    <img width="542" height="662" alt="image" src="https://github.com/user-attachments/assets/402d62b2-dc0e-4814-9606-2fc2e5f7e2d0" />
  </p>

- Technician Task Report: Individual and Team analysis showing all relevant tasks for each technician
  <img width="1082" height="358" alt="image" src="https://github.com/user-attachments/assets/d7393c41-734f-47d0-8ab9-45a9dec7d26f" />
  <p align="center">
     <img width="654" height="774" alt="image" src="https://github.com/user-attachments/assets/703dd935-497e-4045-a565-628129f9ef86" />
  </p>



## 👨‍🎓 Author

**Ridho Kurnia Putra**
- Student ID: 2501995332
- Institution: Bina Nusantara University
- Email: ridhokp@proton.me / ridho.putra@binus.ac.id
- LinkedIn: https://www.linkedin.com/in/ridhokurniaputra/

## 🙏 Acknowledgments

- Firman Rizaldi Yusup - Senior Odoo Developer at Hashmicro
- an ERP Consultant from Hashmicro 
- Bina Nusantara University - Academic institution

## 🗎 Other Documentation
<p align="center">
  <img src="https://github.com/user-attachments/assets/26d9e96a-401c-42f1-b22e-4fcee6191e23" width="32%" />
  <img src="https://github.com/user-attachments/assets/28768ae2-6c1a-47f9-b887-e2f9acd531e1" width="32%" /> 
  <img src="https://github.com/user-attachments/assets/762dede5-4047-424a-baf6-47c8465a87c9" width="32%" />
</p>
<p align="center">
  <img src="https://github.com/user-attachments/assets/11d957b9-7302-474a-90ba-205df439eb00" width="32%" />
  <img src="https://github.com/user-attachments/assets/ba18c6ca-dc33-49d4-93d4-6f47caaa8f0c" width="32%" /> 
  <img src="https://github.com/user-attachments/assets/78090df2-e9da-45df-8c39-ace1a46e2611" width="32%" />
</p>




**Note**: This module was developed as part of a thesis project for Computer Science at BINUS. It demonstrates practical application of enterprise software development principles using the Odoo framework.
