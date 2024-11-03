#-*- coding: utf-8 -*-

from odoo import models, fields, api,_ 


class HmsHospitalization(models.Model):
    _inherit = 'acs.hospitalization'

    def get_round_count(self):
        for record in self:
            record.ward_round_count = len(record.ward_round_ids)

    ward_round_count = fields.Integer(compute='get_round_count', string='Ward Round Count')
    ward_round_ids = fields.One2many('acs.nurse.ward.round', 'hospitalization_id', string='Ward Rounds')

    def get_hospitalizaion_invoice_data(self):
        product_data = super(HmsHospitalization, self).get_hospitalizaion_invoice_data()
        if self.ward_round_ids:
            ward_data = {}
            for ward_round in self.ward_round_ids:
                if ward_round.nurse_id.ward_round_product_id:
                    if ward_round.nurse_id.ward_round_product_id in ward_data:
                        ward_data[ward_round.nurse_id.ward_round_product_id] += 1
                    else:
                        ward_data[ward_round.nurse_id.ward_round_product_id] = 1
            if ward_data:
                product_data.append({
                    'name': _("Nurse Ward Round Charges"),
                })
            for product in ward_data:
                product_data.append({
                    'product_id': product,
                    'quantity': ward_data[product],
                })
        return product_data

    def action_view_wardrounds(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_nursing.hms_ward_round_action")
        action['domain'] = [('hospitalization_id','=',self.id)]
        action['context'] = {'default_hospitalization_id': self.id, 'default_patient_id': self.patient_id.id, 'default_physician_id': self.physician_id.id}
        return action


class HospitalDepartment(models.Model):
    _inherit = 'hr.department'

    department_type = fields.Selection(selection_add=[('nurse', 'Nurse')])


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ward_round_product_id = fields.Many2one('product.product', domain=[('type','=','service')],
        string='Warround Service',  ondelete='cascade', help='Registration Product')


class AcsPatientEvaluation(models.Model):
    _inherit = 'acs.patient.evaluation'

    @api.model
    def create(self, vals):
        record = super(AcsPatientEvaluation, self).create(vals)
        if self.env.context.get('nurse_ward_round'):
            ward_round = self.env['acs.nurse.ward.round'].browse(self.env.context.get('nurse_ward_round'))
            ward_round.write({'evaluation_id': record.id})
        return record
