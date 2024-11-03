# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class CommonLogBookEpt(models.Model):
    _name = "common.log.book.ept"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'
    _description = "Common log book for all connector"

    name = fields.Char(readonly=True)
    type = fields.Selection([('import', 'Import'), ('export', 'Export')], string="Operation")
    module = fields.Selection([('amazon_ept', 'Amazon Connector'),
                               ('woocommerce_ept', 'Woocommerce Connector'),
                               ('shopify_ept', 'Shopify Connector'),
                               ('magento_ept', 'Magento Connector'),
                               ('bol_ept', 'Bol Connector'),
                               ('ebay_ept', 'Ebay Connector'),
                               ('amz_vendor_central', 'Amazon Vendor Central')])
    active = fields.Boolean(default=True)
    log_lines = fields.One2many('common.log.lines.ept', 'log_book_id')
    message = fields.Text()
    model_id = fields.Many2one("ir.model", help="Model Id", string="Model")
    res_id = fields.Integer(string="Record ID", help="Process record id")
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    file_name = fields.Char(string='File Name')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order')


    @api.model
    def create(self, vals):
        """
        This method is create for sequence wise name.
        :param vals: values
        :return:super
        """
        seq = self.env['ir.sequence'].next_by_code('common.log.book.ept') or '/'
        vals['name'] = seq
        return super(CommonLogBookEpt, self).create(vals)

    def create_common_log_book(self, process_type, instance_field, instance, model_id,module):
        """ This method used to create a log book record.
            :param type: Generally, the process type value is 'import' or 'export'.
            :model_id: record of model.
            : instance_field: Name of the field which relates to the instance field for different
                apps
            : instance: Instance value:
            : Module: For which App this log book is belongs to.
            @return: log_book_id
        """
        log_book_id = self.create({"type": process_type,
                                   "module": module,
                                   instance_field: instance.id,
                                   "model_id": model_id,
                                   "active": True})
        return log_book_id
