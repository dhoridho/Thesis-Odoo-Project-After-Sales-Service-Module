from odoo import api, fields, models, _
from datetime import datetime, date , timedelta
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    cs_subcon_id = fields.Many2one('material.subcon', string='Cost Sheet Subcontractor Line')
    bd_subcon_id = fields.Many2one('budget.subcon', string='Budget Subcontractor Line')
    po_subcon_id = fields.Many2one('rfq.variable.line', string='Purchase Order Subcontractor Line')

    @api.onchange('purchase_subcon', 'po_subcon_id')
    def onchange_domain_purchase_subcon(self):
        for rec in self:
            if rec.is_subcon == True:
                return {
                    'domain': {'po_subcon_id': [('variable_id', '=', rec.purchase_subcon.id)]}
                }
            
    @api.onchange('po_subcon_id')
    def onchange_purchase_subcon_line(self):
        for rec in self:
            if rec.is_subcon == True:
                if rec.po_subcon_id:
                    rec.cs_subcon_id = rec.po_subcon_id.cs_subcon_id.id
                    rec.bd_subcon_id = rec.po_subcon_id.bd_subcon_id.id
                    rec.work_subcon_weightage = rec.po_subcon_id.dp_amount_percentage * 100
                    
                    if rec.purchase_subcon.sub_contracting == 'main_contract':
                        rec.name = rec.po_subcon_id.project_scope.name + ' - ' + rec.po_subcon_id.section.name + ' - ' + rec.po_subcon_id.variable.name
                    else:
                        rec.name = 'Addendum - ' + rec.po_subcon_id.project_scope.name + ' - ' + rec.po_subcon_id.section.name + ' - ' + rec.po_subcon_id.variable.name,