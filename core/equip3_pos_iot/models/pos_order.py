from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.depends('log_adult_male_count', 'log_adult_female_count')
    def _compute_adult_count(self):
        for record in self:
            record.log_adult_count = record.log_adult_male_count + record.log_adult_female_count

    @api.depends('log_child_male_count', 'log_child_female_count')
    def _compute_child_count(self):
        for record in self:
            record.log_child_count = record.log_child_male_count + record.log_child_female_count

    @api.depends('log_adult_male_count', 'log_child_male_count')
    def _compute_male_count(self):
        for record in self:
            record.log_male_count = record.log_adult_male_count + record.log_child_male_count

    @api.depends('log_adult_female_count', 'log_child_female_count')
    def _compute_female_count(self):
        for record in self:
            record.log_female_count = record.log_adult_female_count + record.log_child_female_count

    @api.depends('log_adult_male_count', 'log_adult_female_count', 'log_child_male_count', 'log_child_female_count')
    def _compute_total_count(self):
        for record in self:
            record.log_total_count = record.log_adult_male_count + record.log_adult_female_count + record.log_child_male_count + record.log_child_female_count


    gravio_log_id = fields.Many2one('gravio.log', string='Gravio Log')
    log_adult_male_count = fields.Integer(string='Adult Male')
    log_adult_female_count = fields.Integer(string='Adult Female')
    log_child_male_count = fields.Integer(string='Child Male')
    log_child_female_count = fields.Integer(string='Child Female')
    log_adult_count = fields.Integer(string='Adult', compute=_compute_adult_count, store=True)
    log_child_count = fields.Integer(string='Child', compute=_compute_child_count, store=True)
    log_male_count = fields.Integer(string='Male', compute=_compute_male_count, store=True)
    log_female_count = fields.Integer(string='Female', compute=_compute_female_count, store=True)
    log_total_count = fields.Integer(string='Total Customer', compute=_compute_total_count, store=True)
