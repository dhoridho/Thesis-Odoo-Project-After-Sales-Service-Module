
from odoo import api, fields, models, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def crm_whatsapp(self):
        res = super(CrmLead, self).crm_whatsapp()
        res['context'].update({'is_crm_lead' : True})
        return res
 