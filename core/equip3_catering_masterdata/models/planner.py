# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError

class CateringMenuPlanner(models.Model):
    _name = 'catering.menu.planner'
    _rec_name = "reference_number"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    reference_number = fields.Char("Reference Number", tracking=True)
    package_id = fields.Many2one("product.product", string="Package",domain="[('is_catering','=',True),('catering_type':'package')]", required=True, tracking=True)
    from_date = fields.Date(string='From Date', required=True, tracking=True)
    to_date = fields.Date(string='To Date', required=True, tracking=True)
    planner_ids = fields.One2many(comodel_name='menu.planner', inverse_name='catering_menu_id', string='Menu Planner Lines', tracking=True)
    
    @api.model
    def create(self, vals):
        vals['reference_number'] = self.env['ir.sequence'].next_by_code('catering.menu.planner')
        res = super(CateringMenuPlanner, self).create(vals)
        return res

    def action_generate_planner(self):
        planner_ids = []
        reset_all = False
        if self.from_date and self.to_date:
            interval = ((self.to_date-self.from_date)).days+1
            if self.planner_ids and not self.planner_ids.filtered(lambda p:p.planner_date <= self.to_date and p.planner_date >= self.from_date):
                reset_all = True
        else:
            interval = 0

        if interval:
            for i in range(interval):
                date = self.from_date + timedelta(days=i)
                if date.weekday() == 0 and not self.package_id.monday:
                    continue
                if date.weekday() == 1 and not self.package_id.tuesday:
                    continue
                if date.weekday() == 2 and not self.package_id.wednesday:
                    continue
                if date.weekday() == 3 and not self.package_id.thursday:
                    continue
                if date.weekday() == 4 and not self.package_id.friday:
                    continue
                if date.weekday() == 5 and not self.package_id.saturday:
                    continue
                if date.weekday() == 6 and not self.package_id.sunday:
                    continue
                if not self.planner_ids.filtered(lambda p:p.planner_date == date):
                    vals = {
                        'package_id':self.package_id.id,
                        'planner_date':date,
                    }
                    planner_ids.append((0,0,vals))
        if self.planner_ids and reset_all:
            self.planner_ids.unlink()
        if self.planner_ids:
            before_from_date = self.planner_ids.filtered(lambda p:p.planner_date < self.from_date)
            if before_from_date:
                before_from_date.unlink()
            after_to_date = self.planner_ids.filtered(lambda p:p.planner_date > self.to_date)
            if after_to_date:
                after_to_date.unlink()
            false_monday = self.planner_ids.filtered(lambda p:p.planner_date.weekday() == 0)
            if false_monday and not self.package_id.monday:
                false_monday.unlink()
            false_tuesday = self.planner_ids.filtered(lambda p:p.planner_date.weekday() == 1)
            if false_tuesday and not self.package_id.tuesday:
                false_tuesday.unlink()
            false_wednesday = self.planner_ids.filtered(lambda p:p.planner_date.weekday() == 2)
            if false_wednesday and not self.package_id.wednesday:
                false_wednesday.unlink()
            false_thursday = self.planner_ids.filtered(lambda p:p.planner_date.weekday() == 3)
            if false_thursday and not self.package_id.thursday:
                false_thursday.unlink()
            false_friday = self.planner_ids.filtered(lambda p:p.planner_date.weekday() == 4)
            if false_friday and not self.package_id.friday:
                false_friday.unlink()
            false_saturday = self.planner_ids.filtered(lambda p:p.planner_date.weekday() == 5)
            if false_saturday and not self.package_id.saturday:
                false_saturday.unlink()
            false_sunday = self.planner_ids.filtered(lambda p:p.planner_date.weekday() == 6)
            if false_sunday and not self.package_id.sunday:
                false_sunday.unlink()
        self.planner_ids = planner_ids

class Planner(models.Model):
    _name = 'menu.planner'
    _rec_name = "reference_number"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'created_date desc'

    reference_number = fields.Char("Reference Number", tracking=True)
    package_id = fields.Many2one("product.product", string="Package", tracking=True)
    planner_date = fields.Date("Planner Date", default=fields.Date.today, tracking=True)
    masking_package_id = fields.Many2one("product.product", string="Masking Package", related="package_id", tracking=True)
    masking_planner_date = fields.Date("Masing Planner Date", default=fields.Date.today, related="planner_date", tracking=True)
    created_date = fields.Date("Creation Date", default=fields.Date.today, readonly=True, tracking=True)
    created_by = fields.Many2one("res.users", string="Created By", default=lambda self: self.env.uid, readonly=True, tracking=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company.id, tracking=True)
    line_ids = fields.One2many("planner.line", "menu_planner_id", string="Lines", tracking=True)
    customer_ids = fields.One2many("customer.line", "menu_planner_id", string="Customer", readonly=True, tracking=True)
    catering_menu_id = fields.Many2one(comodel_name='catering.menu.planner', string='Catering Menu Planner', ondelete="cascade", tracking=True)
    menu_lines = fields.Boolean(string="Menu Lines", compute="_compute_menu_lines", tracking=True)

    @api.model
    def create(self, vals):
        vals['reference_number'] = self.env['ir.sequence'].next_by_code('menu.planner')
        res = super(Planner, self).create(vals)
        return res

    @api.constrains('planner_date','package_id')
    def _check_planner_date(self):
        for i in self:
            cek_menu_planner = self.search([
                ('package_id', '=', i.package_id.id),
                ('planner_date', '=', i.planner_date),
                ('id', '!=', i.id)
            ])
            if cek_menu_planner:
                raise ValidationError(_("Menu Planner for this date already exists"))

    @api.depends('line_ids')
    def _compute_menu_lines(self):
        for rec in self:
            if rec.line_ids:
                rec.menu_lines = True
            else:
                rec.menu_lines = False
    
    @api.constrains('line_ids')
    def _check_menu_lines(self):
        for record in self:
            if not record.line_ids.menu_id:
                raise ValidationError("Can't save Menu Planner Lines because there's no product in Menu Lines")

class PlannerLine(models.Model):
    _name = 'planner.line'

    menu_planner_id = fields.Many2one("menu.planner", string="Planner")
    menu_id = fields.Many2one("product.product", string="Menu")
    desc = fields.Char("Description", related='menu_id.name')
    quantity = fields.Float("Quantity", default=1)
    uom_id = fields.Many2one("uom.uom", string="Unit Of Measure", related='menu_id.uom_id')

class CustomerLine(models.Model):
    _name = 'customer.line'

    menu_planner_id = fields.Many2one("menu.planner", string="Planner")
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    name = fields.Char("Name")
    order = fields.Char("Order")
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Picking')
    remark = fields.Char(string='Remark')
    is_button_visible = fields.Boolean(string='Is Button Visible', compute="_compute_is_button_visible")

    @api.depends('menu_planner_id','menu_planner_id.planner_date')
    def _compute_is_button_visible(self):
        for i in self:
            is_button_visible = False
            if i.menu_planner_id and i.menu_planner_id.planner_date:
                today = fields.Date.today()
                day = self.env['ir.config_parameter'].sudo().get_param('buffer_date', 1)
                if today <= i.menu_planner_id.planner_date-timedelta(days=int(day)):
                    is_button_visible = True
            i.is_button_visible = is_button_visible
    