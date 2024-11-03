# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PhysicianSpecialty(models.Model):
    _name = 'physician.specialty'
    _description = "Physician Specialty"

    code = fields.Char(string='Code')
    name = fields.Char(string='Specialty', required=True, translate=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Name must be unique!'),
    ]


class PhysicianDegree(models.Model):
    _name = 'physician.degree'
    _description = "Physician Degree"

    name = fields.Char(string='Degree')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Name must be unique!'),
    ]


class Physician(models.Model):
    _name = 'hms.physician'
    _description = "Physician"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'res.users': 'user_id'}

    user_id = fields.Many2one('res.users',string='Related User', required=True,
        ondelete='cascade', help='User-related data of the physician')
    code = fields.Char(string='Physician Code', default='/', tracking=True)
    degree_ids = fields.Many2many('physician.degree', 'physician_rel_education', 'physician_ids','degree_ids', string='Degree')
    specialty_id = fields.Many2one('physician.specialty', ondelete='set null', string='Specialty', help='Specialty Code', tracking=True)
    medical_license = fields.Char(string='Medical License', tracking=True)

    @api.model
    def create(self, values):
        if values.get('code','/') == '/':
            values['code'] = self.env['ir.sequence'].next_by_code('hms.physician')
        if values.get('email'):
            values['login'] = values['email']
        return super(Physician, self).create(values)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: