from odoo import api, fields, models


class ProgressiveClaimInherit(models.Model):
    _inherit = 'progressive.claim'

    dash_actual_progress = fields.Float(related='actual_progress', string="Actual Progress", digits=(2,2), store=True)
    dash_approved_progress = fields.Float(related='approved_progress', string='Approved Progress', digits=(2,2), store=True)
    dash_invoiced_progress = fields.Float(related='invoiced_progress', string='Invoiced Progress', digits=(2,2), store=True)
    dash_contract_amount = fields.Float(related='contract_amount', string='Contract Amount', store=True)
    dash_total_invoice = fields.Float(related='total_invoice', string="Total Amount Invoiced", store=True)
    dash_remaining_amount_invoiced = fields.Float(related='remaining_amount_invoiced', string="Remaining Amount Invoiced", store=True)
    dash_total_claim = fields.Float(related='total_claim', string="Total Amount Claimed", store=True)
    dash_remaining_amount = fields.Float(related='remaining_amount', string="Remaining Amount to Claim", store=True)
    # dash_project = fields.Char(related='project_contract', string="Project Contract", store=True)
    
class ProjectClaimInherit(models.Model):
    _inherit = 'project.claim'

    claim_name = fields.Char(string="Claim ID", related='invoice_id.claim_description', compute="_compute_values", store=True)
    progressive_project_id = fields.Many2one('project.project', string="Project", compute="_compute_values", store=True)
    department_type = fields.Selection(related='progressive_project_id.department_type')
    # project_id = fields.Many2one('project.project', string="Project", related='claim_id.project_id', store=True)
    # progressive_bill = fields.Boolean(related='claim_id.progressive_bill', store=True)
    progressline = fields.Float(string = 'Progress (%)', related='invoice_id.progressline', digits=(2,2), store=True)
    gross_amount = fields.Monetary(string="Gross Amount", related='invoice_id.gross_amount', currency_field='currency_id', store=True)
    dp_deduction = fields.Monetary(string="DP Deduction", related='invoice_id.dp_deduction', currency_field='currency_id', store=True)
    retention_deduction = fields.Monetary(string="Retention Deduction", related='invoice_id.retention_deduction', currency_field='currency_id', store=True)
    tax_amount = fields.Monetary(string="Tax Amount", related='invoice_id.tax_amount', currency_field='currency_id', store=True)
    amount_untaxed = fields.Float(string = 'Amount Untaxed',related='invoice_id.amount_untaxed_2', currency_field='currency_id', store=True)
    amount_deduction = fields.Monetary(string="Amount After Deduction", related='invoice_id.amount_deduction', currency_field='currency_id', store=True)
    amount_invoice = fields.Monetary(string="Amount Invoice", related='invoice_id.amount_invoice', currency_field='currency_id', store=True)
    amount_bill = fields.Monetary(string="Amount Bill", related='invoice_id.amount_invoice', currency_field='currency_id', store=True)
    amount_claim = fields.Monetary(string="Amount Claimed", related='invoice_id.total_claim', currency_field='currency_id', store=True)
    remaining_amount = fields.Monetary(string="Remaining Amount", related='invoice_id.amount_residual', currency_field='currency_id', store=True)



    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if  self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('progressive_project_id','in',self.env.user.project_ids.ids))
        return super(ProjectClaimInherit, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)


    @api.depends('project_id', 'claim_id')
    def _compute_values(self):
        for rec in self:
            rec.progressive_project_id = rec.project_id
            rec.claim_name = rec.invoice_id.claim_description

            # Change field string to Amount Bill (work around to view amount bill in pivot view)
            # Attrs doesn't seem to work in pivot view
            # if self.progressive_bill == True:
            #     self.env['project.claim']._fields['amount_invoice'].string = 'Amount Bill'
            



