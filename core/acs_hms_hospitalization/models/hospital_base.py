# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class Bed(models.Model):
    _name = 'hospital.bed'
    _description = 'Bed'

    def _get_patient(self):
        for rec in self:
            patient_id = False
            ac_hists = rec.accommodation_history_ids.filtered(lambda r: r.start_date and not r.end_date )
            if ac_hists:
                patient_id = ac_hists[0].patient_id.id
            rec.patient_id = patient_id

    READONLY_STATES = {'reserved': [('readonly', True)], 'occupied': [('readonly', True)], 'blocked': [('readonly', True)]}
    
    name = fields.Char(string='Name', required=1, states=READONLY_STATES)
    product_id = fields.Many2one('product.product', ondelete='cascade',
        string='Bed Product', required=1, domain=[('hospital_product_type', '=', 'bed')],
        context={'default_hospital_product_type': 'bed'}, states=READONLY_STATES)
    bed_type = fields.Selection([
        ('gatch', 'Gatch Bed'),
        ('electric', 'Electric'),
        ('stretcher', 'Stretcher'),
        ('low', 'Low Bed'),
        ('low_air_loss', 'Low Air Loss'),
        ('circo_electric', 'Circo Electric'),
        ('clinitron', 'Clinitron')], string='Type', default='gatch', required=True, states=READONLY_STATES)
    telephone = fields.Char(size=14, string='Telephone', states=READONLY_STATES)
    state = fields.Selection([
        ('free', 'Free'),
        ('reserved', 'Reserved'),
        ('occupied', 'Occupied'),
        ('blocked', 'Out of Use'),], string='Status', default="free")
    ward_id = fields.Many2one('hospital.ward', ondelete='restrict', string='Ward/Room', states=READONLY_STATES)
    accommodation_history_ids = fields.One2many("patient.accommodation.history","bed_id",
        string="Accommodation History", states=READONLY_STATES)
    notes = fields.Text(string='Notes', states=READONLY_STATES)
    patient_id = fields.Many2one('hms.patient', compute="_get_patient", ondelete="restrict", string="Patient", states=READONLY_STATES)
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',default=lambda self: self.env.user.company_id.id, states=READONLY_STATES)
    invoice_policy = fields.Selection([
        ('full', 'Days (Full)'),
        ('hourly', 'Hours')], string='Invoice Policy', default='full', required=True, states=READONLY_STATES)

    @api.onchange('product_id')
    def onchnage_product_id(self):
        if not self.name:
            self.name = self.product_id.name

    def action_accommodation_history(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_hospitalization.action_accommodation_history")
        action['domain'] = [('bed_id', '=', self.id)]
        action['context'] = {'default_bed_id': self.id}
        return action

    def copy(self, default=None):
        self.ensure_one()
        chosen_name = default.get('name') if default else ''
        new_name = chosen_name or _('%s (copy)') % self.name
        default = dict(default or {}, name=new_name)
        return super(Bed, self).copy(default)


class ACSHospitalWard(models.Model):
    _name = 'hospital.ward'
    _description = 'Ward/Room'

    def _rec_count(self):
        for rec in self:
            rec.bed_count = len(rec.bed_ids)
            rec.bed_available_count = len(rec.bed_ids.filtered(lambda r: r.state=='free' ))

    name = fields.Char(string='Name', required=True, 
        help='Ward / Room Number')
    building_id = fields.Many2one('hospital.building', ondelete='restrict', 
        string='Building')
    floor = fields.Char(string='Floor Number')
    gender = fields.Selection([
        ('men', 'Men Ward'),
        ('women', 'Women Ward'),
        ('unisex', 'Unisex')], string='Gender', required=True, default="unisex")
    state = fields.Selection([
        ('available', 'Available'),
        ('full', 'Full')], string='Status', default="available")
    ward_room_type = fields.Selection([
        ('general', 'General'),
        ('semi_spaecial', 'Semi-Special'),
        ('deluxe', 'Deluxe'),
        ('super_deluxe', 'Super Deluxe'),
        ('suite', 'Suite'),
        ('sharing', 'Sharing'),
        ('icu', 'ICU'),
        ('dialysis', 'Dialysis'),
        ('recovery_room', 'Recovery Room'), ], 
        string='Wards/Room Type',required=True, default='general')
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',default=lambda self: self.env.user.company_id.id)

    #Facility
    private = fields.Boolean(string='Private',
        help='Check this option for private room')
    television = fields.Boolean(string='Television')
    refrigerator = fields.Boolean(string='Refrigerator')
    internet = fields.Boolean(string='Internet Access')
    bio_hazard = fields.Boolean(string='Bio Hazard', 
        help='Check this option if there is biological hazard')
    private_bathroom = fields.Boolean(string='Private Bathroom')
    telephone = fields.Boolean(string='Telephone')
    microwave = fields.Boolean(string='Microwave')
    guest_sofa = fields.Boolean(string='Guest sofa-bed')
    air_conditioning = fields.Boolean(string='Air Conditioning')

    bed_ids = fields.One2many('hospital.bed', 'ward_id', 'Bed Line', copy=False)
    notes = fields.Text('Notes')
    bed_count = fields.Integer(compute='_rec_count', string='# Beds')
    bed_available_count = fields.Integer(compute='_rec_count', string='#Available Beds')

    def action_bed(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_hospitalization.action_bed")
        action['domain'] = [('ward_id', '=', self.id)]
        action['context'] = {'default_ward_id': self.id}
        return action

    def copy(self, default=None):
        self.ensure_one()
        chosen_name = default.get('name') if default else ''
        new_name = chosen_name or _('%s (copy)') % self.name
        default = dict(default or {}, name=new_name)
        return super(ACSHospitalWard, self).copy(default)


class ACSHospitalBuilding(models.Model):
    _name = 'hospital.building'
    _description = "Hospital Building"

    name = fields.Char(string='Name', required=True,
        help='Name of the building within the institution')
    code = fields.Char(string='Code')
    extra_info = fields.Text(string='Extra Info')
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',default=lambda self: self.env.user.company_id.id)


class ACSHospitalOT(models.Model):
    _name = 'acs.hospital.ot'
    _description = "Operation Theater"

    name = fields.Char(string='Name', index=True, required=True, 
        help='Name of the Operating Room')
    physician_id = fields.Many2one('hms.physician', string='Physician', ondelete="restrict")
    building = fields.Many2one('hospital.building', string='Bulding', index=True, ondelete="restrict")
    telephone_number = fields.Integer(string='Telephone Number',
        help='Telephone number / Extension')
    state = fields.Selection([
        ('free', 'Free'),
        ('reserved', 'Reserved'),
        ('occupied', 'Occupied'),
        ('na', 'Not available')], string=' Current Status', default="free")
    note = fields.Text(string='Extra Info')
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',default=lambda self: self.env.user.company_id.id) 

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: