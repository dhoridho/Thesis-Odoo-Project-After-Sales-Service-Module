from odoo import fields, models


class HrPayrollConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'

    module_sg_dbs_giro = fields.Boolean(
        string='DBS GIRO File for Employee Salary Payments',
        help="This help to generate Dbs giro file for salary payment upload "
        "to bank's site.")
    module_sg_nric_verification = fields.Boolean(
        string='NRIC Number Validation', help="This help to validate employee "
        "identification number for NRIC employee ID Type.")
    module_sg_cimb_report = fields.Boolean(
        string='CIMB Bank Text File Report',
        help="This will help to generate CIMB Bank text file report.")
    module_sg_ocbc_report = fields.Boolean(
        string='OCBC Bank Text File Report',
        help="This will help to generate OCBC Bank text file report.")
    module_sg_appendix8a_report = fields.Boolean(
        string='APPENDIX8A Report From IRAS',
        help="This will help to generate APPENDIX8A income-tax report.")
    module_sg_appendix8b_report = fields.Boolean(
        string='APPENDIX8B Report From IRAS',
        help="This will help to generate APPENDIX8B income-tax report.")
    module_sg_ir21 = fields.Boolean(
        string='IR21 Report as per Singapore Payroll',
        help="This will generate IR21 report as per Singapore Payroll.")
