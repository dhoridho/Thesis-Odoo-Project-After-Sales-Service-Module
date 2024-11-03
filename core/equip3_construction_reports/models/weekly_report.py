from odoo import _, api, fields, models
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
import json


class ProjectWeeklyReport(models.Model):
    _name = 'project.progress.report'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Project Progress Report'

    name = fields.Char(string='Name', required=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, domain="[('primary_states','in', ('progress', 'completed'))]")
    contract_id = fields.Many2one('sale.order.const', string="Contract")
    job_estimate_id = fields.Many2one('job.estimate', string="BOQ")
    is_project_internal = fields.Boolean(string='Project Type', default=False)

    report_start_date = fields.Date(string='Report Start Date', required=True)
    report_end_date = fields.Date(string='Report End Date', required=True)
    completion = fields.Float(string='Actual Progress', store="1")
    # compute = '_get_completion_percentage'
    tag_ids = fields.Many2many('project.tags', string = "Tags")
    company_id = fields.Many2one('res.company', 'Company', readonly=True, index=True,
                                 default=lambda self: self.env.company)
    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                 domain=lambda self: [('id', 'in', self.env.branches.ids)])
    description = fields.Html(string = "Description")
    progress_history_ids = fields.One2many('progress.progress.report', 'progress_report')
    issue_history_ids = fields.One2many('issue.progress.report', 'progress_report')
    material_usage_ids = fields.One2many('material.usage','material_id',string="Material Usage Page")
    equipment_usage_ids = fields.One2many('equipment.usage','equipment_id',string="Equipment Usage Page")
    labour_usage_ids = fields.One2many('labour.usage','labour_id',string="Labour Usage Page")
    overhead_usage_ids = fields.One2many('over.head.usage','overhead_id',string="OverHead Usage Page")
    invoiced_progress = fields.Float(string='Invoiced Progress')
    scurve_report_ids = fields.One2many('scurve.report','scurve_id', string = 'Scurve')
    customer_claim_history_ids = fields.One2many('report.claim.history', 'report_id', string="Claim History Customer", domain=[('progressive_bill', '=', False)])
    subcon_claim_history_ids = fields.One2many('report.claim.history', 'report_id', string="Claim History Subcon", domain=[('progressive_bill', '=', True)])
    # Recently added code -----------
    total_usage = fields.Float(string='Total Usage', readonly=True, compute='_total_usage')
    total_material_usage = fields.Float(string='Total Material Usage', readonly=True, compute = '_total_material_usage')
    total_equipment_usage = fields.Float(string='Total Equipment Usage', readonly=True, compute = '_total_equipment_usage')
    total_labour_usage = fields.Float(string='Total Labour Usage', readonly=True, compute = '_total_labour_usage')
    total_overhead_usage = fields.Float(string='Total Overhaed Usage', readonly=True, compute = '_total_overhead_usage')
    add_description = fields.Boolean(string='Add Description', dafault=False)
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id','in',self.env.user.project_ids.ids))
        
        return super(ProjectWeeklyReport, self).search_read(domain, fields, offset, limit, order)
  
    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                    }
    

    @api.depends('material_usage_ids.quantity', 'material_usage_ids.sale_price')
    def _total_material_usage(self):
        for res in self:
            m_qty_sp = 0.00
            summition_lst = []
            for line in res.material_usage_ids:
                if line and line.quantity and line.sale_price:
                    m_qty_sp = line.quantity * line.sale_price
                    summition_lst.append(float(m_qty_sp))
            res.total_material_usage = sum(summition_lst)

    @api.depends('equipment_usage_ids.quantity', 'equipment_usage_ids.sale_price')
    def _total_equipment_usage(self):
        for res in self:
            m_qty_sp = 0.00
            summition_lst = []
            for line in res.equipment_usage_ids:
                if line and line.quantity and line.sale_price:
                    m_qty_sp = line.quantity * line.sale_price
                    summition_lst.append(float(m_qty_sp))
            res.total_equipment_usage = sum(summition_lst)

    @api.depends('labour_usage_ids.quantity', 'labour_usage_ids.sale_price')
    def _total_labour_usage(self):
        for res in self:
            m_qty_sp = 0.00
            summition_lst = []
            for line in res.labour_usage_ids:
                if line and line.quantity and line.sale_price:
                    m_qty_sp = line.quantity * line.sale_price
                    summition_lst.append(float(m_qty_sp))
            res.total_labour_usage = sum(summition_lst)

    @api.depends('overhead_usage_ids.quantity', 'overhead_usage_ids.sale_price')
    def _total_overhead_usage(self):
        for res in self:
            m_qty_sp = 0.00
            summition_lst = []
            for line in res.overhead_usage_ids:
                if line and line.quantity and line.sale_price:
                    m_qty_sp = line.quantity * line.sale_price
                    summition_lst.append(float(m_qty_sp))
            res.total_overhead_usage = sum(summition_lst)

    @api.depends('total_material_usage', 'total_equipment_usage', 'total_labour_usage', 'total_overhead_usage')
    def _total_usage(self):
        for res in self:
            total_usage = 0.00
            total_usage = res.total_material_usage + res.total_equipment_usage + res.total_labour_usage + res.total_overhead_usage
            res.total_usage = total_usage


    @api.onchange('project_id', 'contract_id')
    def get_project_completion_percentage(self):
        completion = 0
        for rec in self:
            name = rec.name
            project = rec.project_id
            contract = rec.contract_id
            branch = rec.branch_id
            start = rec.report_start_date
            end = rec.report_end_date
            tag = rec.tag_ids
            if project and contract:
                for line in project.project_completion_ids:
                    if contract.id == line.name.id:
                        completion =+ line.project_completion
                self.write({
                    'completion' : completion,
                    'invoiced_progress': rec._get_invoiced_progress(),
                    'name' : name,
                    'project_id' : project.id,
                    'contract_id': contract.id,
                    'branch_id' : branch.id,
                    'report_start_date': start,
                    'report_end_date' : end,
                    'tag_ids': tag.ids,
                })

    @api.onchange('project_id', 'job_estimate_id')
    def get_project_completion_percentage_internal(self):
        completion = 0
        for rec in self:
            project = rec.project_id
            job_estimate = rec.job_estimate_id
            name = rec.name
            branch = rec.branch_id
            start = rec.report_start_date
            end = rec.report_end_date
            tag = rec.tag_ids
            if project and job_estimate:
                for line in project.project_completion_ids:
                    if job_estimate.id == line.name.id:
                        completion =+ line.project_completion
                self.write({
                    'completion' : completion,
                    'invoiced_progress': rec._get_invoiced_progress(),
                    'name' : name,
                    'project_id' : project.id,
                    'job_estimate_id': job_estimate.id,
                    'branch_id' : branch.id,
                    'report_start_date': start,
                    'report_end_date' : end,
                    'tag_ids': tag.ids,
                })

    def _get_invoiced_progress(self):
        progress = 0
        for rec in self:
            claim = rec.env['progressive.claim'].search([('contract_parent', '=', rec.contract_id.id), ('project_id', '=', rec.project_id.id)])
            progress = claim.invoiced_progress
            return progress

    def get_report(self):
        serial_num = 0
        self.progress_history_ids = False
        self.issue_history_ids = False
        self.material_usage_ids = False
        self.equipment_usage_ids = False
        self.labour_usage_ids = False
        self.overhead_usage_ids = False
        self.customer_claim_history_ids = False
        self.subcon_claim_history_ids = False
        #    to fill progress history notebook page
        history_ids = self.env['progress.history'].search([
            ('project_id', '=', self.project_id.id),
            ('sale_order', '=', self.contract_id.id),
            ('progress_start_date_new','>=', self.report_start_date),
            ('progress_end_date_new', '<=',self.report_end_date)])
        history_data = []
        for line in history_ids:
            vals = {}
            serial_num += 1
            vals["sr_no"] = serial_num
            vals["job_order"] = line.work_order.id
            vals["stage_new"] = line.stage_new.id
            vals["progress_start_date_new"] = line.progress_start_date_new
            vals["progress_end_date_new"] = line.progress_end_date_new
            vals["date_create"] = line.date_create
            vals["create_by"] = line.create_by.id
            vals["progress"] = line.progress
            vals["progress_summary"] = line.progress_summary
            history_data.append((0,0,vals))
        self.progress_history_ids = history_data

        # new
        alr_exist = set()
        for history in history_ids:
            alr_exist.add(history.id)
        histories = self.env['progress.history'].search([
            ('project_id', '=', self.project_id.id),
            ('sale_order', '=', self.contract_id.id),
            ('progress_end_date_new', '<=',self.report_end_date),
            ('progress_end_date_new', '>=',self.report_start_date)])
        new_history_data = []
        for h in histories:
            if h.id not in alr_exist:
                vals = {}
                serial_num += 1
                vals["sr_no"] = serial_num
                vals["job_order"] = h.work_order.id
                vals["stage_new"] = h.stage_new.id
                vals["progress_start_date_new"] = h.progress_start_date_new
                vals["progress_end_date_new"] = h.progress_end_date_new
                vals["date_create"] = h.date_create
                vals["create_by"] = h.create_by.id
                vals["progress"] = h.progress
                vals["progress_summary"] = h.progress_summary
                new_history_data.append((0,0,vals))
        self.progress_history_ids = new_history_data

        #    to fill issues history notebook page
        issue_ids = self.env['project.issue'].search([
            ('project_id', '=', self.project_id.id),
            ('contract_id', '=', self.contract_id.id),
            ('create_date', '>=', self.report_start_date),
            ('create_date', '<=', self.report_end_date)])
        issue_data = []
        for record in issue_ids:
            issue_vals = {}
            serial_num += 1
            issue_vals["sr_no"] = serial_num
            issue_vals["issue_id"] = record.id
            issue_vals["name"] = record.name
            issue_vals["priority"] = record.priority
            issue_vals["date_create"] = record.create_date
            issue_vals["issue_stage_id"] = record.issue_stage_id.id
            issue_vals["issue_found_date"] = record.issue_found_date
            issue_vals["issue_solved_date"] = record.issue_solved_date
            issue_data.append((0, 0, issue_vals))
        self.issue_history_ids = issue_data

        # new
        exist_issue = set()
        for issue in issue_ids:
            exist_issue.add(issue.id)
        issue_new_data = []
        issue_found_ids = self.env['project.issue'].search([
            ('project_id', '=', self.project_id.id),
            ('contract_id', '=', self.contract_id.id),
            ('issue_found_date', '>=', self.report_start_date),
            ('issue_found_date', '<=', self.report_end_date)])
        issue_solved_ids = self.env['project.issue'].search([
            ('project_id', '=', self.project_id.id),
            ('contract_id', '=', self.contract_id.id),
            ('issue_solved_date', '>=', self.report_start_date),
            ('issue_solved_date', '<=', self.report_end_date)])
        issues_data = list(issue_found_ids)
        issues_data.extend(issue_solved_ids)
        for record in issues_data:
            if record.id not in exist_issue:
                exist_issue.add(record.id)
                issue_vals = {}
                serial_num += 1
                issue_vals["sr_no"] = serial_num
                issue_vals["issue_id"] = record.id
                issue_vals["name"] = record.name
                issue_vals["priority"] = record.priority
                issue_vals["date_create"] = record.create_date
                issue_vals["issue_stage_id"] = record.issue_stage_id.id
                issue_vals["issue_found_date"] = record.issue_found_date
                issue_vals["issue_solved_date"] = record.issue_solved_date
                issue_new_data.append((0, 0, issue_vals))
        self.issue_history_ids = issue_new_data

        # to fill labour usage tab
        labour_serial_num, material_serial_num, equipment_serial_num, overhead_serial_num = 0, 0, 0, 0
        usage_ids = self.env['stock.scrap.request'].search([
            ('project', '=', self.project_id.id),
            ('schedule_date', '>=', self.report_start_date),
            ('schedule_date', '<=', self.report_end_date)])
        labour_data , material_data,overhead_data,equipment_data = [] , [] , [], []
        for record in usage_ids:
            if record.material_type == 'labour':
                for scrab in record.scrap_ids:
                    labour_vals = {}
                    labour_serial_num += 1
                    labour_vals["sr_no"] = labour_serial_num
                    labour_vals["reference"] = record.name
                    labour_vals["warehouse_id"] = record.warehouse_id.id
                    labour_vals["product_id"] = scrab.product_id.id
                    labour_vals["quantity"] = scrab.scrap_qty
                    labour_vals["sale_price"] = scrab.sale_price
                    labour_vals["analytic_groups_ids"] = [(6,0,record.analytic_tag_ids.ids)]
                    labour_vals["created_on"] = record.create_date
                    labour_vals["project_budget"] = record.project_budget.id
                    labour_vals["job_order_id"] = record.work_orders.id
                    labour_vals["responsible_id"] = record.responsible_id.id
                    labour_vals["usage_type_id"] = record.scrap_type.id
                    labour_vals["schedule_date"] = record.schedule_date
                    labour_vals["company_id"] = record.company_id.id
                    labour_vals["branch_id"] = record.branch_id.id
                    labour_vals["source_location_id"] = scrab.location_id.id
                    labour_vals["project_scope_id"] = scrab.project_scope.id
                    labour_vals["section_id"] = scrab.section.id
                    labour_vals["variable_id"] = scrab.variable.id
                    labour_vals["group_of_product_id"] = scrab.group_of_product.id
                    labour_vals["budget_quantity"] = scrab.budget_qty
                    labour_vals["unit_of_measure_id"] = scrab.product_uom_id.id
                    labour_vals["lot_serial_id"] = scrab.lot_id.id
                    labour_vals["package_id"] = scrab.package_id.id
                    labour_vals["owner_id"] = scrab.owner_id.id
                    labour_vals["scrap_reference"] = scrab.name
                    labour_vals["state"] = record.state
                    labour_data.append((0, 0, labour_vals))

            elif record.material_type == 'material':
                for materials in record.scrap_ids:
                    material_vals = {}
                    material_serial_num += 1
                    material_vals["sr_no"] = material_serial_num
                    material_vals["reference"] = record.name
                    material_vals["usage_name"] = materials.scrap_id.scrap_request_name
                    material_vals["warehouse_id"] = record.warehouse_id.id
                    material_vals["product_id"] = materials.product_id.id
                    material_vals["quantity"] = materials.scrap_qty
                    material_vals["sale_price"] = materials.sale_price
                    material_vals["analytic_groups_ids"] = [(6, 0, record.analytic_tag_ids.ids)]
                    material_vals["created_on"] = record.create_date
                    material_vals["project_budget"] = record.project_budget.id
                    material_vals["job_order_id"] = record.work_orders.id
                    material_vals["responsible_id"] = record.responsible_id.id
                    material_vals["usage_type_id"] = record.scrap_type.id
                    material_vals["schedule_date"] = record.schedule_date
                    material_vals["company_id"] = record.company_id.id
                    material_vals["branch_id"] = record.branch_id.id
                    material_vals["source_location_id"] = materials.location_id.id
                    material_vals["project_scope_id"] = materials.project_scope.id
                    material_vals["section_id"] = materials.section.id
                    material_vals["variable_id"] = materials.variable.id
                    material_vals["group_of_product_id"] = materials.group_of_product.id
                    material_vals["budget_quantity"] = materials.budget_qty
                    material_vals["unit_of_measure_id"] = materials.product_uom_id.id
                    material_vals["lot_serial_id"] = materials.lot_id.id
                    material_vals["package_id"] = materials.package_id.id
                    material_vals["owner_id"] = materials.owner_id.id
                    material_vals["scrap_reference"] = materials.name
                    material_vals["state"] = record.state
                    material_data.append((0, 0, material_vals))

            elif record.material_type == 'equipment':
                for equipments in record.scrap_ids:
                    equipment_vals = {}
                    equipment_serial_num += 1
                    equipment_vals["sr_no"] = equipment_serial_num
                    equipment_vals["reference"] = record.name
                    equipment_vals["usage_name"] = equipments.scrap_id.scrap_request_name
                    equipment_vals["warehouse_id"] = record.warehouse_id.id
                    equipment_vals["product_id"] = equipments.product_id.id
                    equipment_vals["quantity"] = equipments.scrap_qty
                    equipment_vals["sale_price"] = equipments.sale_price
                    equipment_vals["analytic_groups_ids"] = [(6, 0, record.analytic_tag_ids.ids)]
                    equipment_vals["created_on"] = record.create_date
                    equipment_vals["project_budget"] = record.project_budget.id
                    equipment_vals["job_order_id"] = record.work_orders.id
                    equipment_vals["responsible_id"] = record.responsible_id.id
                    equipment_vals["usage_type_id"] = record.scrap_type.id
                    equipment_vals["schedule_date"] = record.schedule_date
                    equipment_vals["company_id"] = record.company_id.id
                    equipment_vals["branch_id"] = record.branch_id.id
                    equipment_vals["source_location_id"] = equipments.location_id.id
                    equipment_vals["project_scope_id"] = equipments.project_scope.id
                    equipment_vals["section_id"] = equipments.section.id
                    equipment_vals["variable_id"] = equipments.variable.id
                    equipment_vals["group_of_product_id"] = equipments.group_of_product.id
                    equipment_vals["budget_quantity"] = equipments.budget_qty
                    equipment_vals["unit_of_measure_id"] = equipments.product_uom_id.id
                    equipment_vals["lot_serial_id"] = equipments.lot_id.id
                    equipment_vals["package_id"] = equipments.package_id.id
                    equipment_vals["owner_id"] = equipments.owner_id.id
                    equipment_vals["scrap_reference"] = equipments.name
                    equipment_vals["state"] = record.state
                    equipment_data.append((0, 0, equipment_vals))

            elif record.material_type == 'overhead':
                for overheads in record.scrap_ids:
                    overhead_vals = {}
                    overhead_serial_num += 1
                    overhead_vals["sr_no"] = overhead_serial_num
                    overhead_vals["reference"] = record.name
                    overhead_vals["usage_name"] = overheads.scrap_id.scrap_request_name
                    overhead_vals["warehouse_id"] = record.warehouse_id.id
                    overhead_vals["product_id"] = overheads.product_id.id
                    overhead_vals["quantity"] = overheads.scrap_qty
                    overhead_vals["sale_price"] = overheads.sale_price
                    overhead_vals["analytic_groups_ids"] = [(6, 0, record.analytic_tag_ids.ids)]
                    overhead_vals["created_on"] = record.create_date
                    overhead_vals["project_budget"] = record.project_budget.id
                    overhead_vals["job_order_id"] = record.work_orders.id
                    overhead_vals["responsible_id"] = record.responsible_id.id
                    overhead_vals["usage_type_id"] = record.scrap_type.id
                    overhead_vals["schedule_date"] = record.schedule_date
                    overhead_vals["company_id"] = record.company_id.id
                    overhead_vals["branch_id"] = record.branch_id.id
                    overhead_vals["source_location_id"] = overheads.location_id.id
                    overhead_vals["project_scope_id"] = overheads.project_scope.id
                    overhead_vals["section_id"] = overheads.section.id
                    overhead_vals["variable_id"] = overheads.variable.id
                    overhead_vals["group_of_product_id"] = overheads.group_of_product.id
                    overhead_vals["budget_quantity"] = overheads.budget_qty
                    overhead_vals["unit_of_measure_id"] = overheads.product_uom_id.id
                    overhead_vals["lot_serial_id"] = overheads.lot_id.id
                    overhead_vals["package_id"] = overheads.package_id.id
                    overhead_vals["owner_id"] = overheads.owner_id.id
                    overhead_vals["scrap_reference"] = overheads.name
                    overhead_vals["state"] = record.state
                    overhead_data.append((0, 0, overhead_vals))

        progressive_claim_customer = self.env['progressive.claim'].search(
            [('contract_parent', '=', self.contract_id.id), ('progressive_bill', '=', False)])
        progressive_claim_subcon = self.env['progressive.claim'].search(
            [('contract_parent_po', '=', self.contract_id.id), ('progressive_bill', '=', True)])

        customer_claim_history_data = []
        for claim in progressive_claim_customer:
            i = 0
            for history in claim.claim_ids:
                if self.report_start_date <= history.date <= self.report_end_date:
                    customer_claim_history_data.append((0, 0, {
                        'sr_no': i + 1,
                        'report_id': self.id,
                        'claim_id': progressive_claim_customer.id,
                        'date': history.date,
                        'claim_name': history.claim_name,
                        'claim_for': history.claim_for,
                        'progressline': history.progressline,
                        'gross_amount': history.gross_amount,
                        'dp_deduction': history.dp_deduction,
                        'retention_deduction': history.retention_deduction,
                        'amount_deduction': history.amount_deduction,
                        'paid_invoice': history.paid_invoice,
                        'amount_untaxed': history.amount_untaxed,
                        'tax_id': history.tax_id.ids,
                        'tax_amount': history.tax_amount,
                        'amount_invoice': history.amount_invoice,
                        'amount_claim': history.amount_claim,
                        'remaining_amount': history.remaining_amount,
                        'invoice_status': history.invoice_status,
                        'payment_status': history.payment_status,
                        'progressive_bill': False,
                    }))
                    i += 1

        subcon_claim_history_data = []
        for claim in progressive_claim_subcon:
            i = 0
            for history in claim.claim_ids:
                if self.report_start_date <= history.date <= self.report_end_date:
                    subcon_claim_history_data.append((0, 0, {
                        'sr_no': i + 1,
                        'report_id': self.id,
                        'claim_id': progressive_claim_subcon.id,
                        'date': history.date,
                        'claim_name': history.claim_name,
                        'claim_for': history.claim_for,
                        'progressline': history.progressline,
                        'gross_amount': history.gross_amount,
                        'dp_deduction': history.dp_deduction,
                        'retention_deduction': history.retention_deduction,
                        'amount_deduction': history.amount_deduction,
                        'paid_invoice': history.paid_invoice,
                        'amount_untaxed': history.amount_untaxed,
                        'tax_id': history.tax_id.ids,
                        'tax_amount': history.tax_amount,
                        'amount_invoice': history.amount_invoice,
                        'amount_claim': history.amount_claim,
                        'remaining_amount': history.remaining_amount,
                        'invoice_status': history.invoice_status,
                        'payment_status': history.payment_status,
                        'progressive_bill': True,
                    }))
                    i += 1

        self.equipment_usage_ids = equipment_data
        self.material_usage_ids = material_data
        self.overhead_usage_ids = overhead_data
        self.labour_usage_ids = labour_data
        self.customer_claim_history_ids = customer_claim_history_data
        self.subcon_claim_history_ids = subcon_claim_history_data
        self.create_line_scurve()

    def send_cost_scurve(self, job_cost_sheet, project_budget):
        return {
            'name': 'Plan vs Actual Cost',
            'method': 'cost',
            'job_cost_sheet': job_cost_sheet.id,
            'project_budget': project_budget.ids
        }

    def send_progress_scurve(self, job_cost_sheet, project_budget):
        return {
            'name': 'Plan vs Actual Progress',
            'method': 'progress',
            'job_cost_sheet': job_cost_sheet.id,
            'project_budget': project_budget.ids
        }

    def send_cvp_scurve(self, job_cost_sheet, project_budget):
        return {
            'name': 'Cost Progress',
            'method': 'cvp',
            'job_cost_sheet': job_cost_sheet.id,
            'project_budget': project_budget.ids
        }

    def send_all_scurve(self, job_cost_sheet, project_budget):
        return {
            'name': 'Purchased vs Transferred vs Used Budget',
            'method': 'all',
            'job_cost_sheet': job_cost_sheet.id,
            'project_budget': project_budget.ids
        }

    def send_pa_scurve(self, job_cost_sheet, project_budget):
        return {
            'name': 'Plan and Actual Cost vs Progress',
            'method': 'pa_costprog',
            'job_cost_sheet': job_cost_sheet.id,
            'project_budget': project_budget.ids
        }

    def create_line_scurve(self):
        method = ['cost', 'progress', 'cvp', 'pa_costprog', 'all']
        self.scurve_report_ids = [(5, 0, 0)]
        line = [(5, 0, 0)]
        job_cost_sheet = False
        project_budget = False
        for res in self:
            for proj in res.project_id:
                job_cost_sheet = res.env['job.cost.sheet'].search([('project_id', '=', proj.id), ('state', 'not in', ['cancelled','reject','revised'])],limit=1)
                project_budget = res.env['project.budget'].search([('project_id', '=', proj.id)])
            for log in method:
                if log == 'cost':
                    line.append((0, 0, res.send_cost_scurve(job_cost_sheet, project_budget)))
                elif log == 'progress':
                    line.append((0, 0, res.send_progress_scurve(job_cost_sheet, project_budget)))
                elif log == 'cvp':
                    line.append((0, 0, res.send_cvp_scurve(job_cost_sheet, project_budget)))
                elif log == 'all':
                    line.append((0, 0, res.send_all_scurve(job_cost_sheet, project_budget)))
                else:
                    line.append((0, 0, res.send_pa_scurve(job_cost_sheet, project_budget)))
            res.scurve_report_ids = line
            for scurve in res.scurve_report_ids:
                scurve._initiate_s_curve()

    # @api.onchange('report_start_date')
    # def start_date_after_end_date(self):
    #     if self.report_start_date > self.report_end_date:
    #         raise ValidationError(_("Report Start Date is after Report End Date. Please re-set the Report Start Date"))

    # @api.onchange('report_start_date', 'report_end_date')
    # def onchange_date(self):
    #     for rec in self:
    #         if rec.report_start_date > rec.report_end_date:
    #             raise UserError(_('Report end date should be after report start date.'))

    @api.constrains('report_start_date', 'report_end_date')
    def constrains_date(self):
        for rec in self:
            if rec.report_start_date != False and rec.report_end_date != False:
                if rec.report_start_date > rec.report_end_date:
                    raise ValidationError(_('Report end date should be after report start date.'))
            if rec.project_id.act_start_date:
                if rec.report_start_date < rec.project_id.act_start_date:
                    raise ValidationError(_('Report start date should be after the project actual start date.'))
            else:
                if rec.report_start_date < rec.project_id.start_date:
                    raise ValidationError(_('Report start date should be after the project plan start date.'))
            if rec.project_id.act_start_date and rec.project_id.act_end_date:
                if rec.report_start_date < rec.project_id.act_start_date or rec.report_end_date > rec.project_id.act_end_date:
                    raise ValidationError(_("The report dates of the progress are not in between the project's planned dates. Please re-set the report dates"))

