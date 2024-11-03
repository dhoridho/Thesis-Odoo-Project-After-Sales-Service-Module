# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class ACSLabTestUom(models.Model):
    _name = "acs.lab.test.uom"
    _description = "Lab Test UOM"
    _order = 'sequence asc'
    _rec_name = 'code'

    name = fields.Char(string='UOM Name', required=True)
    code = fields.Char(string='Code', required=True, index=True, help="Short name - code for the test UOM")
    sequence = fields.Integer("Sequence", default="100")

    _sql_constraints = [('code_uniq', 'unique (name)', 'The Lab Test code must be unique')]


class AcsLaboratory(models.Model):
    _name = 'acs.laboratory'
    _description = 'Laboratory'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin']
    _inherits = {
        'res.partner': 'partner_id',
    }

    description = fields.Text()
    is_collection_center = fields.Boolean('Is Collection Center')
    partner_id = fields.Many2one('res.partner', 'Partner', ondelete='restrict', required=True)


class LabTest(models.Model):
    _name = "acs.lab.test"
    _description = "Lab Test Type"

    name = fields.Char(string='Name', help="Test type, eg X-Ray, hemogram,biopsy...", index=True)
    code = fields.Char(string='Code', help="Short name - code for the test")
    description = fields.Text(string='Description')
    product_id = fields.Many2one('product.product',string='Service', required=True)
    critearea_ids = fields.One2many('lab.test.critearea','test_id', string='Test Cases')
    remark = fields.Char(string='Remark')
    report = fields.Text (string='Test Report')
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Company' ,default=lambda self: self.env.user.company_id.id)
    consumable_line_ids = fields.One2many('hms.consumable.line', 'lab_test_id',
        string='Consumable Line')
    acs_tat = fields.Char(string='Turnaround Time')
    test_type = fields.Selection([
        ('pathology','Pathology'),
        ('radiology','Radiology'),
    ], string='Test Type', default='pathology')
    result_value_type = fields.Selection([
        ('quantitative','Quantitative'),
        ('qualitative','Qualitative'),
    ], string='Result Type', default='quantitative')
    sample_type_id = fields.Many2one('acs.laboratory.sample.type', string='Sample Type')

    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the account must be unique per company !')
    ]

    def name_get(self):
        res = []
        for rec in self:
            name = rec.name
            if rec.code:
                name = "%s [%s]" % (rec.name, rec.code)
            res += [(rec.id, name)]
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


class LabTestCritearea(models.Model):
    _name = "lab.test.critearea"
    _description = "Lab Test Criteria"
    _order="sequence, id asc"

    name = fields.Char('Parameter')
    sequence = fields.Integer('Sequence',default=100)
    result = fields.Char('Result')
    lab_uom_id = fields.Many2one('acs.lab.test.uom', string='UOM')
    remark = fields.Char('Remark')
    normal_range = fields.Char('Normal Range')
    normal_range_male = fields.Char('Normal Range (Male)')
    normal_range_female = fields.Char('Normal Range (Female)')
    test_id = fields.Many2one('acs.lab.test','Test type', ondelete='cascade')
    patient_lab_id = fields.Many2one('patient.laboratory.test','Lab Test', ondelete='cascade')
    request_id = fields.Many2one('acs.laboratory.request', 'Lab Request', ondelete='cascade')
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Company',default=lambda self: self.env.user.company_id.id)
    display_type = fields.Selection([
        ('line_section', "Section")], default=False, help="Technical field for UX purpose.")
    #ACS: in doo15 warning and danger can be removed. After checkinging need
    result_type = fields.Selection([
        ('low', "Low"),
        ('normal', "Normal"),
        ('high', "High"),
        ('positive', "Positive"),
        ('negative', "Negative"),
        ('warning', "Warning"),
        ('danger', "Danger"),
        ], default='normal', string="Result Type", help="Technical field for UI purpose.")
    result_value_type = fields.Selection([
        ('quantitative','Quantitative'),
        ('qualitative','Qualitative'),
    ], string='Result Value Type', default='quantitative')

    @api.onchange('normal_range_male')
    def onchange_normal_range_male(self):
        if self.normal_range_male and not self.normal_range_female:
            self.normal_range_female = self.normal_range_male

    @api.onchange('result')
    def onchange_result(self):
        if self.result and self.result_value_type=='quantitative' and self.normal_range:
            try:
                split_value = self.normal_range.split('-')
                low_range = high_range = 0
                result = float(self.result)
                if len(split_value)==2:
                    low_range = float(split_value[0])
                    high_range = float(split_value[1])
                elif len(split_value)==2:
                    low_range = float(split_value[0])
                    high_range = float(split_value[0])

                if low_range or high_range:
                    if result < low_range:
                        self.result_type = 'low'
                    elif result > high_range:
                        self.result_type = 'high'
                    elif result > low_range and result < high_range:
                        self.result_type = 'normal'
                    elif result==low_range or result==high_range:
                        self.result_type = 'warning'
            except:
                pass


