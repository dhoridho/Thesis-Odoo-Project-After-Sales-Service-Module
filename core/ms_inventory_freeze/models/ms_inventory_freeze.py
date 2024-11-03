from odoo import fields, models, api, _
from odoo.exceptions import Warning

class StockLocation(models.Model):
    _inherit = 'stock.location'

    freeze_status = fields.Selection([
        ('full','Fully Freeze'),
        ('partial','Partially Freeze'),
    ], string='Freeze Status', copy=False)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_freeze = fields.Boolean(string='Is Freeze?', copy=False)

class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    def action_start(self):
        res = super(StockInventory, self).action_start()
        for inventory in self:
            location_ids = self.env['stock.location'].search([
                ('id','child_of',inventory.location_ids.ids)
            ])
            if not location_ids :
                location_ids = self.env['stock.location'].search([
                    ('usage', '=', 'internal')
                ])
            product_ids = inventory.product_ids
            if not product_ids :
                product_ids = self.env['product.product'].search([])
            product_ids.write({'is_freeze':True})
            if not inventory.product_ids :
                location_ids.write({'freeze_status':'full'})
            else :
                location_ids.write({'freeze_status':'partial'})
        return res
    prepare_inventory = action_start

    def set_freeze_false(self):
        for inventory in self:
            location_ids = self.env['stock.location'].search([
                ('id','child_of',inventory.location_ids.ids)
            ])
            if not location_ids :
                location_ids = self.env['stock.location'].search([
                    ('usage', '=', 'internal')
                ])
            location_ids.write({'freeze_status':False})
            product_ids = inventory.product_ids
            if not product_ids :
                product_ids = self.env['product.product'].search([])
            product_ids.write({'is_freeze':False})

    def action_cancel_draft(self):
        res = super(StockInventory, self).action_cancel_draft()
        self.set_freeze_false()
        return res

    def _action_done(self):
        res = super(StockInventory, self)._action_done()
        self.set_freeze_false()
        return res

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _action_done(self):
        for me_id in self :
            if not me_id.move_id.inventory_id :
                if me_id.location_id.freeze_status == 'full' :
                    raise Warning("Can't move product %s from location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done"%(me_id.product_id.display_name,me_id.location_id.display_name))
                elif me_id.location_dest_id.freeze_status == 'full' :
                    raise Warning("Can't move product %s to location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done"%(me_id.product_id.display_name,me_id.location_dest_id.display_name))
                elif me_id.location_id.freeze_status and me_id.product_id.is_freeze :
                    raise Warning("Can't move product %s from location %s, because the product and location is in freeze status. Stock move can be process after inventory adjustment done"%(me_id.product_id.display_name,me_id.location_id.display_name))
                elif me_id.location_dest_id.freeze_status and me_id.product_id.is_freeze :
                    raise Warning("Can't move product %s to location %s, because the product and location is in freeze status. Stock move can be process after inventory adjustment done"%(me_id.product_id.display_name,me_id.location_dest_id.display_name))
        return super(StockMoveLine, self)._action_done()
    