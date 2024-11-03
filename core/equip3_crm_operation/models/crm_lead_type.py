from odoo import models, fields, api, _

class CrmLeadType(models.Model):
    _name = 'crm.lead.type'
    _description = "Crm Lead Type"
    _rec_name = "description"

    description = fields.Char(string="Description", required=True)