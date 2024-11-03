import json
import datetime
import itertools
import pytz

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.tools.date_utils import start_of, end_of, add, subtract
from odoo.tools import float_round
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


def convert_tz(dt, tz_from, tz_to):
    if isinstance(dt, str):
        dt = fields.Datetime.from_string(dt)
    if isinstance(tz_from, str):
        tz_from = pytz.timezone(tz_from)
    if isinstance(tz_to, str):
        tz_to = pytz.timezone(tz_to)
    dt = tz_from.localize(dt).astimezone(tz_to)
    return dt.replace(tzinfo=None)


def read_m2o(record, extra_fields=[]):
    field_names = ['id', 'display_name'] + extra_fields
    values = dict()
    for field_name in field_names:
        values[field_name] = record[field_name]
    return values

class MrpMPS(models.Model):
    _name = 'mrp.mps'
    _description = 'Master Production Schedule'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.mps') or _('New')
        return super(MrpMPS, self).create(vals)

    @api.model
    def _default_branch(self):
        if len(self.env.branches) == 1:
            return self.env.branch.id
        return False

    name = fields.Char(required=True, readonly=True, default=lambda self: _('New'), string='Reference')
    description = fields.Char(string='Name')
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    warehouse_id = fields.Many2one('stock.warehouse', required=True)
    product_ids = fields.Many2many('product.product', string='Products', domain="[('has_bom', '=', True)]")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True, readonly=True)
    branch_id = fields.Many2one('res.branch', default=_default_branch, required=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('close', 'Close')
    ], default='draft', required=True, string='Status', readonly=True)

    period_type = fields.Selection(related='company_id.manufacturing_period')

    datas = fields.Text(compute='compute_datas', inverse='set_datas', store=False)
    bom_edit_history = fields.Text()
    forecast_edit_history = fields.Text()

    reproduce_action = fields.Selection(selection=[
        ('mrp.plan', 'Production Plan'),
        ('mrp.production', 'Production Order')
    ], default='mrp.plan', string='Reproduce Action')

    plan_ids = fields.Many2many('mrp.plan', string='Production Plans', readonly=True)
    order_ids = fields.Many2many('mrp.production', string='Production Orders', readonly=True)
    request_ids = fields.Many2many('material.request', string='Material Requests', readonly=True)

    plan_count = fields.Integer(compute='_compute_plan_count')
    order_count = fields.Integer(compute='_compute_order_count')
    request_count = fields.Integer(compute='_compute_request_count')

    @api.depends('plan_ids')
    def _compute_plan_count(self):
        for record in self:
            record.plan_count = len(record.plan_ids)

    @api.depends('order_ids')
    def _compute_order_count(self):
        for record in self:
            record.order_count = len(record.order_ids)

    @api.depends('request_ids')
    def _compute_request_count(self):
        for record in self:
            record.request_count = len(record.request_ids)

    def _get_date_range(self):
        date_from = self.date_from
        date_to = self.date_to

        user_tz = self.tz()
        utc = pytz.utc
        
        date_from = convert_tz(datetime.datetime(date_from.year, date_from.month, date_from.day, 0, 0), utc, user_tz).date()
        date_to = convert_tz(datetime.datetime(date_to.year, date_to.month, date_to.day, 0, 0), utc, user_tz).date()
        
        period_type = self.period_type
        first_day = start_of(date_from, period_type)
        
        while first_day.weekday() in (5, 6):
            first_day += relativedelta(days=1)

        date_range = []
        while first_day <= date_to:
            last_day = end_of(first_day, period_type)
            date_range += [(first_day, last_day)]
            first_day = add(last_day, days=1)
            while first_day.weekday() in (5, 6):
                first_day += relativedelta(days=1)
        return date_range

    @api.model
    def get_swo_data(self, products):
        if not products:
            return {}
        
        query = """
        SELECT
            swo.product_id,
            SUM(swo.product_min_qty),
            SUM(swo.product_max_qty),
            (ARRAY_AGG(swo.run_rate_days))[1]
        FROM
            stock_warehouse_orderpoint swo
        WHERE
            swo.product_id IN %s
        GROUP BY
            swo.product_id
        """
        self.env.cr.execute(query, [tuple(products.ids)])
        return {o[0]: {
            'product_min_qty': o[1],
            'product_max_qty': o[2],
            'run_rate_days': o[3] or 1
        } for o in self.env.cr.fetchall()}

    @api.model
    def _get_duration_expected(self, operation_id, workcenter_id, qty_production):
        time_cycle = operation_id and operation_id.time_cycle or 60.0
        cycle_number = float_round(qty_production / workcenter_id.capacity, precision_digits=0, rounding_method='UP')
        return workcenter_id.time_start + workcenter_id.time_stop + cycle_number * time_cycle * 100.0 / workcenter_id.time_efficiency

    @api.model
    def _get_expected_end_date(self, expected_end_date, resource_id):
        attendance_ids = resource_id.attendance_ids.filtered(lambda a: a.dayofweek == str(expected_end_date.weekday()))
        if not attendance_ids:
            return False
        attendance_id = sorted(attendance_ids, key=lambda a: a.hour_from)[0]
        expected_end_date = datetime.datetime(expected_end_date.year, expected_end_date.month,\
            expected_end_date.day, int(attendance_id.hour_from), 0)
        return expected_end_date

    @api.model
    def _get_expected_duration(self, bom, to_produce):
        operations = set(bom.bom_line_ids.mapped('operation_id'))
        workcenters = {operation.id: operation._get_workcenter() for operation in operations}
        expected_duration = 0.0
        if not bom or to_produce <= 0.0:
            return expected_duration
        for bom_line_id in bom.bom_line_ids:
            workcenter_id = workcenters.get(bom_line_id.operation_id.id, False)
            if workcenter_id:
                expected_duration += self._get_duration_expected(bom_line_id.operation_id, workcenter_id, to_produce)
        return expected_duration

    @api.model
    def _get_suggested_start_date(self, expected_end_date, expected_duration, resource, workcenters):
        if not expected_end_date:
            return False
        
        workorders = [{
            'start': o.date_planned_start,
            'finish': o.date_planned_finished,
            'duration': o.duration_expected
        } for o in workcenters.order_ids.filtered(lambda o: o.date_planned_start and o.date_planned_finished and o.date_planned_finished > o.date_planned_start)]

        duration_left = expected_duration
        attendances = resource.cycle_attendances(expected_end_date)
        attendances = [attendances[0]] + attendances[1:][::-1]

        days = 0
        dayofweek = int(attendances[0].dayofweek)
        for i, att in enumerate(itertools.cycle(attendances)):
            hour_from = int(att.hour_from)
            hour_to = int(att.hour_to) if i > 0 else expected_end_date.hour
            minute_to = next_minute if i > 0 else expected_end_date.minute

            total_minutes = ((hour_to - hour_from) * 60) + minute_to
            taken_minutes = min(duration_left, total_minutes)

            days += dayofweek - int(att.dayofweek) if dayofweek >= int(att.dayofweek) else 7 - int(att.dayofweek) + dayofweek
            
            current_day = expected_end_date - relativedelta(days=days)
            finish = current_day.replace(hour=hour_to, minute=minute_to, second=0, microsecond=0)
            start = finish - relativedelta(minutes=taken_minutes)
            overlaps = list(filter(lambda w: w['start'] < finish and w['finish'] > start, workorders))

            if overlaps:
                duration_left = expected_duration # reset
                dayofweek = int(att.dayofweek)
                next_minute = max(o['start'] for o in overlaps).minute
                continue
            
            duration_left -= taken_minutes

            if duration_left <= 0.0:
                break

            dayofweek = int(att.dayofweek)
            next_minute = 0
        
        return start

    @api.model
    def _get_suggested_end_date(self, suggested_start_date, expected_duration, resource):
        if not suggested_start_date:
            return False
        
        duration_left = expected_duration
        attendances = resource.cycle_attendances(suggested_start_date)

        days = 0
        dayofweek = int(attendances[0].dayofweek)
        for i, att in enumerate(itertools.cycle(attendances)):
            hour_from = int(att.hour_from) if i > 0 else suggested_start_date.hour
            minute_from = 0 if i > 0 else suggested_start_date.minute
            total_minutes = ((att.hour_to - hour_from) * 60) - minute_from
            days += int(att.dayofweek) - dayofweek if int(att.dayofweek) >= dayofweek else 7 - dayofweek + int(att.dayofweek)
            if duration_left - total_minutes <= 0.0:
                break
            else:
                duration_left -= total_minutes
                dayofweek = int(att.dayofweek)

        return (suggested_start_date + relativedelta(days=days)).replace(hour=hour_from, minute=minute_from, second=0, microsecond=0) + relativedelta(minutes=duration_left)

    @api.model
    def _get_estimated_date(self, bom, date_planned_start, qty):
        if not date_planned_start:
            return False, False
        
        if not bom.bom_line_ids:
            raise ValidationError(_('Please set materials for %s' % bom.display_name))

        dt_object = convert_tz(date_planned_start, self.tz(), pytz.utc)

        start_date = max(dt_object, datetime.datetime.now().replace(second=0, microsecond=0))
        
        estimated_start_date = datetime.datetime.max
        estimated_end_date = datetime.datetime.min
        first_available_slots = {}
        for bom_line_id in bom.bom_line_ids:
            operation_id = bom_line_id.operation_id

            if not operation_id:
                raise ValidationError(_('Please set operation for material %s' % bom_line_id.display_name))
            
            workcenter_id = operation_id._get_workcenter()
            duration_expected = self._get_duration_expected(operation_id, workcenter_id, qty)

            workcenters = workcenter_id | workcenter_id.alternative_workcenter_ids

            best_start_date = False
            best_finished_date = datetime.datetime.max
            err_message = False
            for workcenter in workcenters:
                key = (workcenter, start_date, duration_expected)
                if key not in first_available_slots:
                    from_date, to_date = workcenter._get_first_available_slot(start_date, duration_expected)
                    from_date = from_date.replace(second=0, microsecond=0)
                    to_date = to_date.replace(second=0, microsecond=0)
                    first_available_slots[key] = (from_date, to_date)
                else:
                    from_date, to_date = first_available_slots[key]

                if not from_date:
                    continue
                
                if to_date and to_date < best_finished_date:
                    best_start_date = from_date
                    best_finished_date = to_date

            if best_finished_date == datetime.datetime.max:
                raise UserError(_('Impossible to plan. Please check the workcenter availabilities.'))
            
            if best_start_date < estimated_start_date:
                estimated_start_date = best_start_date
            if best_finished_date > estimated_end_date:
                estimated_end_date = best_finished_date

        if estimated_start_date != datetime.datetime.max:
            estimated_start_date = convert_tz(estimated_start_date, pytz.utc, self.tz())
        if estimated_end_date != datetime.datetime.min:
            estimated_end_date = convert_tz(estimated_end_date, pytz.utc, self.tz())
        return estimated_start_date, estimated_end_date

    @api.model
    def _get_workcenters(self, bom):
        workcenters = self.env['mrp.workcenter']
        if not bom:
            return workcenters
        for operation in set(bom.bom_line_ids.mapped('operation_id')):
            workcenter = operation._get_workcenter()
            workcenters |= workcenter
        return workcenters

    @api.model
    def _get_resource(self, workcenters):
        resource = self.env['resource.calendar']
        if not workcenters:
            return resource
        if len(workcenters) == 1:
            return workcenters[0].resource_calendar_id
        resources = set(workcenters.mapped('resource_calendar_id'))
        if len(resources) == 1:
            return list(resources)[0]
        workorder_ids = self.env['mrp.workorder']
        for workcenter in workcenters:
            workorder_id = self.env['mrp.workorder'].search([
                ('workcenter_id', '=', workcenter.id),
                ('date_planned_finished', '!=', False)
            ], order='date_planned_finished desc', limit=1)
            if not workorder_id:
                return workcenter.resource_calendar_id
            workorder_ids |= workorder_id
        return sorted(workorder_ids, key=lambda w: w.date_planned_finished)[0].workcenter_id.resource_calendar_id

    @api.model
    def tz(self):
        return self.env.context.get('tz') or self.env.user.tz

    def _get_forecasted_stock(self, forecast, on_hand):
        total_forecast_demand = forecast['total_forecast_demand']
        forecasted_stock = on_hand - total_forecast_demand
        confirmed_production = forecast['confirmed_production']
        carryover_demand = forecast['carryover_demand']

        min_stock = forecast['min_stock']
        max_stock = forecast['max_stock']
        if min_stock is False or max_stock is False:
            if forecasted_stock < 0:
                need_to_produce_hide = 0 - forecasted_stock - confirmed_production 
            else:
                need_to_produce_hide = 0
        else:
            if forecasted_stock < min_stock and carryover_demand == 0:
                need_to_produce_hide = 0 - forecasted_stock - confirmed_production + max_stock
            elif forecasted_stock < min_stock and carryover_demand > 0:
                need_to_produce_hide = 0 - forecasted_stock - confirmed_production
            else:
                need_to_produce_hide = 0
        need_to_produce = max(0, need_to_produce_hide)

        to_produce = forecast['to_produce']
        max_load = forecast['max_load']

        is_to_produce_edited = forecast['is_to_produce_edited']

        to_produce_ori = max(0, min(need_to_produce, max_load))
        if is_to_produce_edited:
            to_produce = history.get('to_produce', 0.0)
            is_to_produce_edited = to_produce != to_produce_ori
        else:
            to_produce = to_produce_ori

        return {
            'forecasted_stock': forecasted_stock,
            'need_to_produce_hide': need_to_produce_hide,
            'need_to_produce': need_to_produce,
            'to_produce': to_produce
        }
    
    @api.model
    def _update_backward(self, product_states, product_histories, next_date_start_tz, next_date_stop_tz, date_range):
        forecasts = product_states['forecasts']
        history = product_histories.get(str(next_date_stop_tz), {})

        next_forecast = forecasts[str(next_date_start_tz)]
        next_need_to_produce_hide = next_forecast['need_to_produce_hide']
        next_max_load = next_forecast['max_load']
        next_forecasted_demand = next_forecast['forecasted_demand']

        date_start_tz_index = date_range.index((next_date_start_tz, next_date_stop_tz)) - 1
        date_start_tz, date_stop_tz = date_range[date_start_tz_index]
        forecast = forecasts[str(date_start_tz)]

        carryover_demand = max(0.0, next_need_to_produce_hide - next_max_load)
        total_forecast_demand = carryover_demand + next_forecasted_demand
        on_hand = forecast['on_hand']

        forecast.update({
            'carryover_demand': carryover_demand,
            'total_forecast_demand': total_forecast_demand
        })

        forecast.update(self._get_forecasted_stock(forecast, on_hand))

        if date_start_tz_index > 0:
            self._update_backward(product_states, product_histories, date_start_tz, date_stop_tz, date_range)

        if not forecast['is_backdate']:
            self._update_forward(next_forecast, forecast)
        else:
            if not next_forecast['is_backdate']:
                product_states['carryover_left'] = carryover_demand

    @api.model
    def _update_forward(self, forecast, prev_forecast):
        on_hand_hide = prev_forecast['forecasted_stock'] + prev_forecast['confirmed_production'] + prev_forecast['to_produce']
        on_hand = max(0, on_hand_hide)
        forecast.update(
            self._get_forecasted_stock(forecast, on_hand),
            on_hand_hide=on_hand_hide,
            on_hand=on_hand)

    @api.depends('date_from', 'date_to', 'company_id', 'warehouse_id', 'product_ids', 'bom_edit_history', 'forecast_edit_history')
    def compute_datas(self):
        for record in self:
            record.datas = record._compute_datas()
    
    def _compute_datas(self):
        debug = False
        need_to_fill = ['date_from', 'date_to', 'company_id', 'warehouse_id']
        if any(not self[field_name] for field_name in need_to_fill):
            return json.dumps({
                'ranges': [],
                'states': {},
                'debug': debug
            }, default=str)

        company = self.company_id
        branch = self.branch_id

        bom_edit_history = json.loads(self.bom_edit_history or '{}')
        histories = json.loads(self.forecast_edit_history or '{}')

        date_range = self._get_date_range()
        date_range_reversed = date_range[::-1]

        period = company.manufacturing_period

        products = self.env['product.product'].browse(self.product_ids._origin.ids)

        SWO = self.get_swo_data(self.product_ids)
        warehouse = self.warehouse_id

        is_reproduce = self.env.context.get('is_reproduce', False)

        user_tz = self.tz()
        utc = pytz.utc
        today_tz = convert_tz(fields.Datetime.now(), utc, user_tz).date()

        states = {}
        for product in products:
            product_id_str = str(product.id)

            product_bom = bom_edit_history.get(product_id_str, {})
            product_histories = histories.get(product_id_str, {})

            is_bom_edited = product_bom.get('is_bom_edited', False)

            bom_domain = self.env['mrp.bom'].with_context(
                equip_bom_type='mrp',
                branch_id=branch.id
            )._bom_find_domain(product=product, company_id=company.id, bom_type='normal')
            boms = self.env['mrp.bom'].search(bom_domain, order='sequence, product_id')

            if is_bom_edited:
                bom = self.env['mrp.bom'].browse(product_bom.get('bom_id', False))
            else:
                bom = boms and boms[0] or self.env['mrp.bom']

            workcenters = self._get_workcenters(bom)
            resource = self._get_resource(workcenters)

            min_stock = SWO.get(product.id, {}).get('product_min_qty', False)
            max_stock = SWO.get(product.id, {}).get('product_max_qty', False)

            has_reordering_rules = min_stock is not False and max_stock is not False

            states[product_id_str] = {
                'product': read_m2o(product),
                'uom': read_m2o(product.uom_id, extra_fields=['rounding']),
                'bom': read_m2o(bom),
                'is_bom_edited': is_bom_edited,
                'boms': [read_m2o(bom) for bom in boms],
                'workcenters': [read_m2o(workcenter) for workcenter in workcenters],
                'resource': read_m2o(resource),
                'forecasts': {str(df): {} for df, dt in date_range},
                'carryover_left': 0.0,
                'has_reordering_rules': has_reordering_rules
            }

            for _iter, (date_start_tz, date_stop_tz) in enumerate(date_range):
                datetime_start = convert_tz(datetime.datetime(date_start_tz.year, date_start_tz.month, date_start_tz.day, 0, 0), user_tz, utc)
                datetime_stop = convert_tz(datetime.datetime(date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, 23, 59), user_tz, utc)

                is_backdate = date_start_tz < today_tz
                if is_backdate:
                    confirmed_demand = 0.0
                    forecasted_demand = 0.0
                    carryover_demand = 0.0
                    total_forecast_demand = 0.0
                    actual_delivery = sum(self.env['stock.move'].search([
                        ('product_id', '=', product.id),
                        ('date', '>=', datetime_start),
                        ('date', '<=', datetime_stop),
                        ('state', '=', 'done'),
                    ]).mapped('product_qty'))
                    
                    on_hand_hide = 0.0
                    on_hand = 0.0
                    forecasted_stock = 0.0
                    
                    confirmed_production = 0.0
                    need_to_produce_hide = 0.0
                    need_to_produce = 0.0
                    max_load = 0.0
                    to_produce = 0.0
                    actual_produced = sum(self.env['stock.move'].search([
                        ('product_id', '=', product.id),
                        ('date', '>=', datetime_start),
                        ('date', '<=', datetime_stop),
                        ('state', '=', 'done'),
                        ('production_id', '!=', False)
                    ]).mapped('product_qty'))

                    is_forecasted_demand_edited = False
                    is_to_produce_edited = False
                    is_scheduled_date_edited = False
                
                else:
                    is_today = date_start_tz == today_tz

                    history = product_histories.get(str(date_stop_tz), {})
                    is_forecasted_demand_edited = history.get('is_forecasted_demand_edited', False)
                    is_to_produce_edited = history.get('is_to_produce_edited', False)
                    is_scheduled_date_edited = history.get('is_scheduled_date_edited', False)

                    res = product.with_context(warehouse=warehouse.id, location=False)._compute_quantities_dict(None, None, None, from_date=datetime_start, to_date=datetime_stop)
                    confirmed_demand = res[product.id]['outgoing_qty']

                    forecasted_demand_ori = confirmed_demand
                    if is_forecasted_demand_edited:
                        forecasted_demand = history.get('forecasted_demand', 0.0)
                        is_forecasted_demand_edited = forecasted_demand != forecasted_demand_ori
                    else:
                        forecasted_demand = forecasted_demand_ori

                    actual_delivery = 0.0
                    actual_produced = 0.0

                    confirmed_production = sum(self.env['stock.move'].search([
                        ('product_id', '=', product.id),
                        ('date', '>=', datetime_start),
                        ('date', '<=', datetime_stop),
                        ('production_id.state', '=', 'confirmed')
                    ]).mapped('product_qty'))

                    max_load = 0.0
                    start = date_start_tz
                    while start <= date_stop_tz:
                        dayofweek = str(start.weekday())
                        max_load += bom.with_context(dayofweek=dayofweek).max_production
                        start = start + relativedelta(days=1)

                    on_hand_hide = 0.0
                    on_hand = 0.0
                    if is_today:
                        on_hand = res[product.id]['qty_available']

                    carryover_demand = 0.0
                    total_forecast_demand = 0.0
                    forecasted_stock = 0.0
                    need_to_produce_hide = 0.0
                    need_to_produce = 0.0
                    to_produce = 0.0

                    date_from = date_start_tz
                    date_to = date_stop_tz
                    expected_end_date = False
                    expected_duration = False
                    scheduled_date = False
                    scheduled_end_date = False
                    estimated_date = False
                    estimated_end_date = False

                states[product_id_str]['forecasts'][str(date_start_tz)] = {
                    # DEMAND
                    'confirmed_demand': confirmed_demand,
                    'forecasted_demand': forecasted_demand,
                    'carryover_demand': carryover_demand,
                    'total_forecast_demand': total_forecast_demand,
                    'actual_delivery': actual_delivery,

                    # STOCK
                    'min_stock': min_stock,
                    'max_stock': max_stock,
                    'on_hand_hide': on_hand_hide,
                    'on_hand': on_hand,
                    'forecasted_stock': forecasted_stock,

                    # PRODUCTION
                    'confirmed_production': confirmed_production,
                    'need_to_produce_hide': need_to_produce_hide,
                    'need_to_produce': need_to_produce,
                    'max_load': max_load,
                    'to_produce': to_produce,
                    'actual_produced': actual_produced,

                    # TECHNICAL
                    'is_backdate': is_backdate,
                    'is_forecasted_demand_edited': is_forecasted_demand_edited,
                    'is_to_produce_edited': is_to_produce_edited,
                    'is_scheduled_date_edited': is_scheduled_date_edited
                }

                if _iter > 0 and not is_backdate:
                    self._update_backward(states[product_id_str], product_histories, date_start_tz, date_stop_tz, date_range)

            for _iter, (date_start_tz, date_stop_tz) in enumerate(date_range):
                forecast = states[product_id_str]['forecasts'][str(date_start_tz)]
                is_backdate = forecast['is_backdate']

                scheduled_end_date = False
                estimated_date = False
                estimated_end_date = False
                expected_end_date = False
                expected_duration = False
                scheduled_date = False

                if not is_backdate:
                    to_produce = forecast['to_produce']

                    expected_end_date = self._get_expected_end_date(date_start_tz, resource)
                    expected_duration = self._get_expected_duration(bom, to_produce)

                    scheduled_date_ori = self._get_suggested_start_date(expected_end_date, expected_duration, resource, workcenters)
                    if is_scheduled_date_edited:
                        scheduled_date = forecast.get('scheduled_date', False)
                        is_scheduled_date_edited = scheduled_date != scheduled_date_ori
                    else:
                        scheduled_date = scheduled_date_ori

                    if is_reproduce:
                        scheduled_end_date = self._get_suggested_end_date(scheduled_date, expected_duration, resource)
                        estimated_date, estimated_end_date = self._get_estimated_date(bom, scheduled_date, to_produce)

                forecast.update({
                    'date_from': date_start_tz,
                    'date_to': date_stop_tz,
                    'expected_end_date': expected_end_date,
                    'expected_duration': expected_duration,
                    'scheduled_date': scheduled_date,
                    'scheduled_end_date': scheduled_end_date,
                    'estimated_date': estimated_date,
                    'estimated_end_date': estimated_end_date,
                })
                
        return json.dumps({
            'ranges': [o[0] for o in date_range],
            'states': states,
            'debug': debug
        }, default=str)

    def set_datas(self):
        for record in self:
            record._set_datas()

    def _set_datas(self):
        datas = json.loads(self.datas or '{}')
        states = datas.get('states', {})

        bom_edit_values = {}
        forecast_edit_values = {}
        for product_id, state in states.items():
            product_id_str = str(product_id)

            if state['is_bom_edited']:
                bom_edit_values[product_id_str] = {
                    'bom_id': state['bom']['id'],
                    'is_bom_edited': state['is_bom_edited']
                }

            for date_start, forecast in state.get('forecasts', {}).items():
                date_to = str(forecast['date_to'])

                if forecast.get('is_forecasted_demand_edited', False) or forecast.get('is_to_produce_edited', False) or forecast.get('is_scheduled_date_edited', False):
                    if product_id_str not in forecast_edit_values:
                        forecast_edit_values[product_id_str] = {
                            date_to: {
                                'forecasted_demand': forecast['forecasted_demand'],
                                'to_produce': forecast['to_produce'],
                                'scheduled_date': forecast['scheduled_date'],
                                'is_forecasted_demand_edited': forecast.get('is_forecasted_demand_edited', False),
                                'is_to_produce_edited': forecast.get('is_to_produce_edited', False),
                                'is_scheduled_date_edited': forecast.get('is_scheduled_date_edited', False)
                            }
                        }
                    else:
                        forecast_edit_values[product_id_str][date_to] = {
                            'forecasted_demand': forecast['forecasted_demand'],
                            'to_produce': forecast['to_produce'],
                            'scheduled_date': forecast['scheduled_date'],
                            'is_forecasted_demand_edited': forecast.get('is_forecasted_demand_edited', False),
                            'is_to_produce_edited': forecast.get('is_to_produce_edited', False),
                            'is_scheduled_date_edited': forecast.get('is_scheduled_date_edited', False)
                        }
        
        self.bom_edit_history = json.dumps(bom_edit_values, default=str)
        self.forecast_edit_history = json.dumps(forecast_edit_values, default=str)

    def action_confirm(self):
        self.ensure_one()
        self.state = 'progress'

    def action_produce(self):
        self.ensure_one()
        self.with_context(is_reproduce=True).compute_datas()

        context = self.env.context.copy()
        context.update({'is_reproduce': True})

        return {
            'name': _('Reproduce'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'target': 'new',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_manuf_other_operations.view_mrp_mps_form_reproduce').id,
            'context': context
        }

    def action_close(self):
        self.ensure_one()
        self.state = 'close'

    def action_create_production_draft(self):
        self.ensure_one()

        company = self.company_id
        branch = self.branch_id
        action = self.reproduce_action
        date_range = self._get_date_range()

        states = json.loads(self.datas or '{}').get('states', {})

        plans = self.env['mrp.plan']
        orders = self.env['mrp.production']

        for product_id, state in states.items():
            product = self.env['product.product'].browse(state['product']['id'])
            bom = self.env['mrp.bom'].browse(int(state['bom']['id']))

            if action == 'mrp.plan':
                plan_matrix_id = False
                if company.manufacturing_plan_conf:
                    plan_matrix_id = self.env['mrp.plan']._default_approval_matrix()

                product_qty = sum(o['to_produce'] for o in state['forecasts'].values())
                plan = self.env['mrp.plan'].create({
                    'name': 'Replenish %s' % (self.name, ),
                    'branch_id': branch.id,
                    'company_id': company.id,
                    'ppic_id': self.env.user.id,
                    'mps_product_id': product.id,
                    'mps_product_qty': product_qty,
                    'mps_bom_id': bom.id,
                    'mps_start_date': date_range[0][0],
                    'mps_end_date': date_range[-1][1],
                    'approval_matrix_id': plan_matrix_id,
                    'analytic_tag_ids': self.env['mrp.plan']._default_analytic_tags(company_id=company, branch_id=branch)
                })

                wizard = self.env['mrp.production.wizard'].with_context(
                    active_model='mrp.plan',
                    active_id=plan.id,
                    active_ids=plan.ids,
                ).create({
                    'plan_id': plan.id,
                    'line_ids': [(0, 0, {
                        'product_id': product.id,
                        'product_uom': bom.product_uom_id.id,
                        'product_qty': product_qty,
                        'no_of_mrp': 1,
                        'company': company.id,
                        'branch_id': branch.id,
                        'bom_id': bom.id
                    })]
                })
                wizard.confirm()
                plans |= plan

            else:
                order_matrix_id = False
                if company.manufacturing_order_conf:
                    order_matrix_id = self.env['mrp.production']._default_approval_matrix()

                total_product_qty = 0.0
                for date, forecast in state['forecasts'].items():
                    product_qty = forecast['to_produce']

                    if product_qty <= 0.0:
                        continue

                    scheduled_date = forecast['scheduled_date']
                    date_planned_start = convert_tz(scheduled_date, self.env.user.tz, pytz.utc)
                    date_planned_finished = date_planned_start + relativedelta(hours=1)

                    order_values = {
                        'product_id': product.id,
                        'product_qty': product_qty,
                        'bom_id': bom.id,
                        'user_id': self.env.user.id,
                        'product_uom_id': bom.product_uom_id.id,
                        'company_id': company.id,
                        'branch_id': branch.id,
                        'date_planned_start': date_planned_start,
                        'date_planned_finished': date_planned_finished,
                        'mps_start_date': forecast['date_from'],
                        'mps_end_date': forecast['date_to'],
                        'approval_matrix_id': order_matrix_id
                    }

                    order = self.env['mrp.production'].create(order_values).sudo()
                    order.onchange_product_id()
                    order.onchange_branch()
                    order._onchange_workorder_ids()
                    order._onchange_move_raw()
                    order._onchange_move_finished()
                    order.onchange_workorder_ids()
                    orders |= order

        self.write({
            'plan_ids': [(4, plan.id) for plan in plans],
            'order_ids': [(4, order.id) for order in orders],
        })

    def action_submit_material_request(self):
        self.ensure_one()

        company = self.company_id
        branch = self.branch_id
        states = json.loads(self.datas or '{}').get('states', {})
        now = fields.Datetime.now()

        group = {}
        for product_id, state in states.items():
            total_qty = sum(o['to_produce'] for o in state['forecasts'].values())

            bom = self.env['mrp.bom'].browse(state['bom']['id'])
            for bom_line in bom.bom_line_ids:
                product = bom_line.product_id
                workcenter = bom_line.operation_id._get_workcenter()
                location = workcenter.location_id
                to_consume_qty = (bom_line.product_qty / bom.product_qty) * total_qty
                product_qty = bom_line.product_uom_id._compute_quantity(to_consume_qty, bom_line.product_id.uom_id)

                if location not in group:
                    group[location] = {product: product_qty}
                else:
                    if product not in group[location]:
                        group[location][product] = product_qty
                    else:
                        group[location][product] += product_qty

        material_values = []
        for location, product_group in group.items():
            warehouse = location.get_warehouse()

            move_values = []
            for product, qty in product_group.items():
                move_values += [(0, 0, {
                    'description': product.display_name,
                    'product': product.id,
                    'product_unit_measure': product.uom_id.id,
                    'quantity': qty,
                    'destination_warehouse_id': warehouse.id
                })]

            material_values += [{
                'requested_by': self.env.user.id,
                'company_id': company.id,
                'branch_id': branch.id,
                'destination_warehouse_id': warehouse.id,
                'destination_location_id': location.id,
                'schedule_date': now,
                'source_document': self.name,
                'product_line': move_values,
            }]

        requests = self.env['material.request'].create(material_values)
        self.write({'request_ids': [(4, request.id) for request in requests]})

    def action_view_production_plan(self):
        self.ensure_one()
        return {
            'name': _('Production Plans'),
            'res_model': 'mrp.plan',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'view_type': 'list,form',
            'domain': [('id', 'in', self.plan_ids.ids)],
            'target': 'current'
        }

    def action_view_production_order(self):
        self.ensure_one()
        return {
            'name': _('Production Orders'),
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'view_type': 'list,form',
            'domain': [('id', 'in', self.order_ids.ids)],
            'target': 'current'
        }

    def action_view_material_request(self):
        self.ensure_one()

        requests = self.request_ids
        action = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.material_request_action')
        if len(requests) == 1:
            action.update({
                'views':  [(self.env.ref('equip3_inventory_operation.material_request_form_view').id, 'form')], 
                'res_id': requests[0].id,
                'target': 'new',
            })
        else:
            action.update({'domain': [('id', 'in', requests.ids)]})
        
        return action

    def action_view_detail(self):
        self.ensure_one()
        context = self.env.context.copy()
        context['default_mps_id'] = self.id
        return {
            'name': _('Master Production Schedule'),
            'res_model': 'mrp.mps.detail',
            'views': [[False, 'form']],
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
