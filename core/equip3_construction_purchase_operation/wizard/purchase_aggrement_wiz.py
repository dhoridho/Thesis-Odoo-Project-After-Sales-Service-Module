from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError

class PurchaseAgreementWiz(models.TransientModel):
    _name = 'purchase.agreement.wiz'
    _description = 'Create Purchase Agreement Wizard'

    request_date = fields.Date(string="Request date", default=datetime.now())
    purchase_agreement_line = fields.One2many('purchase.agreement.line.wiz', 'purchase_agreement_id')

    @api.model
    def default_get(self, fields):
        Job_cost_sheet = self.env['job.cost.sheet'].browse(self.env.context.get('active_id'))
        res = super(PurchaseAgreementWiz, self).default_get(fields)
        for rec in Job_cost_sheet.material_subcon_ids:
            res['purchase_agreement_line'] = [(0, 0, {
                'cs_subcon_id': rec.id,
                'project_scope': rec.project_scope.id,
                'section': rec.section_name.id,
                'variable': rec.variable.id,
                'quantity': rec.product_qty,
                'uom': rec.uom_id.id,
            })]
        return res

    # def comute_line(self):
    #     Job_cost_sheet = self.env['job.cost.sheet'].browse(self.env.context.get('active_id'))
    #     vals = []
    #     for rec in Job_cost_sheet.material_subcon_ids:
    #         res = (0, 0, {
    #             'cs_subcon_id': rec.id,
    #             'project_scope': rec.project_scope.id,
    #             'section': rec.section_name.id,
    #             'variable': rec.variable.id,
    #             'quantity': rec.product_qty,
    #             'uom': rec.uom_id.id,
    #         })
    #     vals.append(res)
    #     self.purchase_agreement_line = vals

    def create_purchase_agreemnet_submit(self):
        Job_cost_sheet = self.env['job.cost.sheet'].browse(self.env.context.get('active_id'))
        for line in self.purchase_agreement_line:
            if line.quantity > line.budget_quantity:
                raise ValidationError(_("The quantity is over the remaining budget"))
            else:
                vals = {
                    'project': Job_cost_sheet.project_id.id,
                    'cost_sheet': Job_cost_sheet.id,
                    'analytic_account_group_ids': Job_cost_sheet.account_tag_ids.ids,
                    'request_date': self.request_date,
                    'is_subcontracting':True,
                    'variable_line_ids': [(0, 0, {
                        'project_scope': line.project_scope.id,
                        'section': line.section.id,
                        'variable': line.variable.id,
                        'quantity': line.quantity,
                        'uom': line.uom.id,
                    })]
                }
                self.env['purchase.request'].sudo().create(vals)


class PurchaseAgreementLine(models.TransientModel):
    _name = 'purchase.agreement.line.wiz'
    _description = 'Create Purchase Agreement Line wizard'

    purchase_agreement_id = fields.Many2one('purchase.agreement.wiz')
    #job_sheet_id = fields.Many2one('job.cost.sheet', string = 'Job Sheet')
    cs_subcon_id = fields.Many2one('material.subcon')
    project_scope = fields.Many2one('project.scope.line', string="Project scope")
    section = fields.Many2one('section.estimate', string="Section")
    variable = fields.Many2one('variable.template', string="Variable")
    quantity = fields.Float(string="Quantity")
    budget_quantity = fields.Float(string="Budget quantity", related='cs_subcon_id.budgeted_qty_left')
    uom = fields.Many2one('uom.uom', string="UoM")