class PatientLabSample(models.Model):
    _name = "acs.patient.laboratory.sample"
    _description = "Patient Laboratory Sample"
    _order = 'date desc, id desc'

    STATES = {'cancel': [('readonly', True)], 'examine': [('readonly', True)], 'collect': [('readonly', True)]}

    name = fields.Char(string='Name', help="Sample Name", readonly=True,copy=False, index=True)
    patient_id = fields.Many2one('hms.patient', string='Patient', required=True)
    user_id = fields.Many2one('res.users',string='User', default=lambda self: self.env.user, states=STATES)
    date = fields.Date(string='Date', default=fields.Date.context_today, states=STATES)
    request_id = fields.Many2one('acs.laboratory.request', string='Lab Request', ondelete='restrict', required=True, states=STATES)
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Company',default=lambda self: self.env.user.company_id.id, states=STATES)
    state = fields.Selection([
        ('draft','Draft'),
        ('collect', 'Collected'),
        ('examine', 'Examined'),
        ('cancel','Cancel'),
    ], string='State',readonly=True, default='draft')
    sample_type_id = fields.Many2one('acs.laboratory.sample.type', string='Sample Type', required=True, states=STATES)
    container_name = fields.Char(string='Sample Container Code', help="If using preprinted sample tube/slide/box no can be updated here.", copy=False, index=True)

    notes = fields.Text(string='Notes', states=STATES)

    #Just to make object selectable in selction field this is required: Waiting Screen
    acs_show_in_wc = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique (name,company_id)', 'Sample Name must be unique per company !')
    ]

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('acs.patient.laboratory.sample')
        return super(PatientLabSample, self).create(vals)

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_("Record can be delete only in Draft state."))
        return super(PatientLabSample, self).unlink()

    @api.onchange('request_id')
    def onchange_request_id(self):
        if self.request_id:
            self.patient_id = self.request_id.patient_id.id

    def action_collect(self):
        self.state = 'collect'

    def action_examine(self):
        self.state = 'examine'

    def action_cancel(self):
        self.state = 'cancel'


class LaboratoryGroupLine(models.Model):
    _name = "laboratory.group.line"
    _description = "Laboratory Group Line"

    group_id = fields.Many2one('laboratory.group', ondelete='restrict', string='Laboratory Group')
    test_id = fields.Many2one('acs.lab.test',string='Test', ondelete='cascade', required=True)
    acs_tat = fields.Char(related='test_id.acs_tat', string='Turnaround Time', readonly=True)
    instruction = fields.Char(string='Special Instructions')
    sale_price = fields.Float(string='Sale Price')
    test_type = fields.Selection([
        ('pathology','Pathology'),
        ('radiology','Radiology'),
    ], string='Test Type', default='pathology')

    @api.onchange('test_id')
    def onchange_test(self):
        if self.test_id:
            self.sale_price = self.test_id.product_id.lst_price


class LaboratoryGroup(models.Model):
    _name = "laboratory.group"
    _description = "Laboratory Group"

    name = fields.Char(string='Group Name', required=True)
    line_ids = fields.One2many('laboratory.group.line', 'group_id', string='Medicament line')
    test_type = fields.Selection([
        ('pathology','Pathology'),
        ('radiology','Radiology'),
    ], string='Test Type', default='pathology')


class LabSampleType(models.Model):
    _name = "acs.laboratory.sample.type"
    _description = "Laboratory Sample Type"
    _order = 'sequence asc'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer("Sequence", default="100")
    description = fields.Text("Description")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: