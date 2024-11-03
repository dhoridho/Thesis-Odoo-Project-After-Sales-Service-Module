from odoo import models, fields, api

class PropertyArchiveWizard(models.TransientModel):
    _name = 'property.archive.wizard'
    _description = 'Property Archive Wizard'


    def archive_contract_property(self):
        context = dict(self.env.context) or {}
        property_ids = self.env['product.product'].browse(context.get('active_ids'))
        agreement_ids = self.env['agreement'].search([('property_id', 'in', property_ids.ids)])

        property_ids.write({'active': False})
        if agreement_ids:
            agreement_ids.write({'active': False})


    def archive_property(self):
        context = dict(self.env.context) or {}
        property_ids = self.env['product.product'].browse(context.get('active_ids'))
        property_ids.write({'active': False})