class ProgressWeeklyReport(models.Model):
    _name = 'progress.progress.report'
    _description = 'Project Progress Report'
    _order = 'sequence'
    _check_company_auto = True

    progress_report = fields.Many2one('project.progress.report', string="Report ID")
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_id = fields.Many2one(related="progress_report.project_id", string='Project')
    contract_id = fields.Many2one(related="progress_report.contract_id", string='Contract')
    stage_new = fields.Many2one('project.stage.const', string="Stage")
    job_order = fields.Many2one('project.task', string='Job Order')
    date_create = fields.Datetime(string="Created date")
    create_by = fields.Many2one('res.users', string="Created By")
    progress = fields.Float(string="Progress (%)")
    progress_summary = fields.Text(string='Progress Summary')
    progress_start_date_new = fields.Datetime(string='Progress Start Date')
    progress_end_date_new = fields.Datetime(string='Progress End Date')
    report_start_date = fields.Date(string='Report Start Date', related="progress_report.report_start_date")
    report_end_date = fields.Date(string='Report End Date', related="progress_report.report_end_date")
    company_id = fields.Many2one(string='Company', related="progress_report.company_id")
    branch_id = fields.Many2one(string="Branch", related="progress_report.branch_id")

    # def progress_report(self):


    @api.depends('progress_report.progress_history_ids', 'progress_report.progress_history_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            # line.job_order =
            for l in line.progress_report.progress_history_ids:
                no += 1
                l.sr_no = no


class IssueWeeklyReport(models.Model):
    _name = 'issue.progress.report'
    _description = 'Issue Progress Report'
    _order = 'sequence'
    _check_company_auto = True

    progress_report = fields.Many2one('project.progress.report', string="Report ID")
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_id = fields.Many2one(related="progress_report.project_id", string='Project')
    contract_id = fields.Many2one(related="progress_report.contract_id", string='Contract')
    report_start_date = fields.Date(string='Report Start Date', related="progress_report.report_start_date")
    report_end_date = fields.Date(string='Report End Date', related="progress_report.report_end_date")
    issue_found_date = fields.Date(string="FOUND DATE")
    issue_solved_date = fields.Date(string='Solved Date')
    company_id = fields.Many2one(string='Company', related="progress_report.company_id")
    branch_id = fields.Many2one(string="Branch", related="progress_report.branch_id")
    issue_id = fields.Many2one('project.issue', string="Issue ID")
    name = fields.Char(string="Issue")
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High')
        ], string='Priority')
    issue_stage_id = fields.Many2one('issue.stage', string='Issue Stage')
    date_create = fields.Datetime(string="Created date")

    @api.depends('progress_report.issue_history_ids', 'progress_report.issue_history_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.progress_report.issue_history_ids:
                no += 1
                l.sr_no = no

class MaterialUsage(models.Model):
    _name = 'material.usage'
    _description = "Material Usage"

    sr_no = fields.Integer(string="NO.")
    reference = fields.Char(string="REFERENCE")
    usage_name = fields.Char(string="NAME")
    warehouse_id = fields.Many2one('stock.warehouse',string="WAREHOUSE")
    product_id = fields.Many2one('product.product',string="PRODUCT")
    quantity = fields.Integer(string="QUANTITY")
    sale_price = fields.Float(string="SALE PRICE")
    analytic_groups_ids = fields.Many2many('account.analytic.tag',string="ANALYTIC GROUPS")
    created_on = fields.Datetime(string="CREATED ON")
    expiry_date = fields.Datetime(string="EXPIRY DATE")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled')
    ], string='State')
    project_budget = fields.Many2one('project.budget',string="PROJECT BUDGET")
    job_order_id = fields.Many2one('project.task',string="JOB ORDER")
    responsible_id = fields.Many2one('res.users',string="RESPONSIBLE")
    usage_type_id = fields.Many2one('usage.type',string="USAGE TYPE")
    schedule_date = fields.Datetime(string="SCHEDULE DATE")
    company_id = fields.Many2one('res.company',string="COMPANY")
    branch_id = fields.Many2one('res.branch',string="BRANCH")
    source_location_id = fields.Many2one('stock.location',string="SOURCE LOCATION")
    project_scope_id = fields.Many2one('project.scope.line',string="PROJECT SCOPE")
    section_id = fields.Many2one('section.line',string="SECTION")
    variable_id = fields.Many2one('variable.template',string="VARIABLE")
    group_of_product_id = fields.Many2one('group.of.product',string="GROUP OF PRODUCT")
    budget_quantity = fields.Float(string="BUDEGT QUANTITY")
    unit_of_measure_id = fields.Many2one('uom.uom',string="UNIT OF MEASURE")
    lot_serial_id = fields.Many2one('stock.production.lot',string="LOT/SERIAL")
    package_id = fields.Many2one('stock.quant.package',string="PACKAGE")
    owner_id = fields.Many2one('res.partner',string="OWNER")
    scrap_reference = fields.Char(string="SCRAP REFERENCE")

    material_id = fields.Many2one('project.progress.report',string="material reference")

class EquipmentUsage(models.Model):
    _name = 'equipment.usage'
    _description = "Equipment Usage"

    sr_no = fields.Integer(string="NO.")
    reference = fields.Char(string="REFERENCE")
    usage_name = fields.Char(string="NAME")
    warehouse_id = fields.Many2one('stock.warehouse',string="WAREHOUSE")
    product_id = fields.Many2one('product.product',string="PRODUCT")
    quantity = fields.Integer(string="QUANTITY")
    sale_price = fields.Float(string="SALE PRICE")
    analytic_groups_ids = fields.Many2many('account.analytic.tag',string="ANALYTIC GROUPS")
    created_on = fields.Datetime(string="CREATED ON")
    expiry_date = fields.Datetime(string="EXPIRY DATE")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled')
    ], string='State')
    project_budget = fields.Many2one('project.budget',string="PROJECT BUDGET")
    job_order_id = fields.Many2one('project.task',string="JOB ORDER")
    responsible_id = fields.Many2one('res.users',string="RESPONSIBLE")
    usage_type_id = fields.Many2one('usage.type',string="USAGE TYPE")
    schedule_date = fields.Datetime(string="SCHEDULE DATE")
    company_id = fields.Many2one('res.company',string="COMPANY")
    branch_id = fields.Many2one('res.branch',string="BRANCH")
    source_location_id = fields.Many2one('stock.location',string="SOURCE LOCATION")
    project_scope_id = fields.Many2one('project.scope.line',string="PROJECT SCOPE")
    section_id = fields.Many2one('section.line',string="SECTION")
    variable_id = fields.Many2one('variable.template',string="VARIABLE")
    group_of_product_id = fields.Many2one('group.of.product',string="GROUP OF PRODUCT")
    budget_quantity = fields.Float(string="BUDEGT QUANTITY")
    unit_of_measure_id = fields.Many2one('uom.uom',string="UNIT OF MEASURE")
    lot_serial_id = fields.Many2one('stock.production.lot',string="LOT/SERIAL")
    package_id = fields.Many2one('stock.quant.package',string="PACKAGE")
    owner_id = fields.Many2one('res.partner',string="OWNER")
    scrap_reference = fields.Char(string="SCRAP REFERENCE")

    equipment_id = fields.Many2one('project.progress.report',string="Equipment reference")


