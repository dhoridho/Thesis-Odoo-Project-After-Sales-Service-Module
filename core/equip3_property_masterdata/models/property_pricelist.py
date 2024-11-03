from odoo import api, fields, models


class PropertyPricelist(models.Model):
    _name = 'property.pricelist'
    _description = 'Property Pricelist'

    name = fields.Char(string='Name', required=True)
    daily_price = fields.Float(string='Daily Price', required=True)
    monthly_price = fields.Float(string='Monthly Price', required=True)
    yearly_price = fields.Float(string='Yearly Price', required=True)

    def write(self, vals):
        property_ids = self.env['product.product'].search([('property_pricelist_id', '=', int(self.id))])
        # update new price for every property that use this current pricelist
        if property_ids:
            update_price = {}
            if 'daily_price' in vals:
                update_price['daily_rent'] = vals['daily_price']
            if 'monthly_price' in vals:
                update_price['deposite'] = vals['monthly_price']
            if 'yearly_price' in vals:
                update_price['rent_price'] = vals['yearly_price']
            property_ids.write(update_price)

        return super(PropertyPricelist, self).write(vals)
