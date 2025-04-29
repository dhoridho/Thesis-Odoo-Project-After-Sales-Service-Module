from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class AfterSalesOperationReportWizard(models.TransientModel):
    _name = 'service.request.report'