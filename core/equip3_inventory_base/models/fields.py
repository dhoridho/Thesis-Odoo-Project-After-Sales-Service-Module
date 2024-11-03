from odoo import models
from odoo.fields import Float


class ProductStandardPrice(Float):

    warehouse_context = 'price_for_warehouse'

    def setup_full(self, model):
        if model._name != 'product.product':
            raise NotImplementedError('ProductStandardPrice only allowed for `product.product` model!')
        return super(ProductStandardPrice, self).setup_full(model)

    def _warehouse_id(self, env):
        is_cost_per_warehouse = eval(env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        if not is_cost_per_warehouse:
            return False
        warehouse_id = env.context.get(self.warehouse_context, False)
        if isinstance(warehouse_id, models.BaseModel):
            warehouse_id = warehouse_id.id
        return warehouse_id

    def _default_warehouse_dependent(self, model):
        warehouse_id = self._warehouse_id(model.env)
        if not warehouse_id:
            return self._default_warehouse_dependent(model)
        return 0.0

    def _compute_warehouse_dependent(self, records):
        warehouse_id = self._warehouse_id(records.env)
        if not warehouse_id:
            return self._compute_company_dependent(records)
        
        # read price as superuser, as the current user may not have access
        prices = records.env['product.warehouse.price'].sudo().search([
            ('company_id', '=', records.env.company.id),
            ('warehouse_id', '=', warehouse_id),
            ('product_id', 'in', records.ids)
        ])
        prices_values = {price.product_id.id: price.standard_price for price in prices}
        for record in records:
            record[self.name] = prices_values.get(record.id)

    def _inverse_warehouse_dependent(self, records):
        warehouse_id = self._warehouse_id(records.env)
        if not warehouse_id:
            return self._inverse_company_dependent(records)
        
        values = {
            record.id: self.convert_to_write(record[self.name], record)
            for record in records
        }

        # update price as superuser, as the current user may not have access
        for record in records:
            record._price_line(warehouse_id).standard_price = values[record.id]

    def _search_warehouse_dependent(self, records, operator, value):
        warehouse_id = self._warehouse_id(records.env)
        if not warehouse_id:
            return self._search_warehouse_dependent(records, operator, value)
        
        product_ids = records.env['product.warehouse.price'].search([
            ('company_id', '=', records.env.company.id),
            ('warehouse_id', '=', warehouse_id),
            ('standard_price', operator, value)
        ]).mapped('product_id')
        return [('id', 'in', product_ids)]

    def _get_attrs(self, model, name):
        attrs = super(ProductStandardPrice, self)._get_attrs(model, name)
        attrs['default'] = attrs.get('default', self._default_warehouse_dependent)
        attrs['compute'] = self._compute_warehouse_dependent
        if not attrs.get('readonly'):
            attrs['inverse'] = self._inverse_warehouse_dependent
        attrs['search'] = self._search_warehouse_dependent
        attrs['_depends_context'] = attrs.get('_depends_context', ()) + (self.warehouse_context, )
        return attrs
