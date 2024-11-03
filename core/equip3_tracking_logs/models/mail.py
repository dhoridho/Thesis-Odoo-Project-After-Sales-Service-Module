from odoo import SUPERUSER_ID, _, api, fields, models,tools

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @tools.ormcache('self.env.uid', 'self.env.su')
    def _get_tracked_fields(self):
        """ Return the set of tracked fields names for the current model. """
        field_obj = self.env['ir.model.fields']
        domain = [('model_id.model','=',self._name)]
        domain += ['|',('tracking','>',0),('is_manual_tracking','!=',False)]
        fields_rec = field_obj.search_read(domain, fields=['name'])
        fields_tracked = []
        if fields_rec:
          fields_tracked =  [item['name'] for item in fields_rec]
        fields = {
            name
            for name, field in self._fields.items()
            if name in fields_tracked
        }
        return fields and set(self.fields_get(fields))

