# -*- coding: utf-8 -*-
# Copyright 2020 Artem Shurshilov
# Odoo Proprietary License v1.0

# This software and associated files (the "Software") may only be used (executed,
# modified, executed after modifications) if you have purchased a valid license
# from the authors, typically via Odoo Apps, or if you have received a written
# agreement from the authors of the Software (see the COPYRIGHT file).

# You may develop Odoo modules that use the Software as a library (typically
# by depending on it, importing it and using its resources), but without copying
# any source code or material from the Software. You may distribute those
# modules under the license of your choice, provided that this license is
# compatible with the terms of the Odoo Proprietary License (For example:
# LGPL, MIT, or proprietary licenses similar to this one).

# It is forbidden to publish, distribute, sublicense, or sell copies of the Software
# or modified copies of the Software.

# The above copyright notice and this permission notice must be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = "res.users"

    res_users_image_ids = fields.One2many('res.users.image', 'res_user_id', string="Face recognition user's images", copy=True)
    face_emotion = fields.Selection(selection=[
        ('neutral', 'neutral'),
        ('happy', 'happy'),
        ('sad', 'sad'),
        ('angry', 'angry'),
        ('fearful', 'fearful'),
        ('disgusted', 'disgusted'),
        ('surprised', 'surprised'),
        ('any', 'any')], string="Emotion", required=True, default='any', help="The emotion that must be performed for access")
    face_gender = fields.Selection(selection=[
        ('male', 'male'),
        ('female', 'female'),
        ('any', 'any'),
    ], string="Gender", required=True, default='any',
        help="Gender to be Accessed")
    face_age = fields.Selection(selection=[
        ('20', '0-20'),
        ('30', '20-30'),
        ('40', '30-40'),
        ('50', '40-50'),
        ('60', '50-60'),
        ('70', '60-any'),
        ('any', 'any'),
    ], string="Age", required=True, default='any',
        help="Age for accessd")


class UserImage(models.Model):
    _name = 'res.users.image'
    _description = "User Image"
    _inherit = ['image.mixin']
    _order = 'sequence, id'

    name = fields.Char("Name", required=True)
    sequence = fields.Integer(default=10, index=True)
    image = fields.Image(required=True)
    image_detection = fields.Image()
    res_user_id = fields.Many2one('res.users', "User", index=True, ondelete='cascade')
    descriptor = fields.Char("Descriptor FR", readonly="1")

    _sql_constraints = [
        ('check_descriptor', 'check(length(descriptor)>50)', 'Descriptor length must be more then 50'),
    ]
