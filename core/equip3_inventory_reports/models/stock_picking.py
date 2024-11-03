from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    fulfillment = fields.Float(string="Fulfillment (%)", compute='_calculate_fulfillment', store=True)
    operation_warehouse_id = fields.Many2one(related='picking_type_id.warehouse_id', store=True, string='Operation Warehouse')
    move_line_ids_without_package = fields.One2many('stock.move.line', 'picking_id', 'Operations without package', domain=['|',('package_level_id', '=', False), ('picking_type_entire_packs', '=', False)])
    # move_ids_without_package_new = fields.One2many('stock.move', 'picking_id', string="Stock moves not in package")

    def action_confirm(self):
        for rec in self:
            if rec.mr_id:
                rec.mr_id._check_processed_record(rec.mr_id.id, rec.id)
        return super(stock_picking, self).action_confirm()

    def action_assign(self):
        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.mapped('move_ids_without_package').filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))
        # if moves and self.filtered(lambda picking: picking.state in ('confirmed','waiting')):
        #     print('dlwapodloawkdoaw')
        #     moves.write({'reserved_by_id': self.env.user.id, 'is_reserved': True})
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        moves._action_assign()
        move_line_list = []

        sort_quants_by = self.env['ir.config_parameter'].sudo().get_param('sort_quants_by') or False
        routing_order = self.env['ir.config_parameter'].sudo().get_param('routing_order') or False
        # print('ro', routing_order)
        # location_dup = []
        if sort_quants_by == 'location_name':
            location_name_list = []
            for line in self.move_line_ids_without_package:
                # if line.location_id.display_name not in location_dup:
                #     data = {'name': line.location_id.display_name}
                    location_name_list.append(line.location_id.display_name)
            # print('ln', location_name_list)
            if routing_order == "ascending":
                location_name_list_sorted = sorted(location_name_list)
                # print('ln_sorted', location_name_list_sorted)
            elif routing_order == 'descending':
                location_name_list_sorted = sorted(location_name_list, reverse=True)
                # print('ln_sorted', location_name_list_sorted)
            priority = 1
            for name in location_name_list_sorted:
                for line in self.move_line_ids_without_package.sorted(key=lambda r: r.id):
                    domain = ['&', '|',('is_customer', '=', self.partner_id.id),
                            ('category_ids', '=', line.product_id.categ_id.id),
                            ('product_ids', '=',  line.product_id.id)]
                    stock_life = self.env['stock.life'].search(domain)
                    if name == line.location_id.display_name and not stock_life:
                        line.move_line_sequence = priority
                        priority += 1
                    else:
                        line.move_line_sequence = priority
                        priority += 1


            # print(cccc)
        else:
            location_priority_list = []
            location_dup = []
            for line in self.move_line_ids_without_package:
                if line.location_id.display_name not in location_dup:
                    data = {'name': line.location_id.display_name, 'priority': line.location_id.removal_priority}
                    location_priority_list.append(data)
                    location_dup.append(line.location_id.display_name)
            location_priority_list = sorted(location_priority_list, key=lambda i:  i['priority'])
            priority = 1
            for prior in location_priority_list:
                for line in self.move_line_ids_without_package.sorted(key=lambda r: r.id):
                    domain = ['&', '|',('is_customer', '=', self.partner_id.id),
                            ('category_ids', '=', line.product_id.categ_id.id),
                            ('product_ids', '=',  line.product_id.id)]
                    stock_life = self.env['stock.life'].search(domain)
                    if prior['name'] == line.location_id.display_name and not stock_life:
                        line.move_line_sequence = priority
                        priority += 1
                    else:
                        line.move_line_sequence = priority
                        priority += 1

        for rec in self:
            if rec.sale_id:
                stock_picking = self.env['stock.picking'].search([('sale_id', '=', rec.sale_id.id)], order='id asc')
                if stock_picking and rec.id != stock_picking[0].id:
                    picking_id_first = self.env['stock.picking'].search([('sale_id', '=', rec.sale_id.id), ('state', '!=', 'done'), ('name', 'ilike', '%PICK%')])
                    if picking_id_first and rec.id != picking_id_first[0].id:
                        raise ValidationError(_('You can only process the Document after %s operation done', picking_id_first.name))

                    packing_id_second = self.env['stock.picking'].search([('sale_id', '=', rec.sale_id.id), ('state', '!=', 'done'), ('name', 'ilike', '%PACK%')])
                    if packing_id_second and rec.id != packing_id_second[0].id:
                        raise ValidationError(_('You can only process the Document after %s operation done', packing_id_second.name))




        return True

    def button_validate(self):
        res = super(stock_picking, self).button_validate()
        context = dict(self.env.context) or {}
        sort_quants_by = self.env['ir.config_parameter'].sudo().get_param('sort_quants_by') or False
        routing_order = self.env['ir.config_parameter'].sudo().get_param('routing_order') or False
        # print('ro', routing_order)
        # location_dup = []
        if context.get('picking_type_code') != 'incoming':
            if sort_quants_by == 'location_name':
                location_name_list = []
                for line in self.move_line_ids_without_package:
                    location_name_list.append(line.location_id.display_name)
                # print('ln', location_name_list)
                if routing_order == "ascending":
                    # print('aesc')
                    location_name_list_sorted = sorted(location_name_list)
                    # print('ln_sorted', location_name_list_sorted)
                elif routing_order == 'descending':
                    # print('desc')
                    location_name_list_sorted = sorted(location_name_list, reverse=True)
                    # print('ln_sorted', location_name_list_sorted)
                priority = 1
                for name in location_name_list_sorted:
                    for line in self.move_line_ids_without_package:
                        if name == line.location_id.display_name:
                            line.move_line_sequence = priority
                            priority += 1

            else:
                location_priority_list = []
                location_dup = []
                for line in self.move_line_ids_without_package:
                    if line.location_id.display_name not in location_dup:
                        data = {'name': line.location_id.display_name, 'priority': line.location_id.removal_priority}
                        location_priority_list.append(data)
                        location_dup.append(line.location_id.display_name)
                location_priority_list = sorted(location_priority_list, key=lambda i:  i['priority'])
                priority = 1
                for prior in location_priority_list:
                    for line in self.move_line_ids_without_package:
                        if prior['name'] == line.location_id.display_name:
                            line.move_line_sequence = priority
                            priority += 1

            for rec in self:
                if rec.state=='done':
                    temp_ids = []
                    for line in rec.move_ids_without_package:
                        if line.state != 'cancel':
                            temp_ids.append(line.id)
                    # rec.move_ids_without_package_new = [(6,0,temp_ids)]
        return res

    @api.model
    def action_internal_transfer_menu(self):
        res = super(stock_picking, self).action_internal_transfer_menu()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        internal_type = IrConfigParam.get_param('internal_type', "with_transit")
        if internal_type == 'with_transit':
            self.env.ref('equip3_inventory_reports.menu_inventory_in_transit').active = True
        else:
            self.env.ref('equip3_inventory_reports.menu_inventory_in_transit').active = False
        return res

    @api.depends('move_ids_without_package', 'move_ids_without_package.fulfillment')
    def _calculate_fulfillment(self):
        for record in self:
            record.fulfillment = 0
            if record.move_ids_without_package:
                record.fulfillment = sum(record.move_ids_without_package.mapped('fulfillment'))/len(record.move_ids_without_package)


