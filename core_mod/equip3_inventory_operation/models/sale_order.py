
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.tools import float_compare, float_round, float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        self.ensure_one()

        context = dict(self.env.context) or {}
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        product_service_operation_delivery = IrConfigParam.get_param(
            'is_product_service_operation_delivery', False)
        is_do_approval_matrix_on = eval(IrConfigParam.get_param('is_delivery_order_approval_matrix', 'False'))
        
        context.update(
            {'is_product_service_operation_delivery': product_service_operation_delivery,
             'picking_type_code': 'outgoing',
             'do_not_confirm_moves': is_do_approval_matrix_on})
        self = self.with_context(context)
        return super(SaleOrder, self)._action_confirm()

    def action_view_delivery(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id(
            "equip3_inventory_operation.action_delivery_order")

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + \
                    [(state, view)
                     for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        # Prepare the context.
        picking_id = pickings.filtered(
            lambda l: l.picking_type_id.code == 'outgoing')
        if picking_id:
            picking_id = picking_id[0]
        else:
            picking_id = pickings[0]
        # action['context'] = dict(self._context, default_partner_id=self.partner_id.id, default_picking_type_id=picking_id.picking_type_id.id, default_origin=self.name, default_group_id=picking_id.group_id.id)
        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_single_warehouse = fields.Boolean(
        string="Single Warehouse", default=True)
    line_warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    delivery_address_id = fields.Many2one(
        'res.partner', string="Delivery Address")
    multiple_do_date = fields.Datetime(string='Delivery Date', index=True)

    landed_cost = fields.Float('Landed Cost', readonly=True)

    # def _action_launch_stock_rule(self, previous_product_uom_qty=False):
    #     """
    #     Launch procurement group run method with required/custom fields genrated by a
    #     sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
    #     depending on the sale order line product rule.
    #     """
    #     precision = self.env['decimal.precision'].precision_get(
    #         'Product Unit of Measure')
    #     context = dict(self.env.context) or {}
    #     temp_list = []
    #     line_list_vals = []
    #     for record in self:
    #         delivery_address_id = record.delivery_address_id.id or record.order_id.partner_shipping_id.id
    #         if record.multiple_do_date:
    #             multiple_do_date = record.multiple_do_date.date()
    #         else:
    #             multiple_do_date = record.order_id.commitment_date or record.order_id.expected_date
    #             multiple_do_date = multiple_do_date.date()
    #         if not record.line_warehouse_id:
    #             if record.order_id.is_single_warehouse:
    #                 record.line_warehouse_id = record.order_id.warehouse_id
    #             else:
    #                 raise ValueError(
    #                     "Please select a warehouse for product: %s" % record.product_id.name)
    #         if {'line_warehouse_id': record.line_warehouse_id.id,
    #             'delivery_address_id': delivery_address_id,
    #             'delivery_date': multiple_do_date,
    #                 'product_id': record.product_id.id} in temp_list:
    #             filter_line = list(filter(lambda r: r.get('line_warehouse_id') == record.line_warehouse_id.id and
    #                                       r.get(
    #                                           'delivery_address_id') == delivery_address_id
    #                                       and r.get('delivery_date') == multiple_do_date and
    #                                       r.get('product_id') == record.product_id.id, line_list_vals))
    #             if filter_line:
    #                 filter_line[0]['lines'].append(record)
    #         else:
    #             temp_list.append({
    #                 'line_warehouse_id': record.line_warehouse_id.id,
    #                 'delivery_address_id': delivery_address_id,
    #                 'delivery_date': multiple_do_date,
    #                 'product_id': record.product_id.id
    #             })
    #             line_list_vals.append({
    #                 'line_warehouse_id': record.line_warehouse_id.id,
    #                 'delivery_address_id': delivery_address_id,
    #                 'delivery_date': multiple_do_date,
    #                 'lines': [record]
    #             })
    #     group_ids = []
    #     for value in line_list_vals:
    #         procurements = []
    #         group_id = False
    #         for line in value.get('lines'):
    #             qty = line._get_qty_procurement(previous_product_uom_qty)
    #             if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
    #                 continue
    #             group_id = line._get_procurement_group()
    #             if not group_id:
    #                 group_id = self.env['procurement.group'].create(
    #                     line._prepare_procurement_group_vals())
    #                 line.order_id.procurement_group_id = group_id
    #                 group_ids.append(group_id)
    #             else:
    #                 next = True
    #                 update_move = False
    #                 group_ids_new = group_ids
    #                 for group in group_ids_new:
    #                     if update_move:
    #                         break
    #                     for i in group.stock_move_ids:
    #                         if i.sale_line_id.line_warehouse_id == line.line_warehouse_id and i.sale_line_id.delivery_address_id == line.delivery_address_id and i.sale_line_id.multiple_do_date == line.multiple_do_date:
    #                             group_id = group
    #                             update_move = True
    #                             break
    #                         else:
    #                             group_id = self.env['procurement.group'].create(
    #                                 line._prepare_procurement_group_vals())
    #                             line.order_id.procurement_group_id = group_id
    #                             group_ids.append(group_id)
    #                             next = False
    #                 # In case the procurement group is already created and the order was
    #                 # cancelled, we need to update certain values of the group.
    #                 if next:
    #                     updated_vals = {}
    #                     if group_id.partner_id != line.order_id.partner_shipping_id:
    #                         updated_vals.update(
    #                             {'partner_id': line.order_id.partner_shipping_id.id})
    #                     if group_id.move_type != line.order_id.picking_policy:
    #                         updated_vals.update(
    #                             {'move_type': line.order_id.picking_policy})
    #                     if updated_vals:
    #                         group_id.write(updated_vals)

    #             values = line._prepare_procurement_values(group_id=group_id)
    #             values.update({
    #                 'line_warehouse_id': value.get('line_warehouse_id'),
    #                 'delivery_address_id': value.get('delivery_address_id'),
    #                 'delivery_date': value.get('delivery_date'),
    #                 'date_planned': value.get('delivery_date'),
    #                 'date_deadline': value.get('delivery_date'),
    #                 'multiple_do': True,
    #             })
    #             product_qty = line.product_uom_qty - qty

    #             line_uom = line.product_uom
    #             quant_uom = line.product_id.uom_id
    #             product_qty, procurement_uom = line_uom._adjust_uom_quantities(
    #                 product_qty, quant_uom)
    #             procurements.append(self.env['procurement.group'].Procurement(
    #                 line.product_id, product_qty, procurement_uom,
    #                 line.order_id.partner_shipping_id.property_stock_customer,
    #                 line.name, line.order_id.name, line.order_id.company_id, values))
    #         if procurements:
    #             self.env['procurement.group'].run(procurements)
    #     if context.get('is_product_service_operation_delivery'):
    #         procurements = []
    #         for line in self:
    #             line = line.with_company(line.company_id)
    #             if line.state != 'sale' or not line.product_id.type in ('service'):
    #                 if not line.product_id.is_product_service_operation_delivery:
    #                     continue
    #             qty = line._get_qty_procurement(previous_product_uom_qty)
    #             if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
    #                 continue

    #             group_id = line._get_procurement_group()
    #             if not group_id:
    #                 group_id = self.env['procurement.group'].create(
    #                     line._prepare_procurement_group_vals())
    #                 line.order_id.procurement_group_id = group_id
    #                 group_ids.append(group_id)
    #             else:
    #                 next = True
    #                 update_move = False
    #                 group_ids_new = group_ids
    #                 for group in group_ids_new:
    #                     if update_move:
    #                         break
    #                     for i in group.stock_move_ids:
    #                         if i.sale_line_id.line_warehouse_id == line.line_warehouse_id and i.sale_line_id.delivery_address_id == line.delivery_address_id and i.sale_line_id.multiple_do_date == line.multiple_do_date:
    #                             group_id = group
    #                             update_move = True
    #                             break
    #                         else:
    #                             group_id = self.env['procurement.group'].create(
    #                                 line._prepare_procurement_group_vals())
    #                             line.order_id.procurement_group_id = group_id
    #                             group_ids.append(group_id)
    #                             next = False
    #                 # In case the procurement group is already created and the order was
    #                 # cancelled, we need to update certain values of the group.
    #                 if next:
    #                     updated_vals = {}
    #                     if group_id.partner_id != line.order_id.partner_shipping_id:
    #                         updated_vals.update(
    #                             {'partner_id': line.order_id.partner_shipping_id.id})
    #                     if group_id.move_type != line.order_id.picking_policy:
    #                         updated_vals.update(
    #                             {'move_type': line.order_id.picking_policy})
    #                     if updated_vals:
    #                         group_id.write(updated_vals)

    #             values = line._prepare_procurement_values(group_id=group_id)
    #             product_qty = line.product_uom_qty - qty
    #             line_uom = line.product_uom
    #             quant_uom = line.product_id.uom_id
    #             product_qty, procurement_uom = line_uom._adjust_uom_quantities(
    #                 product_qty, quant_uom)
    #             procurements.append(self.env['procurement.group'].Procurement(
    #                 line.product_id, product_qty, procurement_uom,
    #                 line.order_id.partner_shipping_id.property_stock_customer,
    #                 line.name, line.order_id.name, line.order_id.company_id, values))
    #         if procurements:
    #             self.env['procurement.group'].run(procurements)
    #     picking_ids = []
    #     for group in group_ids:
    #         for move in group.stock_move_ids:
    #             if move.picking_id:
    #                 if move.picking_id.id not in picking_ids:
    #                     picking_ids.append(move.picking_id.id)
    #     if self:
    #         self[0].order_id.picking_ids = [(6, 0, picking_ids)]
    #     return True

    def _get_account_computed_account(self, move_id):
        self.ensure_one()
        if not self.product_id:
            return

        fiscal_position = move_id.fiscal_position_id
        accounts = self.product_id.product_tmpl_id.get_product_accounts(
            fiscal_pos=fiscal_position)
        if move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            return accounts['income']
        elif move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            return accounts['expense']

    @api.depends('move_ids', 'move_ids.stock_valuation_layer_ids', 'order_id.picking_ids.state', 'landed_cost')
    def _compute_purchase_price(self):
        res = super(SaleOrderLine, self)._compute_purchase_price()
        for line in self:
            if not line.move_ids:
                continue
            if line.product_id.categ_id.property_cost_method != 'standard':
                landed_cost = line.landed_cost
                if line.product_uom and line.product_uom != line.product_id.uom_id:
                    landed_cost = line.product_id.uom_id._compute_price(landed_cost, line.product_uom)
                line.purchase_price += line.landed_cost
        return res