class LabourUsage(models.Model):
    _name = 'labour.usage'
    _description = "Labour Usage"

    sr_no = fields.Integer(string="NO.")
    reference = fields.Char(string="REFERENCE")
    usage_name = fields.Char(string="NAME")
    warehouse_id = fields.Many2one('stock.warehouse', string="WAREHOUSE")
    product_id = fields.Many2one('product.product', string="PRODUCT")
    quantity = fields.Integer(string="QUANTITY")
    sale_price = fields.Float(string="SALE PRICE")
    analytic_groups_ids = fields.Many2many('account.analytic.tag', string="ANALYTIC GROUPS")
    created_on = fields.Datetime(string="CREATED ON")
    expiry_date = fields.Datetime(string="EXPIRY DATE")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled')
    ], string='State')
    project_budget = fields.Many2one('project.budget',string="PROJECT BUDGET")
    job_order_id = fields.Many2one('project.task', string="JOB ORDER")
    responsible_id = fields.Many2one('res.users', string="RESPONSIBLE")
    usage_type_id = fields.Many2one('usage.type', string="USAGE TYPE")
    schedule_date = fields.Datetime(string="SCHEDULE DATE")
    company_id = fields.Many2one('res.company', string="COMPANY")
    branch_id = fields.Many2one('res.branch', string="BRANCH")
    source_location_id = fields.Many2one('stock.location', string="SOURCE LOCATION")
    project_scope_id = fields.Many2one('project.scope.line', string="PROJECT SCOPE")
    section_id = fields.Many2one('section.line', string="SECTION")
    variable_id = fields.Many2one('variable.template', string="VARIABLE")
    group_of_product_id = fields.Many2one('group.of.product', string="GROUP OF PRODUCT")
    budget_quantity = fields.Float(string="BUDEGT QUANTITY")
    unit_of_measure_id = fields.Many2one('uom.uom', string="UNIT OF MEASURE")
    lot_serial_id = fields.Many2one('stock.production.lot', string="LOT/SERIAL")
    package_id = fields.Many2one('stock.quant.package', string="PACKAGE")
    owner_id = fields.Many2one('res.partner', string="OWNER")
    scrap_reference = fields.Char(string="SCRAP REFERENCE")

    labour_id = fields.Many2one('project.progress.report', string="Labour reference")


