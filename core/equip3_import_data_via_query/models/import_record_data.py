from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo import tools
from datetime import datetime
from xlrd import open_workbook
import xlrd
import base64

# def check_taxes_consistency(company_id, has_taxes, line):
#     supplier_taxes_validation = any(
#         tax.company_id.id == company_id\
#         for tax in line.product_id.supplier_taxes_id
#     )
#     if supplier_taxes_validation not in has_taxes:
#         has_taxes.append(supplier_taxes_validation)

#     if has_taxes[0] != supplier_taxes_validation:
#         raise UserError(_("Inconsistent taxes found for product %s.\
#         All products must either have taxes or not have taxes based on their order type (purchase/sale).")\
#         % line.product_id.name)

class ImportRecordData(models.Model):
    _name = 'import.record.data'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Name')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], string='State', default='draft',tracking=True)

    record_type = fields.Selection([
        ('purchase_import', 'Purchase Import'),
    #     ('stock_putaway_rules', 'Stock Putaway Rule'),
    #     ('return_import_purchase','Return Import Purchase Order'),
    #     ('return_import_sale','Return Import Sale Order'),
        ('product_import','Import Product'),
        
    ], string='Record Type',required=1)

    created_date = fields.Date(string='Created Date', default=fields.Datetime.now, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Vendor')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', domain = "[('company_id', '=', current_company_id)]")
    location_id = fields.Many2one('stock.location', string='Location')
    no_return = fields.Char(string='No Document Return')
    sheet_number = fields.Integer("Sheet Number",default=1)
    error_message = fields.Text(string='Message', tracking=True)
    product_list = fields.Html(string='Product List', copy=False)
    file = fields.Binary(string='File')
    file_name = fields.Char(string='File Name')
    filter_location_ids = fields.Many2many('stock.location', string='Location', compute='_get_filter_locations', store=False)

    @api.depends('warehouse_id')
    def _get_filter_locations(self):
        location_id = []
        for record in self:
            if record.warehouse_id:
                location_obj = record.env['stock.location']
                store_location_id = record.warehouse_id.view_location_id.id
                addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_id.append(location.id)
                record.filter_location_ids = [(6, 0, location_id)]
            else:
                record.filter_location_ids = [(6, 0, [])]

    def generate_table(self):
        self.ensure_one()
        no_return = self.no_return

        # Return PO
        if self.record_type == 'return_import_purchase':
            # Query to get the max rma_id from dev_rma_line
            self.env.cr.execute("""
                SELECT MAX(rma_line.rma_id)
                FROM dev_rma_line rma_line
                LEFT JOIN dev_rma_rma rma_rma ON rma_line.rma_id = rma_rma.id
                WHERE rma_rma.name = %s
                AND rma_line.sale_id IS NOT NULL
            """, (no_return,))
            max_rma_id = self.env.cr.fetchone()[0]

            if not max_rma_id:
                raise UserError("No data found for the given Return Number.")

            # Query to get the product_id and return_qty from dev_rma_line using the max rma_id
            self.env.cr.execute("""
                SELECT rma_line.product_id, rma_line.return_qty
                FROM dev_rma_line rma_line
                WHERE rma_line.rma_id = %s
                AND rma_line.sale_id IS NOT NULL
            """, (max_rma_id,))

        # Return SO
        elif self.record_type == 'return_import_sale':
            # Query to get the max rma_id from dev_rma_line
            self.env.cr.execute("""
                SELECT MAX(rma_line.rma_id)
                FROM dev_rma_line rma_line
                LEFT JOIN dev_rma_rma rma_rma ON rma_line.rma_id = rma_rma.id
                WHERE rma_rma.name = %s
            """, (no_return,))
            max_rma_id = self.env.cr.fetchone()[0]

            if not max_rma_id:
                raise UserError("No data found for the given Return Number.")

            # Query to get the product_id and return_qty from dev_rma_line using the max rma_id
            self.env.cr.execute("""
                SELECT rma_line.product_id, rma_line.return_qty
                FROM dev_rma_line rma_line
                WHERE rma_line.rma_id = %s
            """, (max_rma_id,))

        rows = self.env.cr.fetchall()

        if not rows:
            raise UserError("No data found for the given Return Number.")

        product_ids = [row[0] for row in rows]
        return_qtys = [row[1] for row in rows]

        products = self.env['product.product'].browse(product_ids)
        product_names = products.mapped('name')

        data = "<table border='1'>"
        data += "<tr><th>Product Name</th><th>Return Qty</th></tr>"
        for product_name, return_qty in zip(product_names, return_qtys):
            data += "<tr><td>%s</td><td>%s</td></tr>" % (product_name, return_qty)
        data += "</table>"

        self.product_list = data

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('import.record.data') or 'New'
        return super(ImportRecordData, self).create(values)

    def button_confirm(self):
        if not self.file and self.record_type not in ['return_import_purchase', 'return_import_sale']:
            raise UserError("Please upload the document before confirm.")
        elif self.record_type in ['return_import_purchase', 'return_import_sale']:
            self.generate_table()
        else:
            import_name_extension = self.file_name.split('.')[1]
            if import_name_extension not in ['xls', 'xlsx']:
                raise UserError('The upload file is using the wrong format. Please upload your file in xlsx and xls format.')
        self.state = 'confirm'

    def action_trigger_import_data(self):
        records = self.env['import.record.data'].search([('state','=','confirm')])
        for rec in records:
            rec.button_action_import()

    def button_action_import(self):
        self.error_message = ""
        # Read data from excel sheet
        if self.file:
            workbook = open_workbook(file_contents=base64.decodestring(self.file))
            row_count, total_cnt = 0 , 1
            sheet = False
            try:
                sheet = workbook.sheets()[self.sheet_number-1]
                row_count = sheet.nrows
            except Exception as exc:
                raise UserError('Entered sheet number not available in the excel sheet.')

            purchase_orders = []
            cnt = 0
        
        if self.record_type == 'stock_putaway_rules':
            not_updated_data = ""
            try:
                # total_cnt = 1
                for row in range(sheet.nrows):
                    row = sheet.row_values(row)

                    # Skip Column Header
                    if cnt == 0:
                        cnt += 1
                        continue

                    #Checking product
                    self.env.cr.execute("SELECT id FROM product_product WHERE id = '%s' "% (str(row[0]),))
                    product = self.env.cr.dictfetchall()

                    #Checking location IN
                    self.env.cr.execute("SELECT id FROM stock_location WHERE id = '%s' "% (str(row[1]),))
                    loc_in = self.env.cr.dictfetchall()

                    #Checking location out
                    self.env.cr.execute("SELECT id FROM stock_location WHERE id = '%s' "% (str(row[2]),))
                    loc_out = self.env.cr.dictfetchall()   

                    if not product:
                        not_updated_data = not_updated_data+"\n [ "+str(row[0])+" ] Product with ID not available in the system"

                    if not loc_in:
                        not_updated_data = not_updated_data+"\n [ "+str(row[1])+" ] Location with ID not available in the system"
                    
                    if not loc_out:
                        not_updated_data = not_updated_data+"\n [ "+str(row[2])+" ] Location with ID not available in the system"

                    #Checking company
                    if self.env.company.id != row[3]:
                        not_updated_data = not_updated_data+"\n [ "+str(row[3])+" ] Company is not competible!"


                    #check existing data on system
                    put_away_exist_query = """ 
                        SELECT id FROM stock_putaway_rule spr
                        LEFT JOIN product_putaway_ids ptids ON ptids.prod_ids = spr.id
                        WHERE ptids.putaway_id = %s 
                        AND spr.location_in_id = %s
                        AND spr.company_id = %s
                        ORDER BY id ASC LIMIt 1;
                    """
                    self.env.cr.execute(put_away_exist_query, [row[0],row[1],row[3],])
                    put_away_exist = self.env.cr.dictfetchall()
                    if put_away_exist and len(put_away_exist) == 1:
                        query_update = """
                            UPDATE stock_putaway_rule 
                            SET location_out_id = %s
                            WHERE id = %s
                        """
                        self.env.cr.execute(query_update, [row[2], put_away_exist[0].get('id'),])

                    if len(put_away_exist) == 0:                   
                        self.env.cr.execute("""
                            INSERT INTO stock_putaway_rule(location_in_id, location_out_id, create_date, company_id)
                            VALUES(%s,%s,%s,%s) RETURNING id
                        """,(row[1], row[2], fields.Datetime.now(),row[3]))
                        putaway_id = self._cr.dictfetchone()

                        self.env.cr.execute("""
                            INSERT INTO product_putaway_ids(putaway_id, prod_ids)
                            VALUES(%s,%s)
                        """,(row[0], putaway_id.get('id')))    

                    total_cnt += 1 
                self.env.cr.commit()

            except Exception as e:
                error_message = tools.ustr(e)
                pos_orders = []
                self.env.cr.rollback()
                self.error_message = error_message + "\n " + not_updated_data
                self.state = "failed"
            
            if total_cnt == row_count:
                self.state = "done"

        if self.record_type == 'purchase_import':
            not_updated_data = ""
            company_id = self.env.company.id
            try:
                for row in range(sheet.nrows):
                    row = sheet.row_values(row)


                    # Skip Column Header
                    if cnt == 0:
                        cnt +=1
                        continue

                    purchase_order_seq , type_order  = self.purchase_order_sequence(row)

                    # Check Product Availability
                    query = "SELECT id,product_display_name,product_tmpl_id FROM product_product WHERE barcode = '%s' or default_code = '%s' "% (str(row[6]),str(row[6]))
                    self.env.cr.execute(query)
                    product_data = self._cr.dictfetchone()


                    # Check Vendor Availability
                    partner_query = "select id from res_partner where vendor_sequence = '%s' " % (str(row[1]),)
                    self.env.cr.execute(partner_query)
                    vendor_data  = self._cr.dictfetchone()

                    # Check Branch
                    branch_query = "select id, company_id from res_branch where name = '%s' " % (str(row[4]),)
                    self.env.cr.execute(branch_query)
                    branch_data = self._cr.dictfetchone()

                    # Check Destination Warehouse
                    warehouse_query = "select id, company_id from stock_warehouse where name = '%s' " % (str(row[5]),)
                    self.env.cr.execute(warehouse_query)
                    warehouse_data = self._cr.dictfetchone()

                    # Check Analytic Account
                    analytic_query = "select id, company_id from account_analytic_tag where name ilike '%%%s%%' " % (str(row[7]),)
                    self.env.cr.execute(analytic_query)
                    analytic_data = self._cr.dictfetchone()

                    # Check Currency
                    currency_query = "select id, company_id from res_currency where name = '%s' " % (str(row[11]))
                    self.env.cr.execute(currency_query)
                    currency_data = self._cr.dictfetchone()

                    milestone_id = None
                    if type_order == 'is_services_orders':
                        milestone_template_query = "select id from milestone_contract_template where name ilike '%%%s%%' " % (str(row[16]))
                        self.env.cr.execute(milestone_template_query)
                        milestone_template = self._cr.dictfetchone()
                        milestone_id = milestone_template.get('id')

                    if not product_data:
                        not_updated_data = not_updated_data+"\n [ "+str(row[6])+" ] barcode related product not available in the system"

                    if not vendor_data:
                        not_updated_data += "\n [ "+str(row[1])+" ] vendor not available in the system"

                    if not branch_data:
                        not_updated_data += "\n [ "+str(row[4])+" ] branch not available in the system"

                    if not warehouse_data:
                        not_updated_data += "\n [ "+str(row[5])+" ] warehouse_data not available in the system"

                    if not analytic_data:
                        not_updated_data += "\n [ "+str(row[7])+" ] analytic account not available in the system"
                    if not currency_data:
                        not_updated_data += "\n [ "+str(row[11])+" ] Currency not available in the system"
                    if not milestone_id and type_order == 'is_services_orders':
                        not_updated_data += "\n [ "+str(row[16])+" ] Milestone and Contract Terms not available in the system"
                    
                    

                    # Check Bracnh apakah company_id sama dengan company_id user
                    if branch_data:
                        if branch_data.get('company_id') != company_id:
                            not_updated_data += "\n [ "+str(row[4])+" ] branch not compatible with company"
                            branch_data = False

                    # Check Warehouse apakah company_id sama dengan company_id user
                    if warehouse_data:
                        if warehouse_data.get('company_id') != company_id:
                            not_updated_data += "\n [ "+str(row[5])+" ] warehouse not compatible with company"
                            warehouse_data = False

                    # Check Analytic Account apakah company_id sama dengan company_id user
                    if analytic_data:
                        if analytic_data.get('company_id') != company_id:
                            not_updated_data += "\n [ "+str(row[7])+" ] analytic account not compatible with company"
                            analytic_data = False

                    product_template_data = False
                    if product_data:
                        product_template_query = "select uom_id from product_template where id = %s " % (
                            product_data.get('product_tmpl_id'),)

                        self.env.cr.execute(product_template_query)
                        product_template_data = self._cr.dictfetchone()

                    # check if purchase order already exist
                    # check_order_query = "select id from purchase_order where import_reference = '%s' " % (str(row[0]),)
                    check_order_query = """
                        SELECT id 
                        FROM purchase_order 
                        WHERE origin = '%s' 
                        AND company_id = %d
                        AND state = 'draft'
                        """ % (str(row[0]), company_id)
                    self.env.cr.execute(check_order_query)
                    po_order_data = self._cr.dictfetchone()

                    date_order, date_planned = "", ""
                    if row[2]:
                        date_order = xlrd.xldate.xldate_as_datetime(row[2], 0)

                    if row[3]:
                        date_planned = xlrd.xldate.xldate_as_datetime(row[3], 0)
                    
                    # Get Picking Type ID
                    warehouse_id = False
                    if warehouse_data:
                        warehouse_id = self.env['stock.warehouse'].browse(warehouse_data.get('id'))
                        picking_type = False

                    if warehouse_id:
                        picking_type_query = "select id from stock_picking_type where warehouse_id = '%s' and default_location_dest_id = '%s'" % (warehouse_id.id, warehouse_id.lot_stock_id.id)
                        self.env.cr.execute(picking_type_query)
                        picking_type = self._cr.dictfetchone().get('id')

                    check_product_price_query = "select price from product_supplierinfo where product_tmpl_id = '%s' and company_id = '%s' and name = '%s' " % (
                    product_data.get('product_tmpl_id'),company_id, vendor_data.get('id'))
                    self.env.cr.execute(check_product_price_query)
                    pricelist_data = self._cr.dictfetchone()
                    product_price = pricelist_data.get('price') if not row[9] and pricelist_data else row[9]

                    if isinstance(product_price, str):
                        raise UserError(_('The product price in excel & vendor pricelist is null'))

                    check_product_taxes_query = """
                        SELECT pstr.tax_id 
                        FROM product_supplier_taxes_rel pstr
                        LEFT JOIN account_tax at ON at.id = pstr.tax_id
                        WHERE at.company_id = %s AND pstr.prod_id = %s 
                    """
                    self.env.cr.execute(check_product_taxes_query, (company_id,product_data.get('product_tmpl_id'),))
                    taxes_data = self.env.cr.fetchall()
                    tax_ids = [tax[0] for tax in taxes_data]
                    if not po_order_data:
                        # i give condition because cannot call expression like Null or none on python
                        if milestone_id:
                            insert_po_order_query = "INSERT INTO purchase_order(create_date,date_order,date_planned,name,import_reference,create_uid,partner_id,branch_id,destination_warehouse_id,currency_id,company_id,picking_type_id,partner_invoice_id,state,dp," +type_order+ ",active,discount_type,po,origin,milestone_template_id) " \
                                                "VALUES('%s','%s','%s','%s','%s',%s,%s,%s,%s,%s,%s,%s,%s,'%s',%s,%s,%s,'%s',%s,'%s',%s) RETURNING id;" % \
                                                (date_order,date_order,date_planned,purchase_order_seq,row[0],1,vendor_data.get('id'),branch_data.get('id'),warehouse_data.get('id'),currency_data.get('id'),company_id,picking_type,vendor_data.get('id'),'draft',False,True,True,'global',False,row[0],milestone_id)
                        else:
                            insert_po_order_query = "INSERT INTO purchase_order(create_date,date_order,date_planned,name,import_reference,create_uid,partner_id,branch_id,destination_warehouse_id,currency_id,company_id,picking_type_id,partner_invoice_id,state,dp," +type_order+ ",active,discount_type,po,origin,milestone_template_id) " \
                                                "VALUES('%s','%s','%s','%s','%s',%s,%s,%s,%s,%s,%s,%s,%s,'%s',%s,%s,%s,'%s',%s,'%s',NULL) RETURNING id;" % \
                                                (date_order,date_order,date_planned,purchase_order_seq,row[0],1,vendor_data.get('id'),branch_data.get('id'),warehouse_data.get('id'),currency_data.get('id'),company_id,picking_type,vendor_data.get('id'),'draft',False,True,True,'global',False,row[0])

                        self.env.cr.execute(insert_po_order_query)
                        po_ref = self._cr.dictfetchone()
                        purchase_orders.append(po_ref.get('id'))

                        if analytic_data:
                            self.env.cr.execute("INSERT INTO account_analytic_tag_purchase_order_rel  (purchase_order_id, account_analytic_tag_id) VALUES (%s, %s)",
                                            (po_ref.get('id'), analytic_data.get('id')))
                        self.create_purchase_order_line(po_ref, product_data, product_template_data, warehouse_data, analytic_data, row, date_planned, tax_ids, product_price)                 
                    else:
                        if po_order_data.get('id') not in purchase_orders:
                            purchase_orders.append(po_order_data.get('id'))
                        self.create_purchase_order_line(po_order_data, product_data, product_template_data, warehouse_data, analytic_data, row, date_planned, tax_ids, product_price)
                        
                    total_cnt += 1
                # ggg
                if total_cnt == row_count:
                    print (purchase_orders, 'purchase_orders')
                    for po in purchase_orders:
                        po_obj = self.env['purchase.order'].browse(po)
                        po_obj._amount_all()
                        if type_order == 'is_services_orders':
                            po_obj._onchange_milestone_template_id()
                        has_taxes = []
                        for line in po_obj.order_line:
                            # check_taxes_consistency(company_id, has_taxes, line)
                            line._compute_qty_received_method()
                            line._compute_tax_id()
                            # line._set_persentase_antar_badan()                    
                    self.state = "done"

            except Exception as e:
                error_message = tools.ustr(e)
                self.env.cr.rollback()
                self.error_message = error_message + "\n " + not_updated_data
                self.state = "failed"

        elif self.record_type == 'pos_import':
            self.create_pos_order(sheet)

        elif self.record_type == 'product_import':
            self.create_product_template(sheet)

        elif self.record_type in ['return_import_purchase', 'return_import_sale']:
            self.create_return_order()

        elif self.record_type == 'receiving_notes_import':
            self.create_receiving_notes(sheet)

        elif self.record_type == 'delivery_orders_import':
            self.create_delivery_orders(sheet)

    def create_return_order(self):
        def fetch_location(record_type, location_id):
            if record_type == 'return_import_purchase':
                query = """
                    SELECT id 
                    FROM stock_picking_type 
                    WHERE default_location_dest_id = %s AND code = 'incoming'
                    LIMIT 1
                """
            elif record_type == 'return_import_sale':
                query = """
                    SELECT id 
                    FROM stock_picking_type 
                    WHERE default_location_src_id = %s AND code = 'outgoing'
                    LIMIT 1
                """
            self.env.cr.execute(query, (location_id,))
            location = self.env.cr.fetchone()
            if not location:
                raise UserError("Default destination location not found.")
            return location[0]

        def fetch_rma_line_data(record_type, no_return):
            if record_type == 'return_import_purchase':
                query = """
                    WITH max_rma AS (
                        SELECT MAX(rma_line.rma_id) AS max_rma_id
                        FROM dev_rma_line rma_line
                        LEFT JOIN dev_rma_rma ON rma_line.rma_id = dev_rma_rma.id
                        WHERE dev_rma_rma.name = %s
                        AND rma_line.sale_id IS NOT NULL
                    )
                    SELECT
                        rma_line.product_id,
                        SUM(rma_line.return_qty) AS return_qty,
                        SUM(rma_line.delivered_qty) AS delivered_qty,
                        rma_line.tax_number AS tax_number
                    FROM
                        dev_rma_line rma_line
                    JOIN
                        dev_rma_rma ON rma_line.rma_id = dev_rma_rma.id
                    JOIN
                        max_rma ON rma_line.rma_id = max_rma.max_rma_id
                    WHERE
                        dev_rma_rma.name = %s
                        AND rma_line.sale_id IS NOT NULL
                    GROUP BY
                        rma_line.product_id,
                        rma_line.tax_number
                """
            elif record_type == 'return_import_sale':
                query = """
                    WITH max_rma AS (
                        SELECT MAX(rma_line.rma_id) AS max_rma_id
                        FROM dev_rma_line rma_line
                        LEFT JOIN dev_rma_rma ON rma_line.rma_id = dev_rma_rma.id
                        WHERE dev_rma_rma.name = %s
                        AND rma_line.purchase_id IS NOT NULL
                    )
                    SELECT
                        rma_line.product_id,
                        SUM(rma_line.return_qty) AS return_qty,
                        SUM(rma_line.delivered_qty) AS delivered_qty,
                        rma_line.tax_number AS tax_number
                    FROM
                        dev_rma_line rma_line
                    JOIN
                        dev_rma_rma ON rma_line.rma_id = dev_rma_rma.id
                    JOIN
                        max_rma ON rma_line.rma_id = max_rma.max_rma_id
                    WHERE
                        dev_rma_rma.name = %s
                        AND rma_line.purchase_id IS NOT NULL
                    GROUP BY
                        rma_line.product_id,
                        rma_line.tax_number
                """
            self.env.cr.execute(query, (no_return, no_return))
            return self.env.cr.fetchall()

        def fetch_related_ids(record_type, tax_number):
            if record_type == 'return_import_purchase':
                invoice_query = """
                    SELECT id, purchase_order_id
                    FROM account_move 
                    WHERE l10n_id_tax_number = %s AND move_type = 'in_invoice'
                """
                picking_query = """
                    SELECT sp.id
                    FROM stock_picking sp
                    JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                    WHERE sp.purchase_id = %s AND spt.code = 'incoming'
                    LIMIT 1
                """
            elif record_type == 'return_import_sale':
                invoice_query = """
                    SELECT am.id, rel.sale_order_id
                    FROM account_move am
                    JOIN account_move_sale_order_rel rel ON am.id = rel.account_move_id
                    WHERE am.l10n_id_tax_number = %s AND am.move_type = 'out_invoice'
                """
                picking_query = """
                    SELECT sp.id
                    FROM stock_picking sp
                    JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                    WHERE sp.sale_id = %s AND spt.code = 'outgoing'
                    LIMIT 1
                """
                
            self.env.cr.execute(invoice_query, (tax_number,))
            invoice_result = self.env.cr.fetchone()
            if not invoice_result:
                raise UserError("Invoice not found with the no faktur pajak.")
            
            invoice_id, order_id = invoice_result
            self.env.cr.execute(picking_query, (order_id,))
            picking_result = self.env.cr.fetchone()
            if not picking_result:
                raise UserError("Picking not found with the selected order.")
            
            return invoice_id, order_id, picking_result[0]

        def insert_rma_data(record_type, rma_id, updated_results):
            if record_type == 'return_import_purchase':
                query = """
                    INSERT INTO dev_rma_line (product_id, rma_id, return_qty, delivered_qty, account_move_id, purchase_id, picking_id, tax_number, create_uid, create_date,action,is_done_bill)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'refund', False)
                """
            elif record_type == 'return_import_sale':
                query = """
                    INSERT INTO dev_rma_line (product_id, rma_id, return_qty, delivered_qty, account_move_id, sale_id, picking_id, tax_number, create_uid, create_date,action,is_done_bill)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'refund', False)
                """
            insert_values = [(row[0], rma_id, row[1], row[2], row[4], row[5], row[6], row[3], self._uid, fields.Datetime.now()) for row in updated_results]
            self.env.cr.executemany(query, insert_values)

        location_id = fetch_location(self.record_type, self.location_id.id)
        no_return = self.no_return
        is_po = self.record_type == 'return_import_purchase'
        
        results = fetch_rma_line_data(self.record_type, no_return)
        if not results:
            raise UserError("No data found for the given Return Document Number.")

        updated_results = []
        for row in results:
            tax_number = row[3]
            invoice_id, order_id, picking_id = fetch_related_ids(self.record_type, tax_number)
            updated_row = row + (invoice_id, order_id, picking_id)
            updated_results.append(updated_row)
        
        name = self.return_order_sequence()
        branch_id = self.warehouse_id.branch_id.id

        self.env.cr.execute("""
            INSERT INTO dev_rma_rma (partner_id, warehouse_id, location_id, operation_type_id, is_po, create_uid, create_date, write_uid, write_date, date, deadline_date, user_id, company_id, name, state, branch_id, action_type, is_done_bill)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, NOW(), NOW(), NOW(), %s, %s, %s, 'draft', %s, 'refund', False)
            RETURNING id
        """, (self.partner_id.id, self.warehouse_id.id, self.location_id.id, location_id, is_po, self._uid, self._uid, self._uid, self.env.company.id, name, branch_id))
        rma_id = self.env.cr.fetchone()[0]

        insert_rma_data(self.record_type, rma_id, updated_results)
        self.state = 'done'

        if rma_id:
            rma_obj = self.env['dev.rma.rma'].browse(rma_id)
            for line in rma_obj.rma_lines:
                line.onchange_product_id()
                line.onchange_picking_id()
                
                if line.picking_id:
                    if self.record_type == 'return_import_purchase':
                        for move_line in line.picking_id.move_ids_without_package:
                            if line.product_id == move_line.product_id:
                             line.move_id = move_line.id

                    elif self.record_type == 'return_import_sale':
                        for move_line in line.picking_id.move_line_ids_without_package:
                            if line.product_id == move_line.product_id:
                                line.move_id = move_line.move_id.id

    def return_order_sequence(self):
        short_name = self.env.company.short_name
        if not short_name:
            raise UserError(_("Set the short name for company"))

        if self.record_type == 'return_import_purchase':
            sequence = self.env['ir.sequence'].next_by_code('dev.rma.rma.po')
            if not sequence:
                self.env['ir.sequence'].create({
                    'name': 'Return Purchase Order',
                    'code': 'dev.rma.rma.po',
                    'padding': 5,
                })
                sequence = self.env['ir.sequence'].next_by_code('dev.rma.rma.po')
            seq_name = 'RPO/' + short_name + '/' + self.warehouse_id.code + '/' + sequence
        elif self.record_type == 'return_import_sale':
            sequence = self.env['ir.sequence'].next_by_code('dev.rma.rma.so')
            if not sequence:
                self.env['ir.sequence'].create({
                    'name': 'Return Sale Order',
                    'code': 'dev.rma.rma.so',
                    'padding': 5,
                })
                sequence = self.env['ir.sequence'].next_by_code('dev.rma.rma.so')
            seq_name = 'RSO/' + short_name + '/' + self.warehouse_id.code + '/' + sequence

        return seq_name

    def create_purchase_order_line(self, po_ref, product_data, product_template_data, warehouse_data, analytic_data, row, date_planned, tax_ids, product_price):
        product_name = str(product_data.get('product_display_name')).replace("'", "''")
        
        po_id = self.env['purchase.order'].browse(po_ref.get('id'))
        conn = self.env.cr
        operation = 'insert'
        table_name = 'purchase_order_line'
        data_dict = {
            'name': product_name,
            'company_id': self.env.company.id,
            'product_id': product_data.get('id'),
            'price_unit': product_price,
            'product_qty': row[8],
            'product_uom_qty': row[8],
            'order_id': po_ref.get('id'),
            'product_uom': product_template_data.get('uom_id'),
            'date_planned': date_planned,
            'discount_method': 'fix',
            'destination_warehouse_id': warehouse_data.get('id'),
            'currency_id': self.env.user.company_id.currency_id.id,
            'partner_id': po_id.partner_id.id,
            'taxes_id': [(6, 0, tax_ids)],
            'analytic_tag_ids': [(6, 0, [analytic_data.get('id')])],
        }
        m2m_relations = {
            'taxes_id': ('account_tax_purchase_order_line_rel', 'purchase_order_line_id', 'account_tax_id'),
            'analytic_tag_ids': ('account_analytic_tag_purchase_order_line_rel', 'purchase_order_line_id', 'account_analytic_tag_id'),
        }

        self.dict_to_sql(conn, table_name, data_dict, operation, m2m_relations=m2m_relations)

        return True

    def purchase_order_sequence(self,row):
        
        seq_name = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq.goods')
        type_order = 'is_goods_orders'
        if row[13]:
            seq_name = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq.services')
            type_order = 'is_services_orders'
        elif row[14]:
            seq_name = self.env['ir.sequence'].next_by_code('purchase.order.seqs.a')
            type_order = 'is_assets_orders'
        elif row[15]:
            seq_name = self.env['ir.sequence'].next_by_code('purchase.order.seqs.r')
            type_order = 'is_rental_orders'


        return seq_name, type_order

    def button_action_draft(self):
        self.state = "draft"

    def create_pos_order(self,sheet):
        pos_orders = []
        try:
            cnt = 0
            for row in range(sheet.nrows):
                row = sheet.row_values(row)

                # Skip Column Header
                if cnt == 0:
                    cnt += 1
                    continue

                # Check Product Availability
                query = "select id,product_display_name,product_tmpl_id from product_product where barcode = '%s' " % (str(row[5]),)
                self.env.cr.execute(query)
                product_data = self._cr.dictfetchone()

                # Check Customer Availability
                partner_query = "select id from res_partner where customer_sequence = '%s' " % (str(row[3]),)
                self.env.cr.execute(partner_query)
                vendor_data = self._cr.dictfetchone()


                # Check Location
                location_query = "select id from stock_location where complete_name = '%s' " % (str(row[1]),)
                self.env.cr.execute(location_query)
                location_data = self._cr.dictfetchone()


                # Check Session
                session_query = "select id from pos_session where name = '%s' " % (str(row[2]),)
                self.env.cr.execute(session_query)
                session_data = self._cr.dictfetchone()

                # Check Pricelist
                pricelist_query = "select id from product_pricelist where name = '%s' " % (str(row[9]),)
                self.env.cr.execute(pricelist_query)
                pricelist_data = self._cr.dictfetchone()


                not_updated_data = ""
                if not product_data:
                    not_updated_data = not_updated_data + "\n [ " + str(
                        row[6]) + " ] barcode related product not available in the system"

                if not session_data:
                    not_updated_data = not_updated_data + "\n [ " + str(
                        row[2]) + " ] session not available in the system"

                if not vendor_data:
                    not_updated_data += "\n [ " + str(row[1]) + " ] customer not available in the system"

                if not location_data:
                    not_updated_data += "\n [ " + str(row[5]) + " ] location not available in the system"

                if not pricelist_data:
                    not_updated_data += "\n [ " + str(row[9]) + " ] pricelist not available in the system"


                # check if pos order already exist
                check_order_query = "select id from pos_order where import_reference = '%s' " % (str(row[0]),)
                self.env.cr.execute(check_order_query)
                pos_order_data = self._cr.dictfetchone()


                if not pos_order_data:
                    date_order = xlrd.xldate_as_datetime(row[4], 0)
                    if date_order:
                        date_order = str(date_order).split(" ")[0]

                    pos_order_seq = self.env['ir.sequence'].next_by_code('pos.order')

                    picking_type_query = "select id from stock_picking_type where default_location_src_id = %d and sequence_code = 'OUT'" % (
                        location_data.get('id'))
                    self.env.cr.execute(picking_type_query)
                    picking_type_data = self._cr.dictfetchone()

                    insert_pos_order_query = "INSERT INTO pos_order(name,pos_reference,import_reference,partner_id,picking_type_id,date_order,session_id,currency_id,company_id," \
                                             "sale_journal,state,amount_tax,amount_total,amount_paid,amount_return,pricelist_id) " \
                                            "VALUES('%s','%s','%s', %s,%s,'%s',%s,%s,%s,%s,'%s',%s,%s,%s,%s,%s) RETURNING id;" % \
                                            (pos_order_seq,pos_order_seq, row[0], vendor_data.get('id'), picking_type_data.get('id'),
                                             date_order,session_data.get('id'),self.env.user.company_id.currency_id.id,
                                             self.env.user.company_id.id, 1,'draft',row[8],0,0,0,pricelist_data.get('id'))

                    self.env.cr.execute(insert_pos_order_query)
                    pos_ref = self._cr.dictfetchone()
                    pos_orders.append(pos_ref.get('id'))

                    product_name = str(product_data.get('product_display_name')).replace("'", "''")

                    product_template_query = "select uom_id from product_template where id = %s " % (
                        product_data.get('product_tmpl_id'),)
                    self.env.cr.execute(product_template_query)
                    product_template_data = self._cr.dictfetchone()

                    insert_po_line_query = "INSERT INTO pos_order_line(name,full_product_name,product_id,qty,price_unit,order_id,product_uom_id,uom_id,company_id,price_subtotal,price_subtotal_incl,item_state) VALUES ('%s','%s',%s, %s, %s, %s, %s, %s, %s,%s,%s,'%s') RETURNING id;" % \
                                           (product_name,product_name,product_data.get('id'), row[6], row[7], pos_ref.get('id'),
                                            product_template_data.get('uom_id'), product_template_data.get('uom_id'),self.env.user.company_id.id,0,0,'ordered')

                    self.env.cr.execute(insert_po_line_query)
                    pos_line_id = self._cr.dictfetchone()
                    self.env['pos.order.line'].browse(pos_line_id.get('id'))._onchange_qty()

                else:
                    product_name = str(product_data.get('product_display_name')).replace("'", "''")

                    product_template_query = "select uom_id from product_template where id = %s " % (
                        product_data.get('product_tmpl_id'),)
                    self.env.cr.execute(product_template_query)
                    product_template_data = self._cr.dictfetchone()

                    insert_po_line_query = "INSERT INTO pos_order_line(name,full_product_name,product_id,qty,price_unit,order_id,product_uom_id,uom_id,company_id,price_subtotal,price_subtotal_incl,item_state) VALUES ('%s','%s',%s, %s, %s, %s, %s, %s, %s,%s,%s,'%s') RETURNING id;" % \
                                           (product_name, product_name , product_data.get('id'), row[6], row[7], pos_order_data.get('id'),
                                            product_template_data.get('uom_id'), product_template_data.get('uom_id'),
                                            self.env.user.company_id.id, 0, 0, 'ordered')


                    self.env.cr.execute(insert_po_line_query)
                    pos_line_id = self._cr.dictfetchone()
                    self.env['pos.order.line'].browse(pos_line_id.get('id'))._onchange_qty()


        except Exception as e:
            error_message = tools.ustr(e)
            pos_orders = []
            self.env.cr.rollback()
            self.error_message = error_message + "\n " + not_updated_data
            self.state = "failed"

        if self.state != "failed":
            for pos in self.env['pos.order'].browse(pos_orders):
                pos._onchange_amount_all()
            self.state = 'done'

    def create_product_template(self,sheet):
        try:
            product_tmpl_ids = []
            cnt = 0
            row_count = sheet.nrows
            total_cnt = 1
            for row in range(sheet.nrows):
                row = sheet.row_values(row)

                # Skip Column Header
                if cnt == 0:
                    cnt += 1
                    continue

                # Product Category
                categ_query = "select id from product_category where name = '%s' " % (str(row[5]),)
                self.env.cr.execute(categ_query)
                category_data = self._cr.dictfetchone()


                # POS  Category
                pos_categ_query = "select id from pos_category where name = '%s' " % (str(row[6]),)
                self.env.cr.execute(pos_categ_query)
                pos_category_data = self._cr.dictfetchone()

                # Uom
                uom_query = "select id from uom_uom where name = '%s' " % (str(row[8]),)
                self.env.cr.execute(uom_query)
                uom_data = self._cr.dictfetchone()

                not_updated_data = ""
                if not category_data:
                    not_updated_data = not_updated_data + "\n [ " + str(
                        row[5]) + " ] product category not available in the system"

                if not pos_category_data:
                    not_updated_data = not_updated_data + "\n [ " + str(
                        row[6]) + " ] pos product category not available in the system"

                if not uom_data:
                    not_updated_data = not_updated_data + "\n [ " + str(
                        row[8]) + " ] unit of measure not available in the system"

                product_name = str(row[0]).replace("'", "''")
                display_name = str(row[0]).replace("'", "''")
                insert_product_template_query = ""
                active = True if row[9] else False
                sale_ok = True if row[10] else False
                purchase_ok = True if row[11] else False
                available_in_pos = True if row[12] else False
                tracking_product = str(row[13])
                if tracking_product not in ['none','lot','serial']:
                    not_updated_data = not_updated_data + "\n [ " + str(
                        row[8]) + " ] No Tracking Product found, please set only this value e.x none,lot,serial"

                if pos_category_data:
                    insert_product_template_query = "INSERT INTO product_template(name,description,default_code,type,categ_id,pos_categ_id,list_price,uom_id,uom_po_id,active,sale_ok,purchase_ok,available_in_pos,tracking,purchase_line_warn,sale_line_warn) " \
                                            "VALUES('%s','%s','%s','%s',%s,%s,%s,%s,%s,%s,%s,%s,%s,'%s','no-message','no-message') RETURNING id;" % \
                                            (product_name,display_name,row[3],row[4],category_data.get('id'),pos_category_data.get('id'),row[7],uom_data.get('id'),uom_data.get('id'),active,sale_ok,purchase_ok,available_in_pos,tracking_product)
                else:
                    insert_product_template_query = "INSERT INTO product_template(name,description,default_code,type,categ_id,list_price,uom_id,uom_po_id,active,sale_ok,purchase_ok,available_in_pos,tracking,purchase_line_warn,sale_line_warn) " \
                                                    "VALUES('%s','%s','%s','%s',%s,%s,%s,%s,%s,%s,%s,%s,'%s','no-message','no-message') RETURNING id;" % \
                                                    (
                                                    product_name, display_name, row[3], row[4], category_data.get('id'),
                                                    row[7], uom_data.get('id'),uom_data.get('id'), active,sale_ok,purchase_ok,available_in_pos,tracking_product)


                self.env.cr.execute(insert_product_template_query)
                template_data = self._cr.dictfetchone()
                product_tmpl_ids.append(template_data.get('id'))

                full_product_name = product_name
                if row[3]:
                    full_product_name = "["+str(row[3])+"] "+product_name

                insert_product_product_query = "INSERT INTO product_product(default_code,active,product_tmpl_id,barcode,categ_id,product_display_name) " \
                                       "VALUES ('%s',TRUE,%s, '%s', %s, '%s')" % \
                                       (row[3],template_data.get('id'),row[2],category_data.get('id'),full_product_name)

                self.env.cr.execute(insert_product_product_query)
                total_cnt += 1

        except Exception as e:
            error_message = tools.ustr(e)
            pos_orders = []
            self.env.cr.rollback()
            self.error_message = error_message + "\n " + not_updated_data
            self.state = "failed"

        if total_cnt == row_count:
            self.state = 'done'
            products = self.env['product.template'].search([('id','in', product_tmpl_ids), ('default_code','=', ''), ('categ_id.is_generate_product_code','=', True)])
            if products:
                for product in products:
                    product._compute_default_code()
            



    def create_receiving_notes(self,sheet):
        try:
            cnt = 0
            row_count = sheet.nrows
            total_cnt = 1
            for row in range(sheet.nrows):
                row = sheet.row_values(row)

                # Skip Column Header
                if cnt == 0:
                    cnt += 1
                    continue

                # Check Product Availability
                query = "select id,product_display_name,product_tmpl_id from product_product where barcode = '%s' " % (str(row[5]),)
                self.env.cr.execute(query)
                product_data = self._cr.dictfetchone()
                oum_id = False
                if product_data:
                    oum_id = self.env['product.product'].browse(product_data.get('id')).uom_id.id

                # Check Vendor Availability
                partner_query = "select id from res_partner where vendor_sequence = '%s' " % (str(row[1]),)
                self.env.cr.execute(partner_query)
                vendor_data = self._cr.dictfetchone()

                # Check Branch
                branch_query = "select id from res_branch where name = '%s' " % (str(row[3]),)
                self.env.cr.execute(branch_query)
                branch_data = self._cr.dictfetchone()

                # Check Location
                location_query = "select id from stock_location where complete_name = '%s' " % (str(row[4]),)
                self.env.cr.execute(location_query)
                location_dest_id = self._cr.dictfetchone()

                not_updated_data = ""
                if not product_data:
                    not_updated_data = not_updated_data + "\n [ " + str(
                        row[5]) + " ] barcode related product not available in the system"

                if not vendor_data:
                    not_updated_data += "\n [ " + str(row[3]) + " ] vendor not available in the system"

                if not location_dest_id:
                    not_updated_data += "\n [ " + str(row[1]) + " ] location not available in the system"

                if not branch_data:
                    not_updated_data += "\n [ " + str(row[4]) + " ] branch not available in the system"
                    
                date = create_date = scheduled_date = xlrd.xldate.xldate_as_datetime(row[2], 0)
                
                user_id = create_uid = self.env.user.id
                move_type = 'direct'
                state = 'draft'
                sequence_in_id = self.env['ir.sequence'].search([('code','=','stock.picking.receiving.notes.al.fresh')], limit=1)
                sequence_compute = sequence_in_id.next_by_id()
                company_code = self.env['res.company'].browse(self.env.company.id).short_name or "None"
                stock_location = self.env['stock.location'].browse(location_dest_id.get('id'))
                warehouse_code = stock_location.warehouse_id.code
                now = fields.datetime.now()
                seq_code = sequence_compute[-6:]
                name = company_code + '/' + warehouse_code+ '/' + 'IN' + '/' + now.strftime('%d') + '/' + now.strftime('%b').upper() + '/' + now.strftime('%y')+ '/' + seq_code

                if product_data and vendor_data and location_dest_id and branch_data:
                    self.env.cr.execute("SELECT id FROM stock_picking WHERE import_reference = %s LIMIT 1", (row[0],))
                    picking = self.env.cr.fetchone()

                    # 2. Insert/Update Stock Picking
                    if picking:
                        picking_id = picking[0]
                    else:
                        self.env.cr.execute("""
                            INSERT INTO stock_picking (name, import_reference, partner_id, branch_id, company_id, origin, location_id, location_dest_id, picking_type_id, move_type, state, scheduled_date, create_date, date, create_uid, active, user_id, need_to_create_je)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                        """, (name, row[0], vendor_data.get('id'), branch_data.get('id'), self.env.company.id, row[7], 4, location_dest_id.get('id'), self.env.ref('stock.picking_type_in').id, move_type, state, scheduled_date, create_date, date, create_uid, True, user_id, False))
                        picking_id = self.env.cr.fetchone()[0]

                    # 3. Insert Stock Move
                    self.env.cr.execute("""
                        INSERT INTO stock_move (name, product_id, product_uom_qty, product_uom, location_id, location_dest_id, picking_id, create_date, date, create_uid, company_id, procure_method, quantity_done, state)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (product_data.get('product_display_name'), product_data.get('id'), row[6], oum_id, 4, location_dest_id.get('id'),picking_id, create_date, date, create_uid, self.env.company.id, 'make_to_stock', row[6], 'draft'))
                    
                total_cnt += 1
            # Commit transactions
            self.env.cr.commit()
                
        except Exception as e:
            error_message = tools.ustr(e)
            pos_orders = []
            self.env.cr.rollback()
            self.error_message = error_message + "\n " + not_updated_data
            self.state = "failed"

        if total_cnt == row_count:
            self.state = 'done'
            if picking_id:
                picking = self.env['stock.picking'].browse(picking_id)
                picking.onchange_location_id()
                for line in picking.move_ids_without_package:
                    line.onchange_product_id()

    def create_delivery_orders(self,sheet):
        try:
            cnt = 0
            row_count = sheet.nrows
            total_cnt = 1
            for row in range(sheet.nrows):
                row = sheet.row_values(row)

                # Skip Column Header
                if cnt == 0:
                    cnt += 1
                    continue

                # Check Product Availability
                query = "select id,product_display_name,product_tmpl_id from product_product where barcode = '%s' " % (str(row[5]),)
                self.env.cr.execute(query)
                product_data = self._cr.dictfetchone()
                oum_id = False
                if product_data:
                    oum_id = self.env['product.product'].browse(product_data.get('id')).uom_id.id

                # Check Vendor Availability
                partner_query = "select id from res_partner where vendor_sequence = '%s' " % (str(row[1]),)
                self.env.cr.execute(partner_query)
                vendor_data = self._cr.dictfetchone()

                # Check Branch
                branch_query = "select id from res_branch where name = '%s' " % (str(row[3]),)
                self.env.cr.execute(branch_query)
                branch_data = self._cr.dictfetchone()

                # Check Location
                location_query = "select id from stock_location where complete_name = '%s' " % (str(row[4]),)
                self.env.cr.execute(location_query)
                location_id = self._cr.dictfetchone()

                not_updated_data = ""
                if not product_data:
                    not_updated_data = not_updated_data + "\n [ " + str(
                        row[5]) + " ] barcode related product not available in the system"

                if not vendor_data:
                    not_updated_data += "\n [ " + str(row[3]) + " ] vendor not available in the system"

                if not location_id:
                    not_updated_data += "\n [ " + str(row[1]) + " ] location not available in the system"

                if not branch_data:
                    not_updated_data += "\n [ " + str(row[4]) + " ] branch not available in the system"
                    
                date = create_date = scheduled_date = xlrd.xldate.xldate_as_datetime(row[2], 0)
                
                user_id = create_uid = self.env.user.id
                move_type = 'direct'
                state = 'draft'
                sequence_in_id = self.env['ir.sequence'].search([('code','=','stock.picking.delivery.order.al.fresh')], limit=1)
                sequence_compute = sequence_in_id.next_by_id()
                company_code = self.env['res.company'].browse(self.env.company.id).short_name or "None"
                stock_location = self.env['stock.location'].browse(location_id.get('id'))
                warehouse_code = stock_location.warehouse_id.code
                now = fields.datetime.now()
                seq_code = sequence_compute[-6:]
                name = company_code + '/' + warehouse_code+ '/' + 'OUT' + '/' + now.strftime('%d') + '/' + now.strftime('%b').upper() + '/' + now.strftime('%y')+ '/' + seq_code

                if product_data and vendor_data and location_id and branch_data:
                    self.env.cr.execute("SELECT id FROM stock_picking WHERE import_reference = %s LIMIT 1", (row[0],))
                    picking = self.env.cr.fetchone()

                    # 2. Insert/Update Stock Picking
                    if picking:
                        picking_id = picking[0]
                    else:
                        self.env.cr.execute("""
                            INSERT INTO stock_picking (name, import_reference, partner_id, branch_id, company_id, origin, location_id, location_dest_id, picking_type_id, move_type, state, scheduled_date, create_date, date, create_uid, active, user_id, need_to_create_je)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                        """, (name, row[0], vendor_data.get('id'), branch_data.get('id'), self.env.company.id, row[7], location_id.get('id'), 5, self.env.ref('stock.picking_type_in').id, move_type, state, scheduled_date, create_date, date, create_uid, True, user_id, False))
                        picking_id = self.env.cr.fetchone()[0]

                    # 3. Insert Stock Move
                    self.env.cr.execute("""
                        INSERT INTO stock_move (name, product_id, product_uom_qty, product_uom, location_id, location_dest_id, picking_id, create_date, date, create_uid, company_id, procure_method, quantity_done, state)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (product_data.get('product_display_name'), product_data.get('id'), row[6], oum_id, location_id.get('id'), 5, picking_id, create_date, date, create_uid, self.env.company.id, 'make_to_stock', row[6], 'draft'))

                total_cnt += 1
            # Commit transactions
            self.env.cr.commit()

        except Exception as e:
            error_message = tools.ustr(e)
            pos_orders = []
            self.env.cr.rollback()
            self.error_message = error_message + "\n " + not_updated_data
            self.state = "failed"

        if total_cnt == row_count:
            self.state = 'done'
            if picking_id:
                picking = self.env['stock.picking'].browse(picking_id)
                picking.onchange_location_id()
                for line in picking.move_ids_without_package:
                    line.onchange_product_id()

    def dict_to_sql(self, conn, table_name, data_dict, operation, condition=None, m2m_relations=None):
        if m2m_relations is None:
            m2m_relations = {}

        regular_data = {k: v for k, v in data_dict.items() if not isinstance(v, list)}
        m2m_commands = {k: v for k, v in data_dict.items() if isinstance(v, list) and k in m2m_relations}

        main_record_id = None

        # Handle regular data
        if operation.lower() == 'insert':
            if regular_data:
                keys = ', '.join(regular_data.keys())
                values_placeholder = ', '.join(['%s'] * len(regular_data))
                sql_query = f"INSERT INTO {table_name} ({keys}) VALUES ({values_placeholder}) RETURNING id"
                conn.execute(sql_query, tuple(regular_data.values()))
                main_record_id = conn.fetchone()[0]  # Fetch the new ID
        elif operation.lower() == 'update':
            if regular_data:
                set_clause = ', '.join([f"{key} = %s" for key in regular_data.keys()])
                sql_query = f"UPDATE {table_name} SET {set_clause} WHERE {condition} RETURNING id"
                conn.execute(sql_query, tuple(regular_data.values()))
                main_record_id = conn.fetchone()[0]  # Fetch the updated ID
        else:
            raise ValueError("Operation must be either 'insert' or 'update'")

        # Handle Many2Many commands
        for field, commands in m2m_commands.items():
            relation_info = m2m_relations.get(field)
            if relation_info:
                relation_table, from_field, to_field = relation_info
                for command in commands:
                    cmd_type, record_id, ids = command
                    if cmd_type == 4 and record_id is not None:  # Add existing record
                        m2m_query = f"INSERT INTO {relation_table} ({from_field}, {to_field}) VALUES (%s, %s)"
                        conn.execute(m2m_query, (main_record_id, record_id))
                    elif cmd_type == 3 and record_id is not None:  # Remove record without deleting
                        m2m_query = f"DELETE FROM {relation_table} WHERE {from_field} = %s AND {to_field} = %s"
                        conn.execute(m2m_query, (main_record_id, record_id))
                    elif cmd_type == 5:  # Remove all records
                        m2m_query = f"DELETE FROM {relation_table} WHERE {from_field} = %s"
                        conn.execute(m2m_query, (main_record_id,))
                    elif cmd_type == 6:  # Replace all records
                        # Remove all existing records first
                        m2m_query = f"DELETE FROM {relation_table} WHERE {from_field} = %s"
                        conn.execute(m2m_query, (main_record_id,))
                        # Add new records if any
                        if ids:
                            for new_id in ids:
                                m2m_query = f"INSERT INTO {relation_table} ({from_field}, {to_field}) VALUES (%s, %s)"
                                conn.execute(m2m_query, (main_record_id, new_id))

        return main_record_id  # Return the ID of the main record for further use


ImportRecordData()