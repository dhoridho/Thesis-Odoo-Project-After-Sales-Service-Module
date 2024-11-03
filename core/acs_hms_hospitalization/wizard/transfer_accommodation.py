# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from datetime import datetime

class TransferAccommodation(models.TransientModel):
    _name = "transfer.accommodation"
    _description = "Transfer Accommodation"

    hospitalization_id = fields.Many2one('acs.hospitalization', 'Hospitalization', required=True)
    patient_id = fields.Many2one ('hms.patient','Patient', required=True)
    old_ward = fields.Many2one ('hospital.ward', 'Old Ward/Room')
    old_bed = fields.Many2one ('hospital.bed', 'Old Bed No.')
    new_ward = fields.Many2one ('hospital.ward', 'Ward/Room')
    new_bed = fields.Many2one ('hospital.bed', 'Bed No.')

    @api.model
    def default_get(self,fields):
        context = self._context or {}
        res = super(TransferAccommodation, self).default_get(fields)
        hospitalization = self.env['acs.hospitalization'].browse(context.get('active_ids', []))
        res.update({
            'hospitalization_id': hospitalization.id,
            'patient_id': hospitalization.patient_id.id,
            'old_ward': hospitalization.ward_id.id,
            'old_bed': hospitalization.bed_id.id,
        })
        return res


    def transfer_accommodation(self):
        context = self._context or {}
        history_obj = self.env['patient.accommodation.history']
        for data in self:
            hist_id = history_obj.search([('hospitalization_id','=',data.hospitalization_id.id), ('bed_id','=',data.old_bed.id)])
            hist_id.write({'end_date': datetime.now()})
            data.old_bed.write({'state': 'free'})
            data.new_bed.write({'state': 'reserved'})
            history_obj.create({
                'hospitalization_id': data.hospitalization_id.id,
                'patient_id': data.patient_id.id,
                'ward_id': data.new_ward.id,
                'bed_id': data.new_bed.id,
                'start_date': datetime.now(),
            })
            data.hospitalization_id.write({
                'ward_id': data.new_ward.id,
                'bed_id': data.new_bed.id,
            })
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: