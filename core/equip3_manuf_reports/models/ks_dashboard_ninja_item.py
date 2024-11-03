from odoo import models, fields, api
import json


class KsDashboardNinjaItem(models.Model):
    _inherit = 'ks_dashboard_ninja.item'

    def unlink(self):
        for record in self:
            if record.ks_custom_label_ids:
                record.ks_custom_label_ids.unlink()
        return super(KsDashboardNinjaItem, self).unlink()

    ks_use_custom_label = fields.Boolean(string='Use Custom Label')
    ks_custom_label_ids = fields.Many2many('ks.dashboard.ninja.custom.label', string='Custom Labels')

    @api.model
    def _ks_get_chart_data(self, domain=[]):
        result = super(KsDashboardNinjaItem, self)._ks_get_chart_data(domain=domain)
        if not result or not isinstance(result, str) or not self.ks_use_custom_label:
            return result
        try:
            data = json.loads(result)
            if 'datasets' in data:
                for i, (d, field) in enumerate(zip(data['datasets'], self.ks_chart_measure_field)):
                    label = self.ks_custom_label_ids.filtered(lambda l: l.field_id == field)
                    if 'label' not in d or not label:
                        continue
                    data['datasets'][i]['label'] = label.label
            return json.dumps(data)
        except Exception as e:
            return result

    @api.onchange('ks_dashboard_item_type')
    def _onchange_ks_dashboard_item_type_manuf(self):
        if self.ks_dashboard_item_type != 'ks_line_chart':
            self.ks_use_custom_label = False

    @api.onchange('ks_use_custom_label')
    def _onchange_use_custom_label_manuf(self):
        label_ids = [(5,)]
        if self.ks_use_custom_label:
            label_ids += [
                (0, 0, {'field_id': field.id or field._origin.id, 'label': field.field_description})
                for field in self.ks_chart_measure_field
            ]
        self.ks_custom_label_ids = label_ids

    @api.onchange('ks_chart_measure_field')
    def _onchange_ks_chart_measure_field_manuf(self):
        label_ids = [(5,)]
        if self.ks_use_custom_label:
            label_ids += [
                (0, 0, {'field_id': field.id or field._origin.id, 'label': field.field_description})
                for field in self.ks_chart_measure_field
            ]
        self.ks_custom_label_ids = label_ids


class KsDashboardNinjaCustomLabels(models.Model):
    _name = 'ks.dashboard.ninja.custom.label'
    _description = 'KS Dashboard Ninja Custom Labels'

    field_id = fields.Many2one('ir.model.fields', string='Field')
    label = fields.Char(string='Label')

    @api.onchange('field_id')
    def _onchange_field_id(self):
        if self.field_id:
            self.label = self.field_id.field_description
