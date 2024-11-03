{
    "name": "Singapore Employee Document Expiry",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "category": "Human Resources",
    "description":
    '''
    Module to send email for Employee Document Expiry.
    Notification for visa expiry
    employee visa expiry notification
    email notification
    mail notification for expiry
    visa management
    visa expiry management
    documents expiry
    certification expiry
    ''',
    "summary":
    '''
    Document expiry notification
    ''',
    "depends": ["sg_hr_employee"],
    "data": [
        "security/ir.model.access.csv",
        "reports/document_expiry_report_view.xml",
        "data/email_template.xml",
        "data/document_expiry_schedular_view.xml"
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "price": 15,
    "currency": 'EUR',
}
