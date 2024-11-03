# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.tools import email_split
from odoo.exceptions import UserError


def extract_email(email):
    """ extract the email address from a user-friendly email address """
    addresses = email_split(email)
    return addresses[0] if addresses else ''


class Patient(models.Model):
    _inherit = 'hms.patient'

    @api.depends('inverse_family_member_ids','inverse_family_member_ids.patient_id')
    def acs_get_family_partners(self):
        for rec in self:
            family_partner_ids = rec.inverse_family_member_ids.mapped('patient_id.partner_id').ids
            rec.acs_family_partner_ids = [(6,0,family_partner_ids)]

    inverse_family_member_ids = fields.One2many('acs.family.member', 'related_patient_id', string='Related Family')
    acs_family_partner_ids = fields.Many2many('res.partner', compute="acs_get_family_partners", store=True, string="Family Partners")
 
    @api.model
    def create(self, values):
        patient = super(Patient, self).create(values)
        company_id = self.company_id or self.env.user.sudo().company_id
        if company_id.create_auto_users and patient.email and not patient.user_ids:
            patient.sudo().create_patient_related_user()
        return patient

    def create_patient_related_user(self):
        for record in self:
            company_id = record.company_id or self.env.user.sudo().company_id
            if not record.email:
                raise UserError(_('Please define valid email for the Patient'))
            group_portal = self.env.ref('base.group_portal')
            group_portal = group_portal  or False
            user = record.user_ids[0] if record.user_ids else None
            # update partner email, if a new one was introduced
            # add portal group to relative user of selected partners
            user_portal = None
            # create a user if necessary, and make sure it is in the portal group
            if not user:
                user_portal = record.sudo().with_context(company_id=company_id)._create_user()
            else:
                user_portal = user
            if group_portal not in user_portal.groups_id:
                user_portal.write({'active': True, 'groups_id': [(4, group_portal.id)]})
                # prepare for the signup process
                record.partner_id.signup_prepare()

            #ACS NOTE: incase of sigup from website it takes portal user. 
            #And no need to send invitation when user it self is doing signup
            if not self.env.context.get('website_id'):
                record.sudo().send_invitaion_email()

    def _create_user(self):
        company_id = self.env.context.get('company_id')
        email = extract_email(self.email)
        ext_user = self.env['res.users'].sudo().search([('email','=',email)], limit=1)
        if ext_user:
            raise UserError(_('Patient/User already registered with given email address.'))

        return self.env['res.users'].with_context(no_reset_password=True)._create_user_from_template({
            'email': email,
            'login': email,
            'partner_id': self.partner_id.id,
            'company_id': company_id.id,
            'company_ids': [(6, 0, [company_id.id])],
        })

    def send_invitaion_email(self):
        for record in self:
            if not self.env.user.email:
                raise UserError(_('You must have an email address in your User Preferences to send emails.'))

            user = record.user_ids[0] if record.user_ids else None
            if not user:
                raise UserError(_('Patient have no related user in system! Please create one first.'))

            user.mapped('partner_id').sudo().signup_prepare(signup_type="reset", expiration=False)

            template = self.env.ref('acs_hms_portal.set_password_email')

            template_values = {
                'email_to': '${object.email|safe}',
                'email_cc': False,
                'auto_delete': True,
                'partner_to': False,
                'scheduled_date': False,
            }
            template.write(template_values)

            if not user.email:
                raise UserError(_("Cannot send email: user %s has no email address.") % user.name)
            template.sudo().with_context(lang=user.lang).send_mail(user.id, force_send=True, raise_exception=False)
