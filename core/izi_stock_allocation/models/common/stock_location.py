from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = 'stock.location'

    def get_all_location_ids(self, location_ids, location_str_ids):
        self.ensure_one()
        location_ids.append(self.id)
        location_str_ids.append(str(self.id))
        for child_location in self.child_ids:
            location_ids, location_str_ids = child_location.get_all_location_ids(location_ids, location_str_ids)
        return location_ids, location_str_ids

    def get_warehouse(self):
        self.ensure_one()
        # warehouse = False
        warehouse = self.env['stock.warehouse'].search([('view_location_id', '=', self.id)], limit=1)
        if self.usage == 'view':
            # warehouse = self.env['stock.warehouse'].search([('view_location_id', '=', self.id)], limit=1)
            if warehouse:
                return warehouse
            elif self.location_id:
                warehouse = self.location_id.get_warehouse()
        elif self.location_id:
            warehouse = self.location_id.get_warehouse()
        return warehouse
