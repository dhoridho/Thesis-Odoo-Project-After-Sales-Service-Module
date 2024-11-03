from odoo import api, fields, models, _


class WizardPurchaseAgreement(models.TransientModel):
    _name = "wizard.purchase.agreement"

    agreement_id = fields.Many2one('purchase.agreement', string="Tender")
    rfq_id = fields.Many2one('purchase.order', string="RFQ")
    partner_ids = fields.Many2many('res.partner','partner_agreement','agreementid','partnerid', string='Vendors', domain="[('supplier_rank','>', 0), ('is_vendor','=', True)]")
    temp_current_vendors = fields.Many2many('res.partner', string="Temp Current Vendors")
    split_table = fields.Selection([
        ('service', 'Service'),
        ('material', 'Material')
    ], string='Split Table', default='material')

    def _prepare_purchase_split_material(self, vals, material_lines):
        return {
            'project': vals.project.id,
            'cost_sheet': vals.cost_sheet.id,
            'project_budget': vals.project_budget.id,
            'branch_id': vals.branch_id.id,
            'analytic_account_group_ids': [(6, 0, vals.analytic_account_group_ids.ids)],
            'is_goods_orders': True,
            'material_order': True,
            'is_subcontracting': False,
            'is_material_orders': True,
            'partner_ids': self.partner_ids,
            'sh_source': vals.name,
            'destination_warehouse_id': vals.cost_sheet.warehouse_id.id,
            'sh_purchase_agreement_line_ids': material_lines
        }

    def _prepare_purchase_split_service(self, vals, material_lines):
        return {
            'project': vals.project.id,
            'cost_sheet': vals.cost_sheet.id,
            'project_budget': vals.project_budget.id,
            'branch_id': vals.branch_id.id,
            'analytic_account_group_ids': [(6, 0, vals.analytic_account_group_ids.ids)],
            'is_goods_orders': True,
            'material_order': True,
            'is_subcontracting': False,
            'is_material_orders': True,
            'partner_ids': self.temp_current_vendors,
            'sh_source': vals.name,
            'destination_warehouse_id': vals.cost_sheet.warehouse_id.id,
            'sh_purchase_agreement_line_ids': material_lines
        }
    
    def submit_split(self):
        vals = self.agreement_id
        material_lines = []
        if self.split_table != 'material':
            vals['partner_ids'] = self.partner_ids
        for rec in vals.material_line_ids:
            new_material_line = (0, 0, {
                                    'type' : 'split',
                                    'var_material_id' : rec.variable_material_id.id,
                                    'bd_subcon_id' : rec.bd_subcon_id.id or False,
                                    'cs_subcon_id' : rec.cs_subcon_id.id or False,
                                    'project_scope' : rec.project_scope.id,
                                    'section' : rec.section.id,
                                    'subcon' : rec.subcon.id,
                                    'variable' : rec.variable.id,
                                    'group_of_product' : rec.group_of_product.id,
                                    'sh_product_id' : rec.product.id,
                                    'sh_product_description': rec.description,
                                    'sh_qty': rec.quantity,
                                    'budget_quantity': rec.budget_quantity,
                                    'sh_product_uom_id': rec.uom.id,
                                    'dest_warehouse_id': vals.cost_sheet.warehouse_id.id,
                                    'analytic_tag_ids': [(6, 0, rec.analytic_tag_ids.ids)],
                                    'schedule_date': rec.schedule_date,
                                })
            material_lines.append(new_material_line)
        context = {
                'goods_order': 1, 
                'default_is_goods_orders': True,
                'default_is_material_orders': True,
                'material_order': True,
            }
        if self.split_table != 'material':
            pt_data = self._prepare_purchase_split_service(vals, material_lines)
        else:
            pt_data = self._prepare_purchase_split_material(vals, material_lines)
        PT = self.env['purchase.agreement'].with_context(context).create(pt_data)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Purchase Tender',
            'view_mode': 'form',
            'res_model': 'purchase.agreement',
            'target': 'current',
            'res_id' : PT.id,
            'context': context,
        }
