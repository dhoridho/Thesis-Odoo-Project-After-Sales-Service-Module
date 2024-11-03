# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    
    def button_validate(self):
        error_list = []
        if self.purchase_id and self.move_ids_without_package:
            for line in self.move_ids_without_package:
                product_limit = line.product_id.product_limit
                min_qty = line.product_id.min_val
                max_qty = line.product_id.max_val
                done = line.quantity_done
                demand = line.product_uom_qty
                if product_limit == 'no_limit':
                    continue
                elif product_limit and product_limit == 'str_rule':
                    if demand != done:
                        error_list.append('%s cannot be received lower or Greater than %s' % (str(line.product_id.name), demand))
                else:
                    if product_limit and product_limit in ('limit_per', 'limit_amount'):
                        if product_limit == 'limit_per':
                            val = (done / demand) * 100
                            if val < min_qty or val > max_qty:
                                error_list.append('%s cannot be received lower than %s or Greater than %s.'%(line.product_id.name, str(min_qty) + "%", str(max_qty) + "%"))
                        else:
                            if done < min_qty or done > max_qty:
                                error_list.append('%s cannot be received lower than %s or Greater than %s.'%(line.product_id.name, str(min_qty), str(max_qty)))
        if error_list and len(error_list) > 0:
            error = '\n'.join(error_list)
            raise ValidationError(error)
        res = super(StockPicking, self).button_validate()

        for record in self:
            for move in record.move_lines:
                if move.purchase_line_id:
                    move.purchase_line_id.write({'date_received': record.date_done})

        return res
