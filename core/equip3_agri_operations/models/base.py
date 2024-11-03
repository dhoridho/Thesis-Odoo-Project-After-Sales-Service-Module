from odoo import models, api, _


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _search_panel_domain_image(self, field_name, domain, set_count=False, limit=False):
        field = self._fields[field_name]
        exception1 = self._name == 'agriculture.daily.activity' and field.type == 'many2many' and field_name == 'crop_ids'
        exception2 = self._name == 'agriculture.daily.activity.line' and field.type == 'many2many' and field_name == 'worker_group_ids'
        exception3 = self._name == 'agriculture.daily.activity.record' and field.type == 'many2many' and field_name in ('crop_ids', 'material_ids', 'asset_ids')

        if any([exception1, exception2, exception3]):
            record_ids = self.search(domain)
            domain_image = {}
            for record in record_ids:
                for record_field in record[field_name]:
                    domain_image[record_field.id] = {
                        'id': record_field.id, 
                        'display_name': record_field.display_name
                    }
            return domain_image
        return super(Base, self)._search_panel_domain_image(field_name, domain, set_count=set_count, limit=limit)
