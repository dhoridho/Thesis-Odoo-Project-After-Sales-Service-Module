#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ACSProduct(models.Model):
    _inherit = 'product.template'

    hospital_product_type = fields.Selection(selection_add=[('vaccination','Vaccination')])
    age_for_vaccine = fields.Char("Age for Vaccine")
    vaccine_dose_number = fields.Char("Dose Number")


class ACSPatient(models.Model):
    _inherit = 'hms.patient'

    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        for rec in self:
            rec.vaccination_count = len(rec.vaccination_ids)

    vaccination_ids = fields.One2many('acs.vaccination', 'patient_id', 'Vaccination')
    vaccination_count = fields.Integer(compute='_rec_count', string='# Vaccination')

    def action_view_vaccinations(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_vaccination.action_vaccination_vac")
        action['domain'] = [('id', 'in', self.vaccination_ids.ids)]
        action['context'] = {'default_patient_id': self.id}
        return action


class StockMove(models.Model):
    _inherit = "stock.move"

    vaccination_id = fields.Many2one('acs.vaccination', string="Vaccination", ondelete="restrict")
