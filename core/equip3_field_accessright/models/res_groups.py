from odoo import models, fields, api


class ResGroups(models.Model):
    _inherit = 'res.groups'

    field_access = fields.Many2many('ir.model.fields', 'ir_model_fields_group_rel', 'group_id', 'field_id')
    external_or_id = fields.Char(compute='_compute_external_or_id')

    def _compute_external_or_id(self):
        query = """
            SELECT
                name,
                module,
                res_id
            FROM 
                ir_model_data
            WHERE
                model = 'res.groups' AND res_id in %s
        """
        cr = self.env.cr
        cr.execute(query, [tuple(self.ids)])
        xml_ids = {group_id: '.'.join([module, name]) for name, module, group_id in cr.fetchall()}
        for record in self:
            record.external_or_id = xml_ids.get(record.id, str(record.id))

    @api.model
    def create(self, vals):
        groups = super(ResGroups, self).create(vals)
        groups.mapped('field_access')._update_field_groups(force=True)
        return groups

    def write(self, vals):
        field_access_before = self.field_access # before write
        res = super(ResGroups, self).write(vals)
        if vals.get('field_access', False):
            (field_access_before | self.field_access)._update_field_groups(force=True)
        return res

    def unlink(self):
        field_access = self.mapped('field_access')
        res = super(ResGroups, self).unlink()
        field_access._update_field_groups(force=True)
        return res
