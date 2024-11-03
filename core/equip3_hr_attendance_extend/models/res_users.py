# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    minimum_face_descriptor = fields.Integer('Minimum Face Descriptor', compute='_compute_face_descriptor')
    current_face_descriptor = fields.Integer('Current Face Descriptor', compute='_compute_face_descriptor')

    def _compute_face_descriptor(self):
        amount_of_add_face_descriptor = int(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.amount_of_add_face_descriptor'))
        for user in self:
            user.minimum_face_descriptor = amount_of_add_face_descriptor
            user.current_face_descriptor = len(self.res_users_image_ids)

    # @api.onchange('res_users_image_ids')
    # def onchange_res_users_image_ids(self):
    #     amount_of_add_face_descriptor = int(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.amount_of_add_face_descriptor'))
    #     added_res_user_images = len(self.res_users_image_ids) + 1

    #     if added_res_user_images < amount_of_add_face_descriptor:
    #         amount_needed_face = amount_of_add_face_descriptor - added_res_user_images
    #         return {
    #             'warning': {'title': _('Warning'), 'message': _('Please add %s more face.' % amount_needed_face)},
    #         }


class ResUsersImage(models.Model):
    _inherit = 'res.users.image'

    minimum_face_descriptor = fields.Integer('Minimum Face Descriptor')
    current_face_descriptor = fields.Integer('Current Face Descriptor')
    is_cropped = fields.Boolean(string="Is Cropped")