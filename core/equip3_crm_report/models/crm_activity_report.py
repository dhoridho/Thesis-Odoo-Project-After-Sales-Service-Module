from odoo import models, fields, api, _


class ActivityReport(models.Model):
    """ CRM Lead Analysis """

    _inherit = "crm.activity.report"