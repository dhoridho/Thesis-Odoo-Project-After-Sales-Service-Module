# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class Anesthesia(models.Model):
    _name = "hms.anesthesia"
    _rec_name="name"
    _description = "Anesthesia"

    name = fields.Char('Anesthesia Name', required=True)


class PreOpetativeCheckListTemplate(models.Model):
    _name="pre.operative.check.list.template"
    _description = "Pre Operative Checklist Template"

    name = fields.Char(string="Name", required=True)
    remark = fields.Char(string="Remarks")


class PreOpetativeCheckList(models.Model):
    _name="pre.operative.check.list"
    _description = "Pre Operative Checklist"

    name = fields.Char(string="Name", required=True)
    is_done = fields.Boolean(string="Done", default=False)
    remark = fields.Char(string="Remarks")
    surgery_id = fields.Many2one("hms.surgery", ondelete="cascade", string="Surgery")


class ACSDietplan(models.Model):
    _name = "hms.dietplan"
    _description = "Diet plan"

    name = fields.Char(string='Name', required=True)


class PastSurgerys(models.Model):
    _name = "past.surgeries"
    _description = "Past Surgerys"

    result = fields.Char(string='Result')
    date = fields.Date(string='Date')
    hosp_or_doctor = fields.Char(string='Hospital/Doctor')
    description = fields.Char(string='Description', size=128)
    complication = fields.Text("Complication")
    patient_id = fields.Many2one('hms.patient', ondelete="restrict", string='Patient ID', help="Mention the past surgeries of this patient.")


class ACSMedicamentLine(models.Model):
    _name = "medicament.line"
    _description = "Medicine Lines"
    
    product_id = fields.Many2one('product.product', ondelete="cascade", string='Medicine Name')
    name = fields.Char(string='Name')
    medicine_uom_id = fields.Many2one('uom.uom', string='Unit', help='Amount of medication (eg, 250 mg) per dose')
    qty = fields.Float(string='Qty',default=1.0)
    active_component_ids = fields.Many2many('active.comp','medica_line_comp_rel','medica_id','line_id',string='Active Component')
    form_id = fields.Many2one('drug.form', ondelete="cascade", string='Form', help='Drug form, such as tablet or gel')
    dose = fields.Float(string='Dosage', digits=(16, 2) ,help="Amount of medication (eg, 250 mg) per dose")
    common_dosage_id = fields.Many2one('medicament.dosage', ondelete="cascade", string='Frequency', help='Drug form, such as tablet or gel')    
    surgery_template_id = fields.Many2one('hms.surgery.template', ondelete="cascade", string='Surgery Template')
    surgery_id = fields.Many2one('hms.surgery', ondelete="cascade", string='Surgery')
    instruction = fields.Char("Instructions")

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.form_id = self.product_id.form_id.id
            self.dose = self.product_id.dosage
            self.medicine_uom_id = self.product_id.uom_id.id
            self.common_dosage_id = self.product_id.common_dosage_id.id
            self.active_component_ids = [(6, 0, [x.id for x in self.product_id.active_component_ids])]
