from odoo import models


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        res = super(StockImmediateTransfer, self).process()
        for picking in self.pick_ids:
            # print('zzzzz', klla)
            sort_quants_by = self.env['ir.config_parameter'].sudo(
            ).get_param('sort_quants_by') or False
            routing_order = self.env['ir.config_parameter'].sudo(
            ).get_param('routing_order') or False
            if sort_quants_by == 'location_name':
                location_name_list = []
                for line in picking.move_line_ids_without_package:
                    location_name_list.append(line.location_id.display_name)
                # print('ln', location_name_list)
                if routing_order == "ascending":
                    # print('aesc')
                    location_name_list_sorted = sorted(location_name_list)
                    # print('ln_sorted', location_name_list_sorted)
                elif routing_order == 'descending':
                    # print('desc')
                    location_name_list_sorted = sorted(
                        location_name_list, reverse=True)
                    # print('ln_sorted', location_name_list_sorted)
                priority = 1
                for name in location_name_list_sorted:
                    for line in picking.move_line_ids_without_package:
                        if name == line.location_id.display_name:
                            line.move_line_sequence = priority
                            priority += 1
            else:
                location_priority_list = []
                location_dup = []
                for line in picking.move_line_ids_without_package:
                    if line.location_id.display_name not in location_dup:
                        data = {'name': line.location_id.display_name,
                                'priority': line.location_id.removal_priority}
                        location_priority_list.append(data)
                        location_dup.append(line.location_id.display_name)
                    # print('line', line)
                    # self.write({'move_line_ids_without_package': [(2,line.id)]})
                # print('ld', location_dup)
                # print('lpl', location_priority_list)
                location_priority_list = sorted(
                    location_priority_list, key=lambda i:  i['priority'])
                # print('lpl_sorted', location_priority_list)
                move_lines_desc = picking.move_line_ids_without_package.search(
                    [('reference', '=', picking.name)], order='product_uom_qty desc')
                # for line in move_lines_desc:
                # print('reserve_qty', line.product_uom_qty)
                priority = 1
                for prior in location_priority_list:
                    for line in picking.move_line_ids_without_package:
                        if prior['name'] == line.location_id.display_name:
                            line.move_line_sequence = priority
                            priority += 1
        return res
