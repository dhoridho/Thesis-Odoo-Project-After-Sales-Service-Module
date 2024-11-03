# -*- coding: utf-8 -*-

from odoo import api, fields, models


class event_rule(models.Model):
    """
    The model to keep params of how joint event should be created
    """
    _name = "event.rule"
    _description = "Event Rule"

    @api.onchange('res_model')
    def _onchange_res_model(self):
        """
        Onchange method for res_model
        The goal is to put defaults and make configuration easier

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        if self.res_model and self.res_model.model:
            self.action = self.env['ir.actions.act_window'].search([('res_model', '=', self.res_model.model)], limit=1)
            self.field_name = self.env['ir.model.fields'].search([
                ('model_id', '=', self.res_model.id), 
                ('name', '=', 'name'), 
                ('ttype', '=', 'char'),
            ], limit=1)
            self.field_description = self.env['ir.model.fields'].search(
                [
                    ('model_id', '=', self.res_model.id),
                    ('name', '=', 'description'),
                    '|', 
                        ('ttype', '=', 'text'),
                        ('ttype', '=', 'html'),
                ], limit=1)
            self.field_start = self.env['ir.model.fields'].search(
                [
                    ('model_id', '=', self.res_model.id),
                    '|', '|', '|', '|', '|', '|',
                        ('name', '=', 'date_start'),
                        ('name', '=', 'start_date'),
                        ('name', '=', 'date_begin'),
                        ('name', '=', 'begin_date'),
                        ('name', '=', 'date'),
                        ('name', '=', 'start'),
                        ('name', '=', 'begin'),
                    '|',
                        ('ttype', '=', 'datetime'),
                        ('ttype', '=', 'date'),
                ], limit=1)
            self.field_stop = self.env['ir.model.fields'].search(
                [
                    ('model_id', '=', self.res_model.id),
                    '|', '|', '|', '|', '|',
                        ('name', '=', 'date_end'),
                        ('name', '=', 'end_date'),
                        ('name', '=', 'end'),
                        ('name', '=', 'date_stop'),
                        ('name', '=', 'stop_date'),
                        ('name', '=', 'stop'),
                    '|',
                        ('ttype', '=', 'datetime'),
                        ('ttype', '=', 'date'),
                ], limit=1)
            self.field_delay = self.env['ir.model.fields'].search(
                [
                    ('model_id', '=', self.res_model.id),
                    '|',
                        ('name', '=', 'duration'),
                        ('name', '=', 'delay'),
                    ('ttype', '=', 'float'),
                ], limit=1)
            self.domain = "[]"
        else:
            self.domain = "[]"


    name = fields.Char(
        string='Description', 
        required=True,
    )
    res_model = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        help='Which object would trigger event creation',
        ondelete="cascade",
    )
    res_model_domain = fields.Char(
        string='Tech Domain',
        related='res_model.model',
        store=True,
        compute_sudo=True,
        readonly=True,
    )
    field_start = fields.Many2one(
        'ir.model.fields',
        'Start date field',
        domain="['|', ('ttype', '=', 'datetime'), ('ttype', '=', 'date'), ('model_id', '=', res_model)]",
        required=True,
        ondelete="cascade",
        help="name of the record's field holding the start date for the event",
    )
    field_stop = fields.Many2one(
        'ir.model.fields',
        ondelete="cascade",
        string='Stop date field',
        domain="['|', ('ttype', '=', 'datetime'), ('ttype', '=', 'date'), ('model_id', '=', res_model)]",
        help="name of the record's field holding the end date for the event",
    )
    field_delay = fields.Many2one(
        'ir.model.fields',
        ondelete="cascade",        
        string='Delay field',
        domain="[('ttype', '=', 'float'), ('model_id', '=', res_model),]",
        help='provides the duration of the event',
    )
    field_all_day = fields.Many2one(
        'ir.model.fields',
        ondelete="cascade",
        string='Whole Day Field',
        domain="[('ttype', '=', 'boolean'), ('model_id', '=', res_model)]",
        help='name of a boolean field on the record indicating whether the corresponding event is flagged as day-long',
    )
    always_all_day = fields.Boolean(
        string='Always Whole Day',
        help="""Flag this checkbox to indicate that related events last always the whole day.
                Thus, such event would be placed on a special place in calendar. 'Whole Day Field' would not be used.
        """,
        )
    field_atendees = fields.Many2one(
        'ir.model.fields',
        string='Attendees Field',
        domain="""[
            '|', '|', 
                ('ttype', '=', 'many2one'), 
                ('ttype', '=', 'one2many'),
                ('ttype', '=', 'many2many'), 
            ('model_id', '=', res_model), 
            '|',
                ('relation','=','res.users'), 
                ('relation','=','res.partner')
        ]""",
        required=True,
        ondelete="cascade",
        help='Name of a reference field with stated partners',
    )
    field_name = fields.Many2one(
        'ir.model.fields',
        string='Name Field',
        domain="[('ttype', '=', 'char'), ('model_id', '=', res_model)]",
        help='Name of a char field which would be used as a name for new event',
        required=True,
        ondelete="cascade",
    )
    field_description = fields.Many2one(
        'ir.model.fields',
        ondelete="cascade",
        string='Description Field',
        domain="['|', ('ttype', '=', 'text'), ('ttype', '=', 'html'), ('model_id', '=', res_model)]",
        help='Name of a description field which would be used as a description for new event',
    )
    fields_extra_partner_id = fields.Many2one(
        'ir.model.fields',
        string='Contact Links',
        domain="""[
            ('ttype', '=', 'many2one'), 
            ('model_id', '=', res_model), 
            ('relation','=','res.partner')
        ]""",
        required=False,
        ondelete="cascade",
        help='Link to customers, vendors, so on',
    )
    domain = fields.Char(
        string='Domain',
        default="[]",
        help="Use to limit objects by certain criteria. E.g. show only new sales orders [('state','in',[draft,sent])]",
    )
    action = fields.Many2one(
        'ir.actions.act_window',
        string='Action',
        domain="[('res_model','=',res_model_domain)]",
        help='Which form view to open when clicking on an event card',
        required=True,
    )
    last_sync_date = fields.Datetime(
        string="Last Sync Time",
        default=lambda self: fields.Datetime.now(),
    )
