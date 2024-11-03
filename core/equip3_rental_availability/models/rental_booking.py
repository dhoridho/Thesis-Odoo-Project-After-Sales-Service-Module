from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import date, timedelta, datetime
from dateutil import relativedelta


class RentalBooking(models.Model):
    _name = 'rental.booking'
    _description = 'Rental Booking'

    name = fields.Char(string='Name')
    from_date = fields.Datetime('From Date', required=True)
    to_date = fields.Datetime('To Date', required=True)

    @api.model
    def _domain_product(self):
        domain = []
        context = self.env.context
		
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', context.get('allowed_company_ids'))]

        if context.get('allowed_branch_ids'):
            domain += [
                '|',
                ('branch_id', 'in', context.get('allowed_branch_ids'))
                ,('branch_id', '=', False)
            ]

        products = self.env['product.product'].search(domain)

        return [('id', 'in', products.ids), ('rent_ok', '=', True)]

    product_ids = fields.Many2many(comodel_name='product.product', string='Products', domain=_domain_product)
    initial_term = fields.Integer(string='Initial Terms')
    initial_term_type = fields.Selection(string='Initial Term Type', selection=[('hours', 'Hours'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], default="hours", required=True)
    total = fields.Monetary('Total', compute="_compute_total", store=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', default=lambda self:self.env.user.company_id.currency_id.id)
    line_ids = fields.One2many(comodel_name='rental.booking.line', inverse_name='rental_id', string='Rental Booking Line')
    is_search = fields.Boolean(string='Is Search', default=False)
    is_create = fields.Boolean(string='Is Create', default=False)
    need_recheck = fields.Selection(string='Need Recheck', selection=[('not', 'Not'), ('need', 'Need'),], default='not', readonly=True)
    hide_select_all =  fields.Boolean()
    
    
    def select_all(self):
        if self.line_ids:
            line_update = [data.write({'is_selected':True}) for data in self.line_ids]
            self.hide_select_all = True
            
    def deselect_all(self):
        if self.line_ids:
            line_update = [data.write({'is_selected':False}) for data in self.line_ids]
            self.hide_select_all = False
        
    
    
    @api.depends('line_ids','line_ids.is_selected','initial_term','initial_term_type')
    def _compute_total(self):
        for i in self:
            line_selecteds = i.line_ids.filtered(lambda l:l.is_selected == True)
            rental = 0
            if line_selecteds:
                if i.initial_term_type == 'hours':
                    rental = sum(line_selecteds.mapped('hourly_rental'))
                elif i.initial_term_type == 'days':
                    rental = sum(line_selecteds.mapped('daily_rental'))
                elif i.initial_term_type == 'weeks':
                    rental = sum(line_selecteds.mapped('weekly_rental'))
                elif i.initial_term_type == 'months':
                    rental = sum(line_selecteds.mapped('monthly_rental'))
            i.total = rental*i.initial_term
                

    @api.constrains('from_date', 'to_date')
    def check_date(self):
        if self.from_date and self.from_date.date() < date.today():
            raise UserError(_('You cannot enter past date'))
        if self.to_date and self.to_date.date() < date.today():
            raise UserError(_('You cannot enter past date'))
    
    @api.constrains('initial_term')
    def check_initial_term(self):
        if self.initial_term <= 0:
            raise UserError(_("Initial Term can't 0 or Negative!!"))

    @api.model
    def create(self, vals):
        vals.update({'name': self.env['ir.sequence'].next_by_code('rental_booking') or _('New')})
        return super(RentalBooking, self).create(vals)


    @api.onchange('from_date','to_date')
    def _onchange_from_date_to_date(self):
        if self.from_date and self.to_date:
            selisih = self.to_date - self.from_date
            if selisih.seconds:
                seconds_to_hours = int(selisih.seconds/3600) + (selisih.seconds % 3600 > 0)
                days_to_hours = selisih.days and selisih.days*24 or 0
                total_hours = seconds_to_hours+days_to_hours
                self.initial_term = total_hours
                self.initial_term_type = 'hours'
            else:
                if selisih.days % 30 == 0:
                    self.initial_term  = int(selisih.days/30)
                    self.initial_term_type = 'months'
                elif selisih.days % 7 == 0:
                    self.initial_term  = int(selisih.days/7)
                    self.initial_term_type = 'weeks'
                else:
                    self.initial_term = int(selisih.days)
                    self.initial_term_type = 'days'
        self.need_recheck = 'need'

    @api.onchange('initial_term','initial_term_type')
    def _onchange_initial_term(self):
        if self.initial_term and self.from_date:
            if self.initial_term_type == 'hours':
                self.to_date = self.from_date + timedelta(hours=self.initial_term)
            elif self.initial_term_type == 'days':
                self.to_date = self.from_date + timedelta(days=self.initial_term)
            elif self.initial_term_type == 'weeks':
                self.to_date = self.from_date + timedelta(days=self.initial_term*7)
            else:
                self.to_date = self.from_date + timedelta(days=self.initial_term*30)
        self.need_recheck = 'need'

    def search_product(self):
        self.need_recheck = 'not'
        fmt = '%Y-%m-%d %H:%M:%S' 
        date_from = self.from_date.strftime(fmt)
        date_to = self.to_date.strftime(fmt)
        self.hide_select_all= False
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise ValidationError("To Date must be greater than From date")
            else:
                line_ids = []
                if self.product_ids:
                    sql = """select 
                                spl.id 
                            from 
                                stock_production_lot spl 
                            join product_product pp on pp.id = spl.product_id 
                            where 
                                pp.id in %s AND 
                                spl.id NOT IN
                                (select 
                                    rl.lot_id 
                                from rental_order ro, rental_order_line rl
                                Where 
                                    ro.state NOT IN('draft','close') AND 
                                    ro.id=rl.rental_id AND 
                                    (
                                        ((ro.start_date BETWEEN %s AND %s) OR (ro.end_date BETWEEN %s AND %s)) OR  
                                        ((%s BETWEEN ro.start_date AND ro.end_date) OR (%s BETWEEN ro.start_date AND ro.end_date))
                                    )
                                )
                            group by spl.id 
                            """

                    self.env.cr.execute(sql,(
                        # 
                        tuple(p.id for p in self.product_ids),
                        date_from, date_to, date_from, date_to,
                        date_from, date_to
                        ))
                else:
                    sql = """select 
                                spl.id 
                            from 
                                stock_production_lot spl 
                            join product_product pp on pp.id = spl.product_id 
                            where 
                                pp.rent_ok = true AND
                                spl.id NOT IN
                                (select 
                                    rl.lot_id 
                                from rental_order ro, rental_order_line rl
                                Where 
                                    ro.state NOT IN('draft','close') AND 
                                    ro.id=rl.rental_id AND 
                                    (
                                        ((ro.start_date BETWEEN %s AND %s) OR (ro.end_date BETWEEN %s AND %s)) OR  
                                        ((%s BETWEEN ro.start_date AND ro.end_date) OR (%s BETWEEN ro.start_date AND ro.end_date))
                                    )
                                )
                            group by spl.id 
                            """

                    self.env.cr.execute(sql,(
                        date_from, date_to, date_from, date_to,
                        date_from, date_to
                        ))

                query_result = self.env.cr.dictfetchall()
                if query_result:
                    for result in query_result:
                        lot_id = self.env['stock.production.lot'].browse(result['id'])
                        vals = {
                            'lot_id':result['id'],
                            'monthly_rental':lot_id.product_id.rent_per_month,
                            'weekly_rental':lot_id.product_id.rent_per_week,
                            'daily_rental':lot_id.product_id.rent_per_day,
                            'hourly_rental':lot_id.product_id.rent_per_hour,
                        }
                        line_data = self.env['rental.order.line'].search([('lot_id', '=', result['id']),
                                  '&', ('buffer_end_time', '>', date_from), ('buffer_start_time', '<', date_to)])
                        if not line_data:
                            line_ids.append((0, 0, vals))
                    if line_ids:
                        self.is_search = True
                        if self.line_ids:
                            self.line_ids.unlink()
                        self.line_ids = line_ids
                else:
                    raise ValidationError("Sorry, no products are currently available.")


    def create_rental_order(self):
        if self.need_recheck == 'need':
            raise ValidationError(_("You updated date, please search again to recheck availability!"))
        line_ids = []
        line_selecteds = self.line_ids.filtered(lambda l:l.is_selected == True)
        if not line_selecteds:
            raise ValidationError(_("First Please Select the Product"))
        for line in line_selecteds:
            if self.initial_term_type == 'hours':
                price_unit = line.hourly_rental*self.initial_term
            elif self.initial_term_type == 'days':
                price_unit = line.daily_rental*self.initial_term
            elif self.initial_term_type == 'weeks':
                price_unit = line.weekly_rental*self.initial_term
            elif self.initial_term_type == 'months':
                price_unit = line.monthly_rental*self.initial_term
            else:
                price_unit = 0
            product = line.lot_id.product_id
            name = product.name_get()[0][1]
            vals = {
                'lot_id':line.lot_id.id,
                'product_id':product.id,
                'price_unit': price_unit,
                'name':name,
            }
            line_ids.append((0,0,vals))
        self.is_create = True
        return {
                    'name': "Rental Order",
                    'view_mode': 'form',
                    'res_model': "rental.order",
                    'type': 'ir.actions.act_window',
                    'context': {'default_start_date': self.from_date,
                                'default_rental_initial': self.initial_term,
                                'default_rental_initial_type': self.initial_term_type,
                                'default_rental_line': line_ids and line_ids or False,
                                },
                }

class RentalBookingLine(models.Model):
    _name = 'rental.booking.line'
    _description = 'Rental Booking Line'

    lot_id = fields.Many2one(comodel_name='stock.production.lot', string='Serial Number', required=True)
    product_id =  fields.Many2one('product.product',related='lot_id.product_id')
    monthly_rental = fields.Monetary('Monthly Rental')
    weekly_rental = fields.Monetary('Weekly Rental')
    daily_rental = fields.Monetary('Daily Rental')
    hourly_rental = fields.Monetary('Hourly Rental')
    is_selected = fields.Boolean(string='Select Product')
    rental_id = fields.Many2one(comodel_name='rental.booking', string='Rental Booking')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', related="rental_id.currency_id")
    
    
    
    
