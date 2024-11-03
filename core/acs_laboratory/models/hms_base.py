# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountInvoice(models.Model):
    _inherit = 'account.move'

    request_id = fields.Many2one('acs.laboratory.request', string='Lab Request', copy=False, ondelete='restrict')
    hospital_invoice_type = fields.Selection(selection_add=[('laboratory', 'Laboratory')])


class StockMove(models.Model):
    _inherit = "stock.move"

    lab_test_id = fields.Many2one('patient.laboratory.test', string="Lab Test", ondelete="restrict")


class ACSConsumableLine(models.Model):
    _inherit = "hms.consumable.line"

    patient_lab_test_id = fields.Many2one('patient.laboratory.test', string="Patient Lab Test", ondelete="restrict")
    lab_test_id = fields.Many2one('acs.lab.test', string="Lab Test", ondelete="restrict")


class ACSPatient(models.Model):
    _inherit = "hms.patient"

    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        for rec in self:
            rec.request_count = len(rec.request_ids)
            rec.test_count = len(rec.test_ids)

    def _acs_get_attachemnts(self):
        attachments = super(ACSPatient, self)._acs_get_attachemnts()
        attachments += self.test_ids.mapped('attachment_ids')
        return attachments

    request_ids = fields.One2many('acs.laboratory.request', 'patient_id', string='Lab Requests')
    test_ids = fields.One2many('patient.laboratory.test', 'patient_id', string='Tests')
    request_count = fields.Integer(compute='_rec_count', string='# Lab Requests')
    test_count = fields.Integer(compute='_rec_count', string='# Lab Tests')

    def action_lab_requests(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.hms_action_lab_test_request")
        action['domain'] = [('id','in',self.request_ids.ids)]
        action['context'] = {'default_patient_id': self.id}
        return action

    def action_view_test_results(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.action_lab_result")
        action['domain'] = [('id','in',self.test_ids.ids)]
        action['context'] = {'default_patient_id': self.id}
        return action

class product_template(models.Model):
    _inherit = "product.template"

    hospital_product_type = fields.Selection(selection_add=[('pathology', 'Pathology'), ('radiology', 'Radiology')])


class Physician(models.Model):
    _inherit = "hms.physician"

    def _rec_count(self):
        Labrequest = self.env['acs.laboratory.request']
        Labresult = self.env['patient.laboratory.test']
        for record in self.with_context(active_test=False):
            record.lab_request_count = Labrequest.search_count([('physician_id', '=', record.id)])
            record.lab_result_count = Labresult.search_count([('physician_id', '=', record.id)])

    lab_request_count = fields.Integer(compute='_rec_count', string='# Lab Request')
    lab_result_count = fields.Integer(compute='_rec_count', string='# Lab Result')

    def action_lab_request(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.hms_action_lab_test_request")
        action['domain'] = [('physician_id','=',self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action

    def action_lab_result(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.action_lab_result")
        action['domain'] = [('physician_id','=',self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action

#ACS Note : Option to configure the Collection center in user and set directly in lab request in version 15
# class ResUsers(models.Model):
#     _inherit = "res.users"

#     collection_center_id = fields.Many2one('acs.laboratory', 
#         string='Collection Center')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: