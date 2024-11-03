# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.izi_data.models.common.db_odoo.izi_data_source_db_odoo import IZIDataSourceDBOdoo


class IZIDataSourceDBOdoo(models.Model):
    _inherit = 'izi.data.source'

    type = fields.Selection(
        selection_add=[
            ('db_odoo', 'Database Hashmicro'),
        ])

    @api.model
    def create_source_db_odoo(self):
        if not self.search([('type', '=', 'db_odoo')], limit=1):
            data_source = self.create({
                'name': 'Hashmicro',
                'type': 'db_odoo'
            })
            data_source.get_source_tables()
        return True

    IZIDataSourceDBOdoo.create_source_db_odoo = create_source_db_odoo