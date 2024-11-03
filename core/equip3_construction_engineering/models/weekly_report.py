from odoo import _, api, fields, models


class ProjectWeeklyReportInherit(models.Model):
    _inherit = 'project.progress.report'

    construction_type = fields.Selection([('construction','Construction'),('engineering','Engineering')], string="Construction Type", compute='_compute_type')
    production_history_ids = fields.One2many('production.record.report', 'production_record')

    @api.depends('project_id')
    def _compute_type(self):
        project = self.project_id
        if project.construction_type == 'construction':
            self.construction_type = 'construction'
        elif project.construction_type == 'engineering':
            self.construction_type = 'engineering'
        else:
            self.construction_type = False

    def get_report(self):
        res = super(ProjectWeeklyReportInherit, self).get_report()
        num = 0
        self.production_history_ids = False

        # to fill production record history notebook page
        record_ids = self.env['mrp.consumption'].search([
            ('project_id', '=', self.project_id.id),
            ('contract', '=', self.contract_id.id),
            ('create_date','>=', self.report_start_date),
            ('create_date', '<=',self.report_end_date),
            ('state', '=', 'confirm')])
        record_data = []
        for line in record_ids:
            vals = {}
            num += 1
            vals["sr_no"] = num
            vals["record_id"] = line.id
            record_data.append((0,0,vals))
        self.production_history_ids = record_data

        # new
        record_exist = set()
        for record in record_ids:
            record_exist.add(record.id)
        records = self.env['mrp.consumption'].search([
            ('project_id', '=', self.project_id.id),
            ('contract', '=', self.contract_id.id),
            ('create_date','>=', self.report_start_date),
            ('create_date', '<=',self.report_end_date),
            ('state', '=', 'confirm')])
        new_record_data = []
        for r in records:
            if r.id not in record_exist:
                vals = {}
                num += 1
                vals["sr_no"] = num
                vals["record_id"] = r.id
                new_record_data.append((0,0,vals))
        self.production_history_ids = new_record_data

        return res
        
class ProductionRecordReport(models.Model):
    _name = 'production.record.report'
    _description = 'Production Record Report'
    _order = 'sequence'
    _check_company_auto = True

    production_record = fields.Many2one('project.progress.report', string="Report ID")
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_id = fields.Many2one(related="production_record.project_id", string='Project')
    contract_id = fields.Many2one(related="production_record.contract_id", string='Contract')
    report_start_date = fields.Date(string='Report Start Date', related="production_record.report_start_date")
    report_end_date = fields.Date(string='Report End Date', related="production_record.report_end_date")
    company_id = fields.Many2one(string='Company', related="production_record.company_id")
    branch_id = fields.Many2one(string="Branch", related="production_record.branch_id")
    created_on = fields.Datetime(related='record_id.create_date', string="Created On")
    record_id = fields.Many2one('mrp.consumption', string='Production Record')
    finished = fields.Float(related='record_id.finished_qty', string='Finished Product')
    rejected = fields.Float(related='record_id.rejected_qty', string='Rejected Product')
    uom_id = fields.Many2one(related='record_id.product_uom_id', string='Product UOM')
    status = fields.Selection(related='record_id.state', string='Status')

    @api.depends('production_record.production_history_ids', 'production_record.production_history_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.production_record.production_history_ids:
                no += 1
                l.sr_no = no