class OverHeadUsage(models.Model):
    _name = 'over.head.usage'
    _description = "OverHead Usage"

    sr_no = fields.Integer(string="NO.")
    reference = fields.Char(string="REFERENCE")
    usage_name = fields.Char(string="NAME")
    warehouse_id = fields.Many2one('stock.warehouse', string="WAREHOUSE")
    product_id = fields.Many2one('product.product', string="PRODUCT")
    quantity = fields.Integer(string="QUANTITY")
    sale_price = fields.Float(string="SALE PRICE")
    analytic_groups_ids = fields.Many2many('account.analytic.tag', string="ANALYTIC GROUPS")
    created_on = fields.Datetime(string="CREATED ON")
    expiry_date = fields.Datetime(string="EXPIRY DATE")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled')
    ], string='State')
    project_budget = fields.Many2one('project.budget',string="PROJECT BUDGET")
    job_order_id = fields.Many2one('project.task', string="JOB ORDER")
    responsible_id = fields.Many2one('res.users', string="RESPONSIBLE")
    usage_type_id = fields.Many2one('usage.type', string="USAGE TYPE")
    schedule_date = fields.Datetime(string="SCHEDULE DATE")
    company_id = fields.Many2one('res.company', string="COMPANY")
    branch_id = fields.Many2one('res.branch', string="BRANCH")
    source_location_id = fields.Many2one('stock.location', string="SOURCE LOCATION")
    project_scope_id = fields.Many2one('project.scope.line', string="PROJECT SCOPE")
    section_id = fields.Many2one('section.line', string="SECTION")
    variable_id = fields.Many2one('variable.template', string="VARIABLE")
    group_of_product_id = fields.Many2one('group.of.product', string="GROUP OF PRODUCT")
    budget_quantity = fields.Float(string="BUDEGT QUANTITY")
    unit_of_measure_id = fields.Many2one('uom.uom', string="UNIT OF MEASURE")
    lot_serial_id = fields.Many2one('stock.production.lot', string="LOT/SERIAL")
    package_id = fields.Many2one('stock.quant.package', string="PACKAGE")
    owner_id = fields.Many2one('res.partner', string="OWNER")
    scrap_reference = fields.Char(string="SCRAP REFERENCE")

    overhead_id = fields.Many2one('project.progress.report', string="OverHead reference")

