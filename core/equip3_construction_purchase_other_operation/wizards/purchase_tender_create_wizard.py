
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PurchaseTenderCreateWizard(models.TransientModel):
    _inherit = 'purchase.tender.create.wizard'

    project = fields.Many2one('project.project', 'Project')
    tender_name = fields.Char('Tender Name')

    @api.onchange('vendor_ids')
    def get_project(self):
        for res in self:
            purchase_request = self.env['purchase.request'].browse(self.env.context.get('active_id'))
            res.project = purchase_request.project.id
    
    def _send_lines(self, product_line_id):
        return{
            'cs_material_id' : product_line_id.cs_material_id.id,
            'cs_labour_id' : product_line_id.cs_labour_id.id,
            'cs_overhead_id' : product_line_id.cs_overhead_id.id,
            'cs_equipment_id' : product_line_id.cs_equipment_id.id,
            'bd_material_id' : product_line_id.bd_material_id.id,
            'bd_labour_id' : product_line_id.bd_labour_id.id,
            'bd_overhead_id' : product_line_id.bd_overhead_id.id,
            'bd_equipment_id' : product_line_id.bd_equipment_id.id,
            'type' :  product_line_id.type,
            'project_scope' : product_line_id.project_scope.id,
            'section' : product_line_id.section.id,
            'variable' : product_line_id.variable_ref.id,
            'group_of_product' : product_line_id.group_of_product.id,
            'sh_product_id' : product_line_id.product_id.id,
            'sh_product_description': product_line_id.product_description,
            'sh_qty' : product_line_id.tender_qty,
            'budget_quantity' : product_line_id.tender_qty,
            'request_line_id': product_line_id.pr_line_id.id,
            'sh_ordered_qty' : product_line_id.remaning_qty,
            'sh_product_uom_id': product_line_id.uom.id,
            'dest_warehouse_id': product_line_id.destination_warehouse.id,
            'analytic_tag_ids': product_line_id.analytics_tag_ids.ids,
            'schedule_date': product_line_id.schedule_date,
        }

    def _create_tender_vals(self):
        data = []
        context = dict(self.env.context) or {}
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        pr_qty_limit = IrConfigParam.get_param('pr_qty_limit', "no_limit")
        max_percentage = int(IrConfigParam.get_param('max_percentage', 0))
        purchase_request_id = False
        for record in self:
            for product_line_id in record.product_line_ids:
                if product_line_id.tender_qty <= 0:
                    continue
                purchase_request_id = product_line_id.pr_line_id.request_id
                if pr_qty_limit == 'percent':
                    percentage_qty = product_line_id.pr_line_id.product_qty + ((product_line_id.pr_line_id.product_qty * max_percentage) / 100)
                    calculate_qty = percentage_qty - (product_line_id.pr_line_id.purchased_qty + product_line_id.pr_line_id.tender_qty)
                    if product_line_id.tender_qty > calculate_qty:
                        raise UserError(_("Quantity to Tender for %s cannot request greater than %d") % (product_line_id.product_id.display_name, calculate_qty))
                elif pr_qty_limit == 'fix':
                    calculate_qty = product_line_id.pr_line_id.product_qty - (product_line_id.pr_line_id.purchased_qty + product_line_id.pr_line_id.tender_qty)
                    if product_line_id.tender_qty > calculate_qty:
                        raise UserError(_("Quantity to Tender for %s cannot request greater than %d") % (product_line_id.product_id.display_name, calculate_qty))
                product_line_id.pr_line_id.tender_qty += product_line_id.tender_qty
                data.append((0, 0, record._send_lines(product_line_id)))
        vals = {}
        if data:
            vals = {
                'partner_ids' : self.vendor_ids.ids,
                'sh_source': self.sh_source,
                'purchase_request_id': purchase_request_id.id,
                'sh_purchase_agreement_line_ids' : data,
                'is_orders' : True,
                'branch_id': purchase_request_id.branch_id.id,
                'tender_name': self.tender_name,
            }
            if purchase_request_id.project:
                vals.update({'project': purchase_request_id.project.id})
            if purchase_request_id.cost_sheet:
                vals.update({'cost_sheet': purchase_request_id.cost_sheet.id})
            if purchase_request_id.project_budget:
                vals.update({'project_budget': purchase_request_id.project_budget.id})
            if purchase_request_id.analytic_account_group_ids:
                vals.update(
                    {'analytic_account_group_ids': [(6, 0, purchase_request_id.analytic_account_group_ids.ids)]})
            if purchase_request_id.material_request:
                vals.update({'material_request': purchase_request_id.material_request.id})
            if purchase_request_id.is_subcontracting:
                vals.update({'is_subcontracting': purchase_request_id.is_subcontracting})
            if purchase_request_id.is_material_orders:
                vals.update({'is_material_orders': purchase_request_id.is_material_orders})
            if purchase_request_id.is_orders:
                vals.update({'is_orders': purchase_request_id.is_orders})
            if purchase_request_id.is_asset_cons_order:
                vals.update({'is_asset_cons_order': purchase_request_id.is_asset_cons_order})
        return vals


class PurchaseTenderCreateLinesWizard(models.TransientModel):
    _inherit = 'purchase.tender.create.lines.wizard'

    type = fields.Selection([('material','Material'),
                            ('labour','Labour'),
                            ('overhead','Overhead'),
                            ('equipment','Equipment')],
                            string = "Type")
    cs_material_id = fields.Many2one('material.material', 'CS Material ID')
    cs_labour_id = fields.Many2one('material.labour', 'CS Labour ID')
    cs_overhead_id = fields.Many2one('material.overhead', 'CS Overhead ID')
    cs_equipment_id = fields.Many2one('material.equipment', 'CS Equipment ID')
    bd_material_id = fields.Many2one('budget.material', 'BD Material ID')
    bd_labour_id = fields.Many2one('budget.labour', 'BD Labour ID')
    bd_overhead_id = fields.Many2one('budget.overhead', 'BD Overhead ID')
    bd_equipment_id = fields.Many2one('budget.equipment', 'BD equipment ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
