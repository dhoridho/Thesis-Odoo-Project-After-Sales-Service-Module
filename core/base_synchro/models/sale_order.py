from odoo import api, fields, models, _

    
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    base_sync = fields.Boolean('Base Sync', default=False)

    def genreate_sequence(self):
        so_lines = self.env['sale.order'].search([
            ('base_sync', '=', True),
            ('id', 'in', self.ids)
        ])
        for so_line in so_lines:
            if so_line.base_sync:
                IrConfigParam = self.env['ir.config_parameter'].sudo()
                keep_name_so = IrConfigParam.get_param('keep_name_so', False)
                if keep_name_so:
                    so_line.name = self.env['ir.sequence'].next_by_code('sale.order.quotation.order')
                else:
                    so_line.name = self.env['ir.sequence'].next_by_code('sale.order.quotation')
                so_line.base_sync = False
        result =    {
                        'name': 'Sales Order Resequence',
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'sale.order',
                        'type': 'ir.actions.act_window',
                        'domain': [('id', 'in', so_lines.ids)],
                        'target': 'current',
                    }
        return result