# class StockImmediateTransfer(models.TransientModel):
#     _inherit = 'stock.immediate.transfer'

#     def process(self):
#         res = super(StockImmediateTransfer, self).process()
#         for picking in self.pick_ids:
#             # print('zzzzz', klla)
#             sort_quants_by = self.env['ir.config_parameter'].sudo().get_param('sort_quants_by') or False
#             routing_order = self.env['ir.config_parameter'].sudo().get_param('routing_order') or False
#             if sort_quants_by == 'location_name':
#                 location_name_list = []
#                 for line in picking.move_line_ids_without_package:
#                     location_name_list.append(line.location_id.display_name)
#                 # print('ln', location_name_list)
#                 if routing_order == "ascending":
#                     # print('aesc')
#                     location_name_list_sorted = sorted(location_name_list)
#                     # print('ln_sorted', location_name_list_sorted)
#                 elif routing_order == 'descending':
#                     # print('desc')
#                     location_name_list_sorted = sorted(location_name_list, reverse=True)
#                     # print('ln_sorted', location_name_list_sorted)
#                 priority = 1
#                 for name in location_name_list_sorted:
#                     for line in picking.move_line_ids_without_package:
#                         if name == line.location_id.display_name:
#                             line.move_line_sequence = priority
#                             priority += 1
#             else:
#                 location_priority_list = []
#                 location_dup = []
#                 for line in picking.move_line_ids_without_package:
#                     if line.location_id.display_name not in location_dup:
#                         data = {'name': line.location_id.display_name, 'priority': line.location_id.removal_priority}
#                         location_priority_list.append(data)
#                         location_dup.append(line.location_id.display_name)
#                     # print('line', line)
#                     # self.write({'move_line_ids_without_package': [(2,line.id)]})
#                 # print('ld', location_dup)
#                 # print('lpl', location_priority_list)
#                 location_priority_list = sorted(location_priority_list, key=lambda i:  i['priority'])
#                 # print('lpl_sorted', location_priority_list)
#                 move_lines_desc = picking.move_line_ids_without_package.search([('reference', '=', picking.name)], order='product_uom_qty desc')
#                 # for line in move_lines_desc:
#                     # print('reserve_qty', line.product_uom_qty)
#                 priority = 1
#                 for prior in location_priority_list:
#                     for line in picking.move_line_ids_without_package:
#                         if prior['name'] == line.location_id.display_name:
#                             line.move_line_sequence = priority
#                             priority += 1
#         return res


    def do_print_picking(self):
        if self.picking_type_code in ('outgoing', 'incoming'):
            return self.env.ref('stock.action_report_delivery').report_action(self)
        else:
            return super(stock_picking, self).do_print_picking()
