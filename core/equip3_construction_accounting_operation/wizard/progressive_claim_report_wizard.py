from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import PyPDF2


class ProgressiveClaimReport(models.Model):
    _name = 'progressive.claim.report'
    _description = 'Progressive Claim Report'

    project_id = fields.Many2one('project.project', string='Project', required=True)
    print_type = fields.Selection([
        ('all', 'All in One'),
        ('customer', 'Customer Only'),
        ('vendor', 'Vendor Only'),
    ], string='Select Type', required=True, default='all')

    specific_print_type = fields.Selection([
        ('all', 'All Progressive Claim'),
        ('progressive', 'Specific Progressive Claim'),
    ], string='specific_print_type', required=True, default='all')

    progressive_claim_customer_option = fields.Many2one('progressive.claim', string='Progressive Claim Option')
    progressive_claim_subcon_option = fields.Many2one('progressive.claim', string='Progressive Claim Option')

    def action_print_report(self):
        progressive_claim_customer = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('progressive_bill', '=', False)])
        progressive_claim_subcon = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('progressive_bill', '=', True)])

        if self.print_type == 'all':
            if len(progressive_claim_customer) == 0 and len(progressive_claim_subcon) == 0:
                raise ValidationError(_('No Progressive Claim found for this Project'))

            elif len(progressive_claim_customer) > 0 and len(progressive_claim_subcon) > 0:
                return self.env.ref('equip3_construction_accounting_operation.action_report_construction_progressive').report_action(progressive_claim_customer+progressive_claim_subcon)

            elif len(progressive_claim_customer) > 0 and len(progressive_claim_subcon) == 0:
                return self.env.ref('equip3_construction_accounting_operation.action_report_construction_progressive').report_action(progressive_claim_customer)

            elif len(progressive_claim_customer) == 0 and len(progressive_claim_subcon) > 0:
                return self.env.ref('equip3_construction_accounting_operation.action_report_construction_progressive').report_action(progressive_claim_subcon)

        elif self.print_type == 'customer':
            if len(progressive_claim_customer) == 0:
                raise ValidationError(_('No Progressive Claim (Customer) found for this Project'))
            else:
                if self.specific_print_type == 'all':
                    return self.env.ref('equip3_construction_accounting_operation.action_report_construction_progressive').report_action(progressive_claim_customer)
                elif self.specific_print_type == 'progressive':
                    selected_data = None
                    for claim in progressive_claim_customer:
                        if claim.id == self.progressive_claim_customer_option.id:
                            selected_data = claim
                    return self.env.ref('equip3_construction_accounting_operation.action_report_construction_progressive').report_action(selected_data)
                    
        elif self.print_type == 'vendor':
            if len(progressive_claim_subcon) == 0:
                raise ValidationError(_('No Progressive Claim (Vendor) found for this Project'))
            else:
                if self.specific_print_type == 'all':
                    return self.env.ref('equip3_construction_accounting_operation.action_report_construction_progressive').report_action(progressive_claim_subcon)
                elif self.specific_print_type == 'progressive':
                    selected_data = None
                    for claim in progressive_claim_subcon:
                        if claim.id == self.progressive_claim_subcon_option.id:
                            selected_data = claim
                    return self.env.ref('equip3_construction_accounting_operation.action_report_construction_progressive').report_action(selected_data)

