# -*- coding: utf-8 -*-
import datetime
import itertools
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round
from datetime import timedelta
from calendar import monthrange
from dateutil.relativedelta import relativedelta


def convert_tz(dt, tz_from, tz_to):
    if isinstance(dt, str):
        dt = fields.Datetime.from_string(dt)
    if isinstance(tz_from, str):
        tz_from = pytz.timezone(tz_from)
    if isinstance(tz_to, str):
        tz_to = pytz.timezone(tz_to)
    dt = tz_from.localize(dt).astimezone(tz_to)
    return dt.replace(tzinfo=None)


class MrpProductionSchedule(models.Model):
    _name = 'equip.mrp.production.schedule'
    _order = 'warehouse_id, sequence'
    _description = 'Schedule the production of Product in a warehouse'

    @api.model
    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

    def _search_bom_uom(self, operator, value):
        return [('bom_id.product_uom_id', operator, value)]

    def _search_product_template(self, operator, value):
        return [('product_id.product_tmpl_id', operator, value)]

    def _compute_non_zero_forecast(self):
        states = {r['id']: r for r in self.get_production_schedule_view_state()}
        keys = ('low_stock', 'max_stock', 'on_hand_qty', 'sales', 'forecasted_demand', 'forecasted_stock', 'to_replenish_qty')
        for record in self:
            state_forecast = states[record.id]['forecast_ids']
            for key in keys:
                record[key] = any(r[key] != 0.0 for r in state_forecast)

    def _search_non_zero_forecast(self, key_state, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operation not supported!'))
        if not key_state:
            raise UserError(_('Key state not provided!'))
        if key_state not in ('low_stock', 'max_stock', 'on_hand_qty', 'sales', 'forecasted_demand', 'forecasted_stock', 'to_replenish_qty'):
            raise UserError(_('%s is not valid key state!' % key_state))
        states =  self.search([]).get_production_schedule_view_state()
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            mps_ids = [state['id'] for state in states if any(s[key_state] != 0.0 for s in state['forecast_ids'])]
        else:
            mps_ids = [state['id'] for state in states if any(s[key_state] == 0.0 for s in state['forecast_ids'])]
        return [('id', 'in', mps_ids)]

    def _search_any_low_stock(self, operator, value):
        return self._search_non_zero_forecast('low_stock', operator, value)

    def _search_any_max_stock(self, operator, value):
        return self._search_non_zero_forecast('max_stock', operator, value)

    def _search_any_on_hand_qty(self, operator, value):
        return self._search_non_zero_forecast('on_hand_qty', operator, value)

    def _search_any_sales(self, operator, value):
        return self._search_non_zero_forecast('sales', operator, value)

    def _search_any_forecasted_demand(self, operator, value):
        return self._search_non_zero_forecast('forecasted_demand', operator, value)
    
    def _search_any_forecasted_stock(self, operator, value):
        return self._search_non_zero_forecast('forecasted_stock', operator, value)

    def _search_any_to_replenish_qty(self, operator, value):
        return self._search_non_zero_forecast('to_replenish_qty', operator, value)

    @api.model
    def tz(self):
        return self.env.context.get('tz') or self.env.user.tz

    @api.model
    def _get_period_selection(self):
        return [(str(i), range_name) for i, range_name in enumerate(self.env.company.date_range_to_str())]

    @api.depends('product_id', 'company_id')
    def _compute_bom(self):
        for record in self:
            boms = record._find_boms()
            record.bom_id = boms and boms[0].id or False

    @api.depends('product_id', 'company_id')
    def _compute_boms(self):
        for record in self:
            boms = record._find_boms()
            record.bom_ids = [(6, 0, boms.ids)]

    def _find_boms(self):
        self.ensure_one()
        product = self.product_id
        company = self.company_id
        branch = self.env.branch
        if product and company:
            bom_domain = self.env['mrp.bom'].with_context(
                branch_id=branch.id,
                equip_bom_type='mrp'
            )._bom_find_domain(product=product, company_id=company.id, bom_type='normal')
            return self.env['mrp.bom'].search(bom_domain, order='sequence, product_id')
        return self.env['mrp.bom']

    forecast_ids = fields.One2many('equip.mrp.product.forecast', 'production_schedule_id', string='Forecasted Quantity at Date')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('has_bom', '=', True)]")
    product_tmpl_id = fields.Many2one('product.template', related="product_id.product_tmpl_id", search=_search_product_template)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='bom_id.product_uom_id', search=_search_bom_uom)
    
    bom_ids = fields.One2many('mrp.bom', string='Allowed Bill of Materials', compute=_compute_boms)
    
    sequence = fields.Integer(related='product_id.sequence', store=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True, default=_default_warehouse_id)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', compute=_compute_bom, store=True, readonly=False, 
        domain="""[
        '&',
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id),
            '&',
                '|',
                    ('product_id', '=', product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids', '=', product_id),
                        ('product_id', '=', False),
        ('type', '=', 'normal')]""")

    # for filtering purposes
    any_low_stock = fields.Boolean(compute=_compute_non_zero_forecast, search=_search_any_low_stock)
    any_max_stock = fields.Boolean(compute=_compute_non_zero_forecast, search=_search_any_max_stock)
    any_on_hand_qty = fields.Boolean(compute=_compute_non_zero_forecast, search=_search_any_on_hand_qty)
    any_sales = fields.Boolean(compute=_compute_non_zero_forecast, search=_search_any_sales)
    any_forecasted_demand = fields.Boolean(compute=_compute_non_zero_forecast, search=_search_any_forecasted_demand)
    any_forecasted_stock = fields.Boolean(compute=_compute_non_zero_forecast, search=_search_any_forecasted_stock)
    any_to_replenish_qty = fields.Boolean(compute=_compute_non_zero_forecast, search=_search_any_to_replenish_qty)

    _sql_constraints = [
        ('warehouse_product_ref_uniq', 'unique (warehouse_id, product_id)', _('The combination of warehouse and product must be unique!')),
    ]

    @api.model
    def _get_duration_expected(self, operation_id, workcenter_id, qty_production):
        time_cycle = operation_id and operation_id.time_cycle or 60.0
        cycle_number = float_round(qty_production / workcenter_id.capacity, precision_digits=0, rounding_method='UP')
        return workcenter_id.time_start + workcenter_id.time_stop + cycle_number * time_cycle * 100.0 / workcenter_id.time_efficiency

    @api.model
    def _get_expected_end_date(self, period, date_range, resource_id):
        if not period or not date_range or not resource_id:
            return False
        expected_end_date = date_range[int(period)][0]
        attendance_ids = resource_id.attendance_ids.filtered(
            lambda a: a.dayofweek == str(expected_end_date.weekday()))
        if not attendance_ids:
            return False
        attendance_id = sorted(attendance_ids, key=lambda a: a.hour_from)[0]
        expected_end_date = datetime.datetime(expected_end_date.year, expected_end_date.month,\
            expected_end_date.day, int(attendance_id.hour_from), 0)
        return convert_tz(expected_end_date, self.tz(), pytz.utc)

    @api.model
    def _get_workcenter(self, bom_id):
        workcenter_ids = self.env['mrp.workcenter']
        if not bom_id :
            return workcenter_ids
        for operation in set(bom_id.bom_line_ids.mapped('operation_id')):
            workcenter_id = operation._get_workcenter()
            workcenter_ids |= workcenter_id
        return workcenter_ids

    @api.model
    def _get_expected_duration(self, bom_id, to_produce_qty):
        operations = set(bom_id.bom_line_ids.mapped('operation_id'))
        workcenters = {operation.id: operation._get_workcenter() for operation in operations}
        expected_duration = 0.0
        if not bom_id or to_produce_qty <= 0.0:
            return expected_duration
        for bom_line_id in bom_id.bom_line_ids:
            workcenter_id = workcenters.get(bom_line_id.operation_id.id, False)
            if workcenter_id:
                expected_duration += self._get_duration_expected(bom_line_id.operation_id, workcenter_id, to_produce_qty)
        return expected_duration

    @api.model
    def _get_resource(self, workcenter_ids):
        resource_id = self.env['resource.calendar']
        if not workcenter_ids:
            return resource_id
        if len(workcenter_ids) == 1:
            return workcenter_ids[0].resource_calendar_id
        resources = set(workcenter_ids.mapped('resource_calendar_id'))
        if len(resources) == 1:
            return list(resources)[0]
        workorder_ids = self.env['mrp.workorder']
        for workcenter in workcenter_ids:
            workorder_id = self.env['mrp.workorder'].search([
                ('workcenter_id', '=', workcenter.id),
                ('date_planned_finished', '!=', False)
            ], order='date_planned_finished desc', limit=1)
            if not workorder_id:
                return workcenter.resource_calendar_id
            workorder_ids |= workorder_id
        return sorted(workorder_ids, key=lambda w: w.date_planned_finished)[0].workcenter_id.resource_calendar_id
            
    @api.model
    def _get_suggested_start_date(self, expected_end_date, expected_duration, resource_id, bom):
        workcenters = self._get_workcenter(bom)
        user_tz = self.tz()
        workorders = [{
            'start': convert_tz(o.date_planned_start, pytz.utc, user_tz),
            'finish': convert_tz(o.date_planned_finished, pytz.utc, user_tz),
            'duration': o.duration_expected
        } for o in workcenters.order_ids.filtered(lambda o: o.date_planned_start and o.date_planned_finished and o.date_planned_finished > o.date_planned_start)]

        duration_left = expected_duration
        attendances = resource_id.cycle_attendances(expected_end_date)
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
    def _get_suggested_end_date(self, suggested_start_date, expected_duration, resource_id):
        duration_left = expected_duration
        attendances = resource_id.cycle_attendances(suggested_start_date)

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
    def _get_estimated_date(self, bom_id, date_planned_start, qty):
        if not bom_id.bom_line_ids:
            raise ValidationError(_('Please set materials for %s' % bom_id.display_name))

        dt_object = convert_tz(date_planned_start, self.tz(), pytz.utc)

        start_date = max(dt_object, datetime.datetime.now())
        
        estimated_start_date = datetime.datetime.max
        estimated_end_date = datetime.datetime.min
        for bom_line_id in bom_id.bom_line_ids:
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
                from_date, to_date = workcenter._get_first_available_slot(start_date, duration_expected)

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
        
    def action_replenish(self, replenish_option, bom_ids):
        company = self.env.company
        branch = self.env.branch
        date_range = company._get_date_range()

        current_datetime = fields.Datetime.now()
        mps_values = self.get_production_schedule_view_state()

        mps_plan_ids = self.env['mrp.plan']
        mps_order_ids = self.env['mrp.production']

        plan_matrix_id = False
        if company.manufacturing_plan_conf:
            plan_matrix_id = self.env['mrp.plan']._default_approval_matrix()

        order_matrix_id = False
        if company.manufacturing_order_conf:
            order_matrix_id = self.env['mrp.production']._default_approval_matrix()

        for mps in mps_values:
            mps_id = str(mps['id'])
            if not bom_ids[mps_id]:
                continue

            product_id = self.env['product.product'].browse(mps['product_id'][0])
            bom = self.env['mrp.bom'].browse(int(bom_ids[mps_id]))

            if replenish_option == 'MP':
                product_qty = sum(o['to_replenish_qty'] for o in mps['forecast_ids'])
                plan_id = self.env['mrp.plan'].create({
                    'name': 'Replenish %s' % str(current_datetime),
                    'branch_id': branch.id,
                    'company_id': company.id,
                    'mps_product_id': product_id.id,
                    'mps_product_qty': product_qty,
                    'mps_bom_id': bom.id,
                    'mps_start_date': date_range[0][0],
                    'mps_end_date': date_range[-1][1],
                    'approval_matrix_id': plan_matrix_id,
                    'analytic_tag_ids': self.env['mrp.plan']._default_analytic_tags(company_id=company, branch_id=branch)
                })

                wizard = self.env['mrp.production.wizard'].with_context(
                    active_model='mrp.plan',
                    active_id=plan_id.id,
                    active_ids=plan_id.ids,
                ).create({
                    'plan_id': plan_id.id,
                    'line_ids': [(0, 0, {
                        'product_id': product_id.id,
                        'product_uom': bom.product_uom_id.id,
                        'product_qty': product_qty,
                        'no_of_mrp': 1,
                        'company': company.id,
                        'branch_id': branch.id,
                        'bom_id': bom.id
                    })]
                })
                wizard.confirm()
                mps_plan_ids |= plan_id

            else:
                order_ids = self.env['mrp.production']
                total_product_qty = 0.0
                for (forecast, (date_start, date_stop)) in zip(mps['forecast_ids'], date_range):
                    product_qty = forecast['to_replenish_qty']

                    if product_qty <= 0.0:
                        continue

                    scheduled_date = forecast['scheduled_date']
                    date_planned_start = convert_tz(scheduled_date, self.env.user.tz, pytz.utc)
                    date_planned_finished = date_planned_start + timedelta(hours=1)

                    order_values = {
                        'product_id': product_id.id,
                        'product_qty': product_qty,
                        'bom_id': bom.id,
                        'user_id': self.env.user.id,
                        'product_uom_id': product_id.uom_id.id,
                        'company_id': company.id,
                        'branch_id': branch.id,
                        'date_planned_start': date_planned_start,
                        'date_planned_finished': date_planned_finished,
                        'mps_start_date': date_start,
                        'mps_end_date': date_stop,
                        'approval_matrix_id': order_matrix_id
                    }

                    order_id = self.env['mrp.production'].create(order_values)
                    order_id.sudo().onchange_product_id()
                    order_id.sudo().onchange_branch()
                    order_id.sudo()._onchange_workorder_ids()
                    order_id.sudo()._onchange_move_raw()
                    order_id.sudo()._onchange_move_finished()
                    order_id.sudo().onchange_workorder_ids()
                    mps_order_ids |= order_id

        self.env['equip.mps.production'].create({
            'date': current_datetime,
            'plan_ids': [(6, 0, mps_plan_ids.ids)],
            'production_ids': [(6, 0, mps_order_ids.ids)],
        })

    def action_request(self, warehouse_id, bom_ids):
        mps_values = self.get_production_schedule_view_state()

        qty_dict = dict()
        for mps in mps_values:
            mps_id = str(mps['id'])
            if not bom_ids[mps_id]:
                continue

            total_qty = sum(forecast['to_replenish_qty'] for forecast in mps['forecast_ids']) 

            bom_id = self.env['mrp.bom'].browse(int(bom_ids[mps_id]))
            for bom_line in bom_id.bom_line_ids:
                workcenter = bom_line.operation_id._get_workcenter()
                material_id = bom_line.product_id.id
                location_id = workcenter.location_id.id

                ratio = bom_line.product_qty / bom_id.product_qty
                to_consume_qty = ratio * total_qty

                if material_id not in qty_dict:
                    qty_dict[material_id] = {location_id: to_consume_qty}
                else:
                    if location_id not in qty_dict[material_id]:
                        qty_dict[material_id][location_id] = to_consume_qty
                    else:
                        qty_dict[material_id][location_id] += to_consume_qty

        Location = self.env['stock.location']
        Product = self.env['product.product']
        line_ids = []
        for product_id, values in qty_dict.items():
            product = Product.browse(product_id)
            for location_id, to_consume_qty in values.items():
                location = Location.browse(location_id)
                warehouse = location.get_warehouse()
                res = product.with_context(warehouse_id=warehouse.id, location=location.id)._compute_quantities_dict(None, None, None)
                available_qty = res[product_id]['qty_available']
                to_request_qty = to_consume_qty - available_qty
                if to_request_qty > 0:
                    line_ids += [(0, 0, {
                        'description': product.display_name,
                        'product_id': product_id,
                        'uom_id': product.uom_id.id,
                        'qty': to_request_qty,
                        'qty_done': 0.0,
                        'destination_location': location_id,
                        'destination_warehouse_id': warehouse.id,
                        'state': 'draft'
                    })]
        
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        material_request_values = {
            'material_request_line_ids': line_ids,
            'destination_location': warehouse.lot_stock_id.id,
            'destination_warehouse_id': warehouse.id,
            'is_readonly_origin': True
        }

        wizard_id = self.env['material.request.wizard'].create(material_request_values)
        return wizard_id.id

    def bom_materials(self, selected_bom):
        material_avl = {}
        lst_of_materials = []

        bom = selected_bom['bom_material']
        uom = ''
        if 'uom' in selected_bom:
            uom = selected_bom['uom']
        materials = bom.bom_line_ids
        for rec in materials:
            material_lst = []
            material_lst.append(rec.product_id.display_name)
            material_lst.append(rec.product_qty)
            if uom:
                material_lst.append(uom)
            lst_of_materials.append(material_lst)
        material_avl[bom.id] = lst_of_materials
        return material_avl

    def get_selected_bom_material(self, bom):
        bom = int(bom)
        material = self.env['mrp.bom'].browse(bom)
        uom = material.product_uom_id.name
        bom_material = {'bom_material': material, 'uom': uom}
        return self.bom_materials(bom_material)

    def get_swo_data(self):
        if not self:
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
        self.env.cr.execute(query, [tuple(self.mapped('product_id').ids)])
        return {o[0]: {
            'product_min_qty': o[1],
            'product_max_qty': o[2],
            'run_rate_days': o[3] or 1
        } for o in self.env.cr.fetchall()}

    def get_sales_data(self, date_start, date_stop):
        self.ensure_one()
        query = """
        SELECT
            SUM(sol.product_uom_qty)
        FROM
            sale_order_line sol
        LEFT JOIN
            sale_order so
            ON (so.id = sol.order_id)
        WHERE
            sol.product_id = %s AND
            so.state = 'sale' AND
            sol.multiple_do_date_new >= %s AND
            sol.multiple_do_date_new <= %s AND
            so.warehouse_new_id = %s
        """
        self.env.cr.execute(query, [self.product_id.id, date_start, date_stop, self.warehouse_id.id])
        return self.env.cr.fetchall()[0][0]

    def get_production_schedule_view_state(self):
        read_fields = ['product_id']
        if self.env.user.has_group('stock.group_stock_multi_warehouses'):
            read_fields.append('warehouse_id')
        if self.env.user.has_group('uom.group_uom'):
            read_fields.append('product_uom_id')

        production_schedule_states = []
        for record in self:
            values = {'id': record.id}
            for field in read_fields:
                values[field] = (record[field].id, record[field].display_name)
            production_schedule_states += [values]
        production_schedule_states_by_id = {mps['id']: mps for mps in production_schedule_states}

        now = datetime.datetime.now().replace(second=0, microsecond=0)
        now = convert_tz(now, pytz.utc, self.tz())

        SWO = self.get_swo_data()
        date_ranges = {company.id: company._get_date_range() for company in self.mapped('company_id')}

        for production_schedule in self:
            company_id = production_schedule.company_id
            date_range = date_ranges[company_id.id]

            advance_stock_days = 1
            if company_id.manufacturing_period == 'week':
                advance_stock_days = 7
            elif company_id.manufacturing_period == 'month':
                today = fields.Date.today()
                advance_stock_days = monthrange(year=today.year, month=today.month)[1]

            production_schedule_state = production_schedule_states_by_id[production_schedule['id']]

            bom_id = production_schedule.bom_id
            bom_ids = production_schedule.bom_ids
            bom_ids_values = []
            for bom in bom_ids:
                bom_ids_values += [(bom.id, bom.display_name)]

            precision_digits = 2
            workcenter_ids = self._get_workcenter(bom_id)
            resource_id = self._get_resource(workcenter_ids)

            production_schedule_state.update({
                'company_id': [company_id.id, company_id.display_name],
                'bom_id': [bom_id.id, bom_id.display_name],
                'bom_ids': bom_ids_values,
                'precision_digits': precision_digits,
                'colspan': len(date_range) + 1,
                'workcenter_ids': [[w.id, w.display_name] for w in workcenter_ids],
                'resource_id': [resource_id.id, resource_id.display_name],
                'forecast_ids': []
            })
            
            next_on_hand = False
            previous_to_replenish_qty = False
            
            product_id = production_schedule.product_id
            warehouse_id = production_schedule.warehouse_id
            forecast_ids = production_schedule.forecast_ids
            for _iter, (date_start, date_stop) in enumerate(date_range):
                forecast_at_date = forecast_ids.filtered(lambda f: f.date == date_stop)
                forecasted_demand_edited = forecast_at_date.forecasted_demand_edited
                to_replenish_edited = forecast_at_date.to_replenish_edited
                scheduled_date_edited = forecast_at_date.scheduled_date_edited
                forecast_at_date_id = forecast_at_date.id

                if next_on_hand is False:
                    res = product_id.with_context(warehouse=warehouse_id.id, location=False)._compute_quantities_dict(None, None, None, to_date=date_stop)
                    on_hand_qty = res[product_id.id]['qty_available']
                else:
                    on_hand_qty = next_on_hand

                if previous_to_replenish_qty is not False:
                    on_hand_qty += previous_to_replenish_qty

                run_rate_days = SWO.get(product_id.id, {}).get('run_rate_days', 1.0)
                low_stock = SWO.get(product_id.id, {}).get('product_min_qty', 0.0)
                max_stock = SWO.get(product_id.id, {}).get('product_max_qty', 0.0)
                sales = production_schedule.get_sales_data(date_start, date_stop)

                if forecasted_demand_edited:
                    forecast_demand = forecast_at_date.forecasted_demand_qty
                else:
                    forecast_demand = (low_stock / run_rate_days) * advance_stock_days

                forecast_stock = on_hand_qty - forecast_demand

                if to_replenish_edited:
                    to_replenish_qty = forecast_at_date.to_replenish_qty
                else:
                    to_replenish_qty = 0.0
                    if forecast_stock < low_stock:
                        to_replenish_qty = max_stock - forecast_stock

                previous_to_replenish_qty = to_replenish_qty
                
                scheduled_date = False
                scheduled_end_date = False
                expected_end_date = self._get_expected_end_date(str(_iter), date_range, resource_id)
                expected_duration = self._get_expected_duration(bom_id, to_replenish_qty)
                if scheduled_date_edited:
                    scheduled_date = forecast_at_date.scheduled_date
                else:
                    if expected_end_date:
                        expected_end_date = convert_tz(expected_end_date, pytz.utc, self.tz())
                        scheduled_date = self._get_suggested_start_date(expected_end_date, expected_duration, resource_id, bom_id)
                        if scheduled_date:
                            scheduled_end_date = self._get_suggested_end_date(scheduled_date, expected_duration, resource_id)

                estimated_start_date = False
                estimated_end_date = False
                if scheduled_date:
                    try:
                        estimated_start_date, estimated_end_date = self._get_estimated_date(bom_id, scheduled_date, to_replenish_qty)
                    except UserError:
                        pass
                
                production_schedule_state['forecast_ids'] += [{
                    'date_from': date_start,
                    'date_to': date_stop,
                    'expected_end_date': expected_end_date,
                    'expected_duration': expected_duration,
                    'on_hand_qty': on_hand_qty,
                    'low_stock': low_stock,
                    'max_stock': max_stock,
                    'sales': sales,
                    'forecasted_demand': forecast_demand,
                    'forecasted_stock': forecast_stock,
                    'to_replenish_qty': to_replenish_qty,
                    'forecast_at_date_id': forecast_at_date_id,
                    'run_rate_days': run_rate_days,
                    'advanced_stock_days': advance_stock_days,
                    'scheduled_date': scheduled_date,
                    'scheduled_end_date': scheduled_end_date,
                    'estimated_date': estimated_start_date,
                    'estimated_end_date': estimated_end_date,
                    'forecasted_demand_edited': forecasted_demand_edited,
                    'to_replenish_edited': to_replenish_edited,
                    'scheduled_date_edited': scheduled_date_edited
                }]
                next_on_hand = forecast_stock

        return production_schedule_states

    def set_forecast_values(self, date_index, new_value, field):
        field_edited = field + '_edited'
        if field in ('forecasted_demand', 'to_replenish'):
            field_name = field + '_qty'
        else:
            new_value = convert_tz(new_value, self.env.user.tz, pytz.utc)
            field_name = field

        # Get the last date of current period
        self.ensure_one()
        date_start, date_stop = self.company_id._get_date_range()[date_index]
        existing_forecast = self.forecast_ids.filtered(
            lambda f: f.date == date_stop
        )

        if existing_forecast:
            existing_forecast[0].write({
                field_name: new_value,
                field_edited: True
            })
        else:
            existing_forecast.create({
                field_name: new_value,
                field_edited: True,
                'date': date_stop,
                'production_schedule_id': self.id
            })
        return True


class MrpProductForecast(models.Model):
    _name = 'equip.mrp.product.forecast'
    _order = 'date'
    _description = 'Product Forecast at Date'

    production_schedule_id = fields.Many2one('equip.mrp.production.schedule', required=True, ondelete='cascade')
    date = fields.Date('Date', required=True)

    forecasted_demand_qty = fields.Float('Forecasted Demand')
    to_replenish_qty = fields.Float('To Replenish')
    scheduled_date = fields.Datetime('Scheduled Date')

    forecasted_demand_edited = fields.Boolean('Forecasted Demand Edited Manually')
    to_replenish_edited = fields.Boolean('To Replenish Edited Manually')
    scheduled_date_edited = fields.Boolean('Scheduled Date Edited Manually')

