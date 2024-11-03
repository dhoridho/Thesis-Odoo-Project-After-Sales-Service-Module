from odoo import fields, models, api, _
from odoo.exceptions import UserError


class MrpSubcontractingWizard(models.TransientModel):
    _name = 'mrp.subcontracting.wizard'
    _description = 'Subcontracting Wizard'

    @api.depends('production_id', 'production_id.product_id', 'production_id.create_date', 'product_qty')
    def _compute_allowed_requisition_ids(self):
        requisitions = self.env['purchase.requisition'].search([])
        for record in self:
            product_qty = record.product_qty
            production_id = record.production_id

            req_ids = []
            for req in requisitions:
                if req.date_end < production_id.create_date:
                    continue
                total_remaining_qty = sum(req.line_ids.filtered(
                    lambda line: line.product_id == production_id.product_id
                ).mapped('qty_remaining'))
                if total_remaining_qty >= product_qty:
                    req_ids.append(req.id)
            
            record.allowed_requisition_ids = [(6, 0, req_ids)]

    production_id = fields.Many2one('mrp.production', string='Manufacturing order', required=True)
    origin = fields.Char(string='Origin', related='production_id.name')
    subcon_type = fields.Selection(
        string='Options',
        selection=[('purchase.request', 'Purchase Requests'), ('purchase.order', 'Request for Quotations')],
        default='purchase.order'
    )
    uom_id = fields.Many2one('uom.uom', string='UoM', related='production_id.product_uom_id')
    product_qty = fields.Float(string='To Subcontract', digits='Product Unit of Measure')
    allowed_requisition_ids = fields.One2many('purchase.requisition', compute=_compute_allowed_requisition_ids)
    requisition_id = fields.Many2one('purchase.requisition', string='Blanket Order', domain="[('id', 'in', allowed_requisition_ids)]")

    @api.constrains('product_qty')
    def _check_subcontract(self):
        for record in self:
            product_qty = record.product_qty
            production_qty = record.production_id.product_qty
            if product_qty > production_qty or product_qty <= 0:
                raise UserError(_('Quantity should be greater than 0.0 and less or equal than %s' % production_qty))

    def action_confirm(self):
        self.ensure_one()

        values = getattr(self, '_prepare_%s_vals' % self.subcon_type.replace('.', '_'))()

        res_id = self.env[self.subcon_type].search([
            ('is_a_subcontracting', '=', True),
            ('subcon_production_id', '=', self.production_id.id)
        ], limit=1).id

        if self.subcon_type == 'purchase.order':
            action = self.env['ir.actions.actions']._for_xml_id('equip3_purchase_operation.product_requests_for_quotation_services')
        else:
            action = self.env['ir.actions.actions']._for_xml_id('equip3_purchase_operation.product_purchase_requests_services')
        context = dict(eval(action.get('context', '').strip() or '{}', self._context))

        if not res_id:
            res = self.env[self.subcon_type].with_context(context).create(values)
            res_id = res.id

        if self.requisition_id:
            values = self._prepare_purchase_requisition_vals(res_id)
            self.requisition_id.write(values)

        self.production_id.write({'is_subcontracted': True})
        action['view_mode'] = 'tree,form'
        action['views'] = [[False, 'form']]
        action['res_id'] = res_id
        return action

    def _prepare_subcon_vals(self):
        self.ensure_one()
        values = {
            'origin': self.origin,
            'is_a_subcontracting': True,
            'subcon_production_id': self.production_id.id,
            'subcon_uom_id': self.uom_id.id,
            'subcon_product_qty': self.product_qty,
        }
        return values

    def _prepare_purchase_request_vals(self):
        self.ensure_one()

        picking_type_id = self.env.ref('stock.picking_type_in').id
        company_id = self.production_id.company_id
        branch_id = self.production_id.branch_id

        values = {
            'picking_type_id': picking_type_id,
            'company_id': company_id.id,
            'branch_id': branch_id.id,
            'is_readonly_origin': True,
            'request_date': fields.Datetime.now(),
            'is_goods_orders': False,
            'subcon_requisition_id': self.requisition_id.id,
            'destination_warehouse': self.production_id.location_dest_id.get_warehouse().id,
            'is_services_orders': True,
            'is_single_request_date': True,
            'is_single_delivery_destination': True,
            'line_ids': [(0, 0, {
                'product_id': self.production_id.bom_id.subcontracting_product_id.id,
                'product_uom_id':  self.production_id.bom_id.subcontracting_product_id.uom_id.id,
                'name':  self.production_id.bom_id.subcontracting_product_id.display_name,
                'product_qty': 1.0,
                'analytic_account_group_ids': [(6, 0, self.production_id.analytic_tag_ids.ids)]
            })]
        }
        values.update(self._prepare_subcon_vals())
        return values

    def _prepare_purchase_order_vals(self):
        self.ensure_one()

        production_id = self.production_id
        picking_type_id = self.env.ref('stock.picking_type_in')
        company_id = production_id.company_id
        branch_id = self.production_id.branch_id

        partner_id = self.env['res.partner']
        if production_id.bom_id.subcontractor_ids:
            partner_id = production_id.bom_id.subcontractor_ids[0]

        now = fields.Datetime.now()

        values = {
            'partner_id': partner_id.id,
            'picking_type_id': picking_type_id.id,
            'company_id': company_id.id,
            'branch_id': branch_id.id,
            'date_planned': now,
            'state': 'draft',
            'requisition_id': self.requisition_id.id,
            'analytic_account_group_ids': [(6, 0, production_id.analytic_tag_ids.ids)],
            'discount_type': 'global',
            'is_service': True,
            'is_services_orders': True,
            'is_delivery_receipt': True,
            'is_single_delivery_destination': True,
            'destination_warehouse_id': production_id.location_dest_id.get_warehouse().id,
            'order_line': [(0, 0, {
                'product_id': production_id.bom_id.subcontracting_product_id.id,
                'product_uom': production_id.bom_id.subcontracting_product_id.uom_id.id,
                'name': production_id.bom_id.subcontracting_product_id.display_name,
                'product_qty': 1.0,
                'date_planned': now,
                'taxes_id': [(6, 0, production_id.bom_id.subcontracting_product_id.taxes_id.ids)],
                'discount_method': 'fix',
                'analytic_tag_ids': [(6, 0, production_id.analytic_tag_ids.ids)]
            })]
        }
        values.update(self._prepare_subcon_vals())
        return values

    def _prepare_purchase_requisition_vals(self, purchase_id):
        self.ensure_one()

        production_id = self.production_id
        line_ids = self.requisition_id.line_ids.filtered(
            lambda l: l.product_id == production_id.product_id)

        values = {
            'line_ids': [(1, line.id, {
                'bom_id': production_id.bom_id.id,
                'wizard_qty': line.qty_remaining
            }) for line in line_ids]
        }

        if self.subcon_type == 'purchase.order':
            values.update({'purchase_id': purchase_id})

        values.update(self._prepare_subcon_vals())
        return values
