`1.2.35                                                      [11/11/2021]`
***************************************************************************
- Add RBS option on evalution.

`1.2.34                                                      [04/10/2021]`
***************************************************************************
- Add graph view on appointment.

`1.2.33                                                       [29/09/2021]`
***************************************************************************
- Avoid duplication of invocie when duplicating pateint, treatement.

`1.2.32                                                       [13/09/2021]`
***************************************************************************
- Improved code for patient weight, height, temp, spo2 measure.

`1.2.31                                                       [25/08/2021]`
***************************************************************************
- Improved code for family relation.

`1.2.30                                                       [17/08/2021]`
***************************************************************************
- Improved code for adding new support of WS.

`1.2.29                                                       [19/07/2021]`
***************************************************************************
- Added new activity view on appointment.

`1.2.28                                                       [07/07/2021]`
***************************************************************************
- Added option to validate payment on appointment confirmation.

`1.1.27                                                       [05/07/2021]`
***************************************************************************
- Apply group to manage Ethnic group and tribe Data.
- Added option to manage auto activity for followup. (Option to configure
default appointment type in configuration.)
- Add option to manage responsible user on appointment.
- Show Pregency warning error when any mediciane with preg waring get 
added on prescrption where pregnency waring is ticked.
- Improved Usablity for appointment UI.

`1.1.26                                                       [02/07/2021]`
***************************************************************************
- Imprived view for department.
- Added option to set default cosulation and followup service on 
department level.

`1.1.25                                                       [10/06/2021]`
***************************************************************************
- Fix issue of access error for appointment creation from portal.

`1.1.24                                                       [03/06/2021]`
***************************************************************************
- Improved code for prescripon action issue from other users.
- Show general infor to receptionist also so she can add chief complaint.
- Fix issue of access when receptiost cancel appointment. Without 
access to account module.

`1.1.23                                                       [20/05/2021]`
***************************************************************************
- Added chart option for weight, height, RR, Spo2, BP and HR.

`1.1.22                                                       [29/04/2021]`
***************************************************************************
- Improved code to fix error on report format selection.

`1.1.21                                                       [06/04/2021]`
***************************************************************************
- Added Patint evaluation PDF report.
- Add Chatter in Evaluation Records.

`1.1.20                                                       [02/04/2021]`
***************************************************************************
- Updated the demo records of product to resolve the issue of stock inventory
valuation in test cases

`1.1.19                                                       [30/03/2021]`
***************************************************************************
- Updated code for updating total qty of perscription line on change of 
state also.

`1.1.18                                                       [25/03/2021]`
***************************************************************************
- Improved medical advice report to print Disease.

`1.1.17                                                       [24/03/2021]`
***************************************************************************
- Added names on page views for inheritance support.
- Improved invoice report.

`1.1.16                                                       [16/03/2021]`
***************************************************************************
- ALERT: Take backup before updating module.
- folloing field types havebeen chanegd:
     temp, hr, rr, systolic_bp, diastolic_bp, spo2

`1.0.16                                                       [16/03/2021]`
***************************************************************************
- Allow nurse to mark evaluation on popup and show abi and bmi state
 properly on appointment.

`1.0.15                                                       [16/03/2021]`
***************************************************************************
- Allow nurse to create and finish evaluation.

`1.0.14                                                       [09/03/2021]`
***************************************************************************
- Show nurse and dr category related Schedules.

`1.0.13                                                       [06/03/2021]`
***************************************************************************
- Avoid copying fields when duplicating record for appointment 
and prescription.

`1.0.12                                                       [26/02/2021]`
***************************************************************************
- Allow to create patient for portal user also.

`1.0.11                                                       [26/02/2021]`
***************************************************************************
- Added smart button Precsription, Treatment and Appointment in Physican.

`1.0.10                                                       [19/02/2021]`
***************************************************************************
- Imprvoed code for allowing manuly entry for prescription qty.

`1.0.9                                                       [12/02/2021]`
***************************************************************************
- Imprvoed code for followup conf on HMS setting.

`1.0.8                                                       [10/02/2021]`
***************************************************************************
- Fix issue of prescripion send by mail template issue.

`1.0.7                                                       [02/02/2021]`
***************************************************************************
- Set default timer propelry on change of physician nnd set dureation on 
change of end date.

`1.0.6                                                       [29/01/2021]`
***************************************************************************
- Updated Translated File.
- Add option to create patient from partner.

`1.0.5                                                       [25/01/2021]`
***************************************************************************
- Updated Search View.

`1.0.4                                                       [09/01/2020]`
***************************************************************************
- Added proper genetic risk view and menu.

`1.0.3                                                       [11/11/2020]`
***************************************************************************
- Search Precsription by medicine name.

`1.0.2                                                        [29/10/2020]`
***************************************************************************
- Add invoice ref and origin also on insurance invoice.

`1.0.1                                                        [10/10/2020]`
***************************************************************************
- Launched Module for v14 with following changes.

Patient:
- Rename patient_diseases to patient_diseases_ids
- Rename genetic_risks to genetic_risks_ids
- Rename family_history to family_history_ids

Physician:
- Rename government_id to medical_license
- Rename specialty to specialty_id

Appointment:
- replace diseas_id by diseases_ids
- Add auotmatic next followup date

Prescription:
- replace diseas_id by diseases_ids

Deaprtment:
- replace patient_department by patient_department
- Added department_type to manage appointment types.

Add option to print Qr on prescription for authentication.
Add option to manage planning date and duration on appoitnment.
Add new department_type to manage diff dipartment types in speciality.
Add new Evaluation Object.

Split module with acs_hms_base and move Patient, Physician and Drug 
related code in that module