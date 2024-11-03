from odoo import models, fields, api, _

class facilitiesarea(models.Model):
    _name = 'maintenance.assignation.type'
    _description = 'Modul Assignation Type'

    name = fields.Char("Maintenance Assignation Type", required=True, translate=True)
    active = fields.Boolean("Active Assignation Type", required=True, default=True)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Assignation Type'),
            'template': '/equip3_asset_fms_masterdata/static/xls/assignation_type_template.xls'
        }]