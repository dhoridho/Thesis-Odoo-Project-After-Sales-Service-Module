from odoo import fields, models, api, _

class GuaranteeTable(models.Model):
    _name = "guarantee.table"
    _description = "Guarantee Table"
    _order = "sequence"

    sequence = fields.Integer('Sequence', default=1)
    guarantee_type = fields.Selection([
        ('down_payment_guarantee', 'Down Payment Guarantee'),
        ('operational_guarantee', 'Operational Guarantee'),
        ('contractor_all_risk', 'Contractor All Risk'),
    ], string='Guarantee Type')
    amount = fields.Float("Amount")
    project_id = fields.Many2one('project.project')
    