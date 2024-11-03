from odoo import models, fields, api


class ConstructionCostInProgress(models.Model):
    _name = 'cost.in.progress'
    _description = 'Cost In Progress'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch')
    name = fields.Char('Name')
    project_id = fields.Many2one('project.project', string="Project")
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    cip_line_ids = fields.One2many('cost.in.progress.line', 'cip_id', string="Cost In Progress")


class ConstructionCostInProgressLine(models.Model):
    _name = 'cost.in.progress.line'
    _description = 'Cost In Progress Line'

    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    cip_id = fields.Many2one('cost.in.progress')
    product_id = fields.Many2one('product.product', string = 'Product')
    label = fields.Char('Label')
    account_id = fields.Many2one('account.account', string = 'Account')
    amount = fields.Float(string="Amount")

    @api.depends('cip_id.cip_line_ids', 'cip_id.cip_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.cip_id.cip_line_ids:
                no += 1
                l.sr_no = no

    



    
    