class ScurveReport(models.Model):
    _name = 'scurve.report'
    _description = "Scurve Line Report"

    name = fields.Char(string="Name")
    project_id = fields.Many2one('project.project', string='Project', required=True, related="scurve_id.project_id")
    scurve_id = fields.Many2one(comodel_name='project.progress.report', string='Scurve Report')
    #scurve master
    job_cost_sheet = fields.Many2one('job.cost.sheet', 'Cost Sheet', required=True, store="1")
    project_budget = fields.Many2many(comodel_name='project.budget', string='Project Budget', domain="[('project_id','=', project_id)]", store="1")
    work_orders_ids = fields.Many2many("project.task", string="Work Orders", store="1")
    method = fields.Selection([('cost','Plan vs Actual Cost'),('progress','Plan vs Actual Progress'), ('cvp', 'Cost Progress'), ('pa_costprog', 'Plan and Actual Cost vs Progress'), ('all', 'Purchased vs Transferred vs Used Budget')], string = "Method", default='cost')
    contract_amount = fields.Float(string='Contract Amount')
    work_order_count = fields.Integer(string='Work Order Count', store=True)
    report_start_date = fields.Date(string='Report Start Date', related='scurve_id.report_start_date')
    report_end_date = fields.Date(string='Report End Date', related='scurve_id.report_end_date')
    #scurve
    ks_chart_data = fields.Text(string=_("Chart Data"), default=0)
    ks_graph_view = fields.Integer(string="Graph view", default=1)
    scurve_line_ids = fields.One2many('scurve.line.report','scurve_report_id', string = 'Scurve Line')

    def scurve_create_data_dict(self,result):
        data_dict = {}
        for data in result:
            keys = data_dict.keys()
            project_data = {
                'ks_scurve_id': self.id,
                'ks_value': float(self.work_order_count),
                'ks_project_id': self.project_id.id,
                'ks_partner_id': self.project_id.partner_id.id,
            }
            if self.project_id.id in keys:
                data_dict[self.project_id.id]['project'].append(self.project_id.name)
                data_dict[self.project_id.id]['count'].append(self.work_order_count)
            else:
                data_dict[self.project_id.id] = {'project': [], 'count': []}
        return data_dict

    def get_labels(self):
        if self.method == 'cost' or self.method == 'all':
            name = 'cost'
        else:
            name = 'progress(%)'
        return name

    def get_month(self):
        start_date = datetime.strptime(str(self.report_start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.report_end_date), "%Y-%m-%d")
        month = []
        for res in self:
            if res.report_end_date:
                while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                    end_date = start_date + relativedelta(months=+1, days=-1)
                    year_date = start_date.strftime("%Y")
                    month_date = start_date.strftime("%B")
                    month_year = month_date + ' ' + year_date

                    if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                        end_date = ends_date

                    month.append(month_year)
                    start_date = start_date + relativedelta(months=+1)
        return month

    def get_planned_cost_table(self):
        planned = []
        line = []
        cost = 0.0
        tra = 0.0
        pur = 0.0
        use = 0.0
        start_date = datetime.strptime(str(self.report_start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.report_end_date), "%Y-%m-%d")
        if self.method == 'cost':
            self.scurve_line_ids = [(5, 0, 0)]
        if self.project_budget:
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                line = []
                end_date = start_date + relativedelta(months=+1, days=-1)
                month_date = start_date.strftime("%B")
                year_date = start_date.strftime("%Y")
                budget = self.env['project.budget'].search([('project_id', '=', self.project_id.id), ('month.month', '=', month_date), ('month.year', '=', year_date)])
                line_src = self.env['scurve.line.report'].search([('scurve_report_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                cost += budget.budget_amount_total
                tra += budget.transferred_amount_total
                pur += budget.purchased_amount_total
                use += budget.actual_amount_total
                if budget:
                    if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                            end_date = ends_date
                elif line_src:
                    self.scurve_line_ids = [(1, line_src.id, {
                                'planned_cost': cost,
                                'purchased_amt': pur,
                                'transferred_amt': tra,
                                'used_amt': use
                            })]
                else:
                    return planned
                
                if line_src:
                    self.scurve_line_ids = [(1, line_src.id, {
                                'planned_cost': cost,
                                'purchased_amt': pur,
                                'transferred_amt': tra,
                                'used_amt': use
                            })]
                else:
                    line.append((0, 0, {
                        'scurve_report_id': self.id,
                        'month': month_date,
                        'year': year_date,
                        'planned_cost': cost,
                        'purchased_amt': pur,
                        'transferred_amt': tra,
                        'used_amt': use
                    }))

                self.scurve_line_ids = line
                start_date = start_date + relativedelta(months=+1)
            
        else:
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                line = []
                end_date = start_date + relativedelta(months=+1, days=-1)
                year_date = start_date.strftime("%Y")
                month_date = start_date.strftime("%B")
                line_src = self.env['scurve.line.report'].search([('scurve_report_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                    end_date = ends_date

                if line_src:
                    self.scurve_line_ids = [(1, line_src.id, {
                                'planned_cost': self.job_cost_sheet.amount_total,
                                'purchased_amt': self.job_cost_sheet.contract_budget_pur,
                                'transferred_amt': self.job_cost_sheet.contract_budget_tra,
                                'used_amt': self.job_cost_sheet.contract_budget_used,
                            })]
                else:
                    line.append((0, 0, {
                        'scurve_report_id': self.id,
                        'month': month_date,
                        'year': year_date,
                        'planned_cost': self.job_cost_sheet.amount_total,
                        'purchased_amt': self.job_cost_sheet.contract_budget_pur,
                        'transferred_amt': self.job_cost_sheet.contract_budget_tra,
                        'used_amt': self.job_cost_sheet.contract_budget_used,
                    }))
                self.scurve_line_ids = line
                start_date = start_date + relativedelta(months=+1)
    
    def get_planned_progress_table(self): 
        workorders = []
        start_date = datetime.strptime(str(self.report_start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.report_end_date), "%Y-%m-%d")
        acc_progress = 0.0
        if self.method == 'progress': 
            self.scurve_line_ids = [(5, 0, 0)]
        if self.work_orders_ids:
            workorders.append((0, 0, {'workorder': self.work_orders_ids.ids,}))
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                line = []
                end_date = start_date + relativedelta(months=+1, days=-1)
                month_date = start_date.strftime("%B")
                year_date = start_date.strftime("%Y")
                line_src = self.env['scurve.line.report'].search([('scurve_report_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                for wo in self.work_orders_ids:
                    if wo.planned_end_date:
                        wo_month = wo.planned_end_date.strftime("%B")
                        wo_year = wo.planned_end_date.strftime("%Y")
                            
                        if wo_month == month_date and wo_year == year_date:
                            cal = wo.work_weightage * wo.stage_weightage / 100

                            acc_progress += cal

                            wo = [(2, wo.id, 0)]

                if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                    end_date = ends_date

                if line_src:
                    self.scurve_line_ids = [(1, line_src.id, {
                                'planned_progress': acc_progress,
                            })]
                else:
                    line.append((0, 0, {
                        'scurve_report_id': self.id,
                        'month': month_date,
                        'year': year_date,
                        'planned_progress': acc_progress,
                    }))
                self.scurve_line_ids = line
                start_date = start_date + relativedelta(months=+1)    

    def get_actual_cost_table(self):
        actual = []
        amount = 0.0
        start_date = datetime.strptime(str(self.report_start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.report_end_date), "%Y-%m-%d")
        if self.project_budget:
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                end_date = start_date + relativedelta(months=+1, days=-1)
                month_date = start_date.strftime("%B")
                year_date = start_date.strftime("%Y")
                budget = self.env['project.budget'].search([('project_id', '=', self.project_id.id), ('month.month', '=', month_date), ('month.year', '=', year_date)])
                line_src = self.env['scurve.line.report'].search([('scurve_report_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                if budget:
                    if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                            end_date = ends_date
                else:
                    return actual
                amount += budget.actual_amount_total
                self.scurve_line_ids = [(1, line_src.id, {
                            'actual_cost': amount,
                        })]
                start_date = start_date + relativedelta(months=+1)
            else:
                pass

    def get_actual_progress_table(self):
        workorders = []
        acc_progress = 0.0
        start_date = datetime.strptime(str(self.report_start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.report_end_date), "%Y-%m-%d")
        if self.work_orders_ids:
            workorders.append((0, 0, {'workorder': self.work_orders_ids.ids,}))
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                end_date = start_date + relativedelta(months=+1, days=-1)
                month_date = start_date.strftime("%B")
                year_date = start_date.strftime("%Y")
                line_src = self.env['scurve.line.report'].search([('scurve_report_id', '=', self.id), ('month', '=', month_date), ('year', '=', year_date)])
                for wo_act in self.work_orders_ids:
                    if wo_act.actual_end_date:
                        wo_month = wo_act.actual_end_date.strftime("%B")
                        wo_year = wo_act.actual_end_date.strftime("%Y")
                        if wo_month == month_date and wo_year == year_date:
                            cal1 = wo_act.work_weightage * wo_act.stage_weightage / 100
                            acc_progress += cal1
                if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                    end_date = ends_date
                self.scurve_line_ids = [(1, line_src.id, {
                            'actual_progress': acc_progress,
                        })]
                start_date = start_date + relativedelta(months=+1)

    def get_plan_cost_from_table(self):
        planned = []
        cost = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                cost = line.planned_cost
                planned.append(cost)
            return planned

    def get_all_cost_from_table(self, purchased, transferred, used):
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                pur = line.purchased_amt
                tra = line.transferred_amt
                use = line.used_amt
                purchased.append(pur)
                transferred.append(tra)
                used.append(use)
            return purchased, transferred, used
    
    def get_plan_progress_from_table(self):
        planned = []
        acc_progress = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                prog = line.planned_progress
                acc_progress = prog
                planned.append(acc_progress)
            return planned

    def get_actual_cost_from_table(self):
        actual = []
        acc_progress = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                acc_progress = line.actual_cost
                actual.append(acc_progress)
            return actual

    def get_actual_progress_from_table(self):
        actual = []
        acc_progress = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                prog = line.actual_progress
                acc_progress = prog
                actual.append(acc_progress)
            return actual
    
    def get_plan_cost_progress_from_table(self):
        planned = []
        cost = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                prog = line.prog_planned_cost
                cost = prog
                planned.append(cost)
            return planned
    
    def get_actual_cost_progress_from_table(self):
        actual = []
        acc_progress = 0.0
        if self.scurve_line_ids:
            for line in self.scurve_line_ids:
                prog = line.prog_actual_cost
                acc_progress = prog
                actual.append(acc_progress)
            return actual

    def create_scurve_cost(self, final_dict):
        final_dict = {}
        month = self.get_month()
        label_1 = ''
        label_2 = ''

        name = self.get_labels()
        self.get_planned_cost_table()
        self.get_actual_cost_table()
        planned = self.get_plan_cost_from_table()
        actual = self.get_actual_cost_from_table()
        label_1 = 'Planned '
        label_2 = 'Actual '
        name1 = name
        name2 = name
        
        final_dict.update({
            'labels': month,
            'datasets': [{
                'data' : planned,
                'label': label_1 + name1,
                }, {
                'data': actual,
                'label': label_2 + name2,
                }]
            })
        self.ks_chart_data = json.dumps(final_dict)
        print(final_dict)
        return final_dict

    def create_scurve_all(self, final_dict):
        final_dict = {}
        month = self.get_month()
        label_1 = ''
        label_2 = ''
        label_3 = ''

        purchased = []
        transferred = []
        used = []
        name = self.get_labels()
        self.get_planned_cost_table()
        self.get_all_cost_from_table(purchased, transferred, used)
        label_1 = 'Purchased '
        label_2 = 'Transferred '
        label_3 = 'Used '
        name1 = name
        name2 = name
        name3 = name

        final_dict.update({
            'labels': month,
            'datasets': [{
                'data' : purchased,
                'label': label_1 + name1,
                }, {
                'data' : transferred,
                'label': label_2 + name2,
                }, {
                'data' : used,
                'label': label_3 + name3,
                }]
            })
        self.ks_chart_data = json.dumps(final_dict)
        print(final_dict)
        return final_dict

    def create_scurve_progress(self, final_dict):
        final_dict = {}
        month = self.get_month()
        label_1 = ''
        label_2 = ''
        
        name = self.get_labels()
        self.get_planned_progress_table()
        self.get_actual_progress_table()
        planned = self.get_plan_progress_from_table()
        actual = self.get_actual_progress_from_table()
        label_1 = 'Planned '
        label_2 = 'Actual '
        name1 = name
        name2 = name
    
        final_dict.update({
            'labels': month,
            'datasets': [{
                'data' : planned,
                'label': label_1 + name1,
                }, {
                'data': actual,
                'label': label_2 + name2,
                }]
            })
        self.ks_chart_data = json.dumps(final_dict)
        print(final_dict)
        return final_dict

    def create_scurve_cvp(self, final_dict):
        final_dict = {}
        month = self.get_month()
        label_1 = ''
        label_2 = ''
        
        self.get_planned_progress_table()
        self.get_planned_cost_table()
        self.get_actual_progress_table()
        self.get_actual_cost_table()
        # self.scurve_line_cvp_ids._compute_plan_cost_progress()
        # self.scurve_line_cvp_ids._compute_actual_cost_progress()
        planned = self.get_actual_cost_progress_from_table()
        actual = self.get_actual_progress_from_table()
        name1 = 'Cost(%)'
        name2 = 'Progress(%)'
        label_1 = 'Actual '
        label_2 = 'Actual '

    
        final_dict.update({
            'labels': month,
            'datasets': [{
                'data' : planned,
                'label': label_1 + name1,
                }, {
                'data': actual,
                'label': label_2 + name2,
                }]
            })
        self.ks_chart_data = json.dumps(final_dict)
        print(final_dict)
        return final_dict

    def create_scurve_pa_costprog(self, final_dict):
        final_dict = {}
        month = self.get_month()
        label_1 = ''
        label_2 = ''
    
        self.get_actual_progress_table()
        self.get_planned_progress_table()
        self.get_actual_cost_table()
        self.get_planned_cost_table()
        # self.scurve_line_pa_ids._compute_plan_cost_progress()
        # self.scurve_line_pa_ids._compute_actual_cost_progress()
        planned = self.get_plan_cost_progress_from_table()
        planned1 = self.get_plan_progress_from_table()
        actual = self.get_actual_cost_progress_from_table()
        actual1 = self.get_actual_progress_from_table()
        name1 = 'Cost'
        name2 = 'Progress(%)'
        label_1 = 'Planned '
        label_2 = 'Actual '
    
        final_dict.update({
            'labels': month,
            'datasets': [{
                'data' : planned,
                'label': label_1 + name1,
                }, {
                'data' : planned1,
                'label': label_1 + name2,
                }, {
                'data' : actual,
                'label': label_2 + name1,
                }, {
                'data': actual1,
                'label': label_2 + name2,
                }]
            })
        self.ks_chart_data = json.dumps(final_dict)
        print(final_dict)
        return final_dict

    @api.depends('work_orders_ids')
    def _initiate_s_curve(self):
        for record in self:
            record.work_order_count = len(record.work_orders_ids)  
        data =  self.scurve_create_data_dict(self.project_id)
        if self.method == 'cost':
            self.create_scurve_cost(data)
        elif self.method == 'progress':
            self.create_scurve_progress(data)
        elif self.method == 'cvp':
            self.create_scurve_cvp(data)
        elif self.method == 'all':
            self.create_scurve_all(data)
        else:
            self.create_scurve_pa_costprog(data)

class ScurveLine(models.Model):
    _name = 'scurve.line.report'
    _description = "Scurve Line Report"

    sequence = fields.Integer(string="Sequence", default=0)
    scurve_report_id = fields.Many2one(comodel_name='scurve.report', string='Scurve Line')
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    month = fields.Char(string='Month')
    year = fields.Char(string='Year')
    planned_cost = fields.Float(string='Planned Cost')
    actual_cost = fields.Float(string='Actual Cost')
    prog_planned_cost = fields.Float(string='Progress Planned Cost')
    prog_actual_cost = fields.Float(string='Progress Actual Cost')
    contract_amount = fields.Float(string='Contract Amount', related='scurve_report_id.contract_amount')
    planned_progress = fields.Float(string='Planned Progress')
    actual_progress = fields.Float(string='Actual Progress')
    planned_revenue = fields.Float(string='Planned Revenue')
    actual_revenue = fields.Float(string='Actual Revenue')
    planned_material_cost = fields.Float(string='Planned Material Cost')
    actual_material_cost = fields.Float(string='Actual Material Cost')
    purchased_amt = fields.Float(string='Purchased Amount')
    transferred_amt = fields.Float(string='Transferred Amount')
    used_amt = fields.Float(string='Used Amount')
    method = fields.Selection([
        ('cost', 'Cost'),
        ('progress', 'Progress')
    ], string='Method', related='scurve_report_id.method')

    def _compute_plan_cost_progress(self):
        for line in self:
            cost = line.planned_cost / line.contract_amount * 100
            line.prog_planned_cost = cost

    def _compute_actual_cost_progress(self):
        for line in self:
            cost = line.actual_cost / line.contract_amount * 100
            line.prog_actual_cost = cost  

    @api.depends('scurve_report_id.scurve_line_ids', 'scurve_report_id.scurve_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.scurve_report_id.scurve_line_ids:
                no += 1
                l.sr_no = no


class ClaimHistoryReport(models.Model):
    _name = 'report.claim.history'
    _description = 'Claim History Report'

    claim_id = fields.Many2one('progressive.claim', string="Progressive Claim")
    sr_no = fields.Integer(string = "No.")
    date = fields.Date(string = "Date")
    claim_name = fields.Char(string="Claim ID")
    claim_for = fields.Selection([('down_payment', 'Down Payment'),('progress', 'Progress'),
                                  ('retention1', 'Retention 1'), ('retention2', 'Retention 2')],
                                 string="Claim Type")
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    progressline = fields.Float(string="Progress (%)")
    gross_amount = fields.Monetary(string="Gross Amount", currency_field='currency_id')
    dp_deduction = fields.Monetary(string="DP Deduction", currency_field='currency_id')
    retention_deduction = fields.Monetary(string="Retention Deduction", currency_field='currency_id')
    amount_deduction = fields.Monetary(string="Amount Deduction", currency_field='currency_id')
    paid_invoice = fields.Monetary(string="Paid Invoice", currency_field='currency_id')
    amount_untaxed = fields.Monetary(string="Amount Untaxed", currency_field='currency_id')
    tax_id = fields.Many2many('account.tax', string="Taxes")
    tax_amount = fields.Monetary(string="Tax Amount", currency_field='currency_id')
    amount_invoice = fields.Monetary(string="Amount Invoice", currency_field='currency_id')
    amount_claim = fields.Monetary(string="Amount Claimed", currency_field='currency_id')
    remaining_amount = fields.Monetary(string="Remaining Amount", currency_field='currency_id')
    invoice_status = fields.Selection([('draft', 'Draft'),('to_approve', 'To Approve'), ('approved', 'Approved'),
                                       ('rejected', 'Rejected'), ('posted', 'Posted'), ('cancel', 'Cancelled'),
                                       ('failed', ' Payment Failed')], string="Invoice Status")
    payment_status = fields.Selection([('not_paid', 'Not Paid'),('in_payment', 'In Payment'), ('paid', 'Paid'),
                                       ('partial', 'Partially Paid'), ('reversed', 'Reversed'),
                                       ('invoicing_legacy', ('Invoicing App Legacy'))], string="Payment Status")

    report_id = fields.Many2one('project.progress.report', string="Report Reference")
    progressive_bill = fields.Boolean(string="Progressive Bill", store = True)



