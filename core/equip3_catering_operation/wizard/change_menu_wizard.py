from odoo import api, fields, models


class ChangeMenuWizard(models.TransientModel):
    _name = 'change.menu.wizard'
    _description = 'Change Menu Wizard'

    customer_mpl_id = fields.Many2one(comodel_name='customer.line', string='Customer Line', required=True)
    line_ids = fields.One2many('change.menu.line.wizard', 'change_menu_wiz_id', string='Products')
    remark = fields.Char(string='Remark', required=True)
    
    def action_change_menu(self):
        picking = self.customer_mpl_id.picking_id
        scheduled_date = picking.scheduled_date
        if picking.state == 'draft':
            picking_lines = []
            for menu_line in self.line_ids:
                vals_line = {
                    'product_id':menu_line.menu_id.id,
                    'name':menu_line.desc,
                    'product_uom_qty':menu_line.quantity,
                    'product_uom':menu_line.uom_id.id,
                    'location_id':picking.location_id.id,
                    'location_dest_id':picking.location_dest_id.id,
                }
                picking_lines.append((0,0,vals_line))
            if picking.move_ids_without_package:
                picking.move_ids_without_package.unlink()
            picking.write({
                'scheduled_date':scheduled_date,
                'move_ids_without_package' : picking_lines
                })
            self.customer_mpl_id.remark = self.remark

    @api.model
    def default_get(self, fields):
        res = super(ChangeMenuWizard, self).default_get(fields)
        menu_rec = self.env['customer.line'].browse(self.env.context.get('active_id')).menu_planner_id
        line_ids = []
        for menu in menu_rec:
            for rec in menu.line_ids:
                line = (0, 0, {
                    'menu_id': rec.menu_id,
                    'desc': rec.desc,
                    'quantity': rec.quantity,
                    'uom_id': rec.uom_id
                })
                line_ids.append(line)
        res.update({
            'line_ids': line_ids
        })
        return res
            
class ChangeMenuLineWizard(models.TransientModel):
    _name = 'change.menu.line.wizard'
    _description = 'Change Menu Line Wizard'

    change_menu_wiz_id = fields.Many2one(comodel_name='change.menu.wizard', string='Wizard', required=True)
    menu_id = fields.Many2one("product.product", string="Menu", domain="[('catering_type','=','menu')]")
    desc = fields.Char("Description", related='menu_id.name')
    quantity = fields.Float("Quantity", default=1)
    uom_id = fields.Many2one("uom.uom", string="Unit Of Measure", related='menu_id.uom_id')