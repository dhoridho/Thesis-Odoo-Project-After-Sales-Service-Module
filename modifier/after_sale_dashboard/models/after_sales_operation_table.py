from odoo import models, fields, api, tools


class AfterSalesMonthlyCount(models.Model):
    _name = 'after.sales.monthly.report'
    _description = 'After Sales Monthly report'
    _auto = False  # This tells Odoo that this is a database view, not a regular table

    month_year = fields.Char(string='Month', readonly=True)
    year = fields.Char(string='Year', readonly=True)
    month_name = fields.Char(string='Month Name', readonly=True)
    service_request_count = fields.Integer(string='Service Requests', readonly=True)
    warranty_claim_count = fields.Integer(string='Warranty Claims', readonly=True)
    sale_return_count = fields.Integer(string='Sale Returns', readonly=True)
    def init(self):
        """
        Initialize the SQL view. This method is called when the view is created or updated.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER() AS id,
                    COALESCE(sr.request_month, wc.month_year, rma.month_year) AS month_year,
                    COALESCE(SPLIT_PART(sr.request_month, '-', 1), wc.year, rma.year) AS year,
                    COALESCE(
                        TRIM(TO_CHAR(TO_DATE(SPLIT_PART(sr.request_month, '-', 2), 'MM'), 'Month')),
                        TRIM(wc.month_name),
                        TRIM(rma.month_name)
                    ) AS month_name,
                    COALESCE(sr.count, 0) AS service_request_count,
                    COALESCE(wc.count, 0) AS warranty_claim_count,
                    COALESCE(rma.count, 0) AS sale_return_count
                FROM
                    (SELECT request_month, COUNT(id) AS count 
                     FROM service_request WHERE request_month IS NOT NULL GROUP BY request_month) sr
                FULL OUTER JOIN
                    (SELECT TO_CHAR(claim_date, 'YYYY-MM') AS month_year,
                            EXTRACT(YEAR FROM claim_date)::text AS year,
                            TO_CHAR(claim_date, 'Month') AS month_name,
                            COUNT(id) AS count 
                     FROM warranty_claim WHERE claim_date IS NOT NULL 
                     GROUP BY TO_CHAR(claim_date, 'YYYY-MM'), EXTRACT(YEAR FROM claim_date), TO_CHAR(claim_date, 'Month')
                    ) wc ON sr.request_month = wc.month_year
                FULL OUTER JOIN
                    (SELECT TO_CHAR(create_date, 'YYYY-MM') AS month_year,
                            EXTRACT(YEAR FROM create_date)::text AS year,
                            TO_CHAR(create_date, 'Month') AS month_name,
                            COUNT(id) AS count 
                     FROM dev_rma_rma WHERE create_date IS NOT NULL 
                     GROUP BY TO_CHAR(create_date, 'YYYY-MM'), EXTRACT(YEAR FROM create_date), TO_CHAR(create_date, 'Month')
                    ) rma ON COALESCE(sr.request_month, wc.month_year) = rma.month_year
                ORDER BY month_year DESC
            )
        """ % (self._table,))


class AfterSalesProductReport(models.Model):
    _name = 'after.sales.product.report'
    _description = 'After Sales Product Report'
    _auto = False  # This will be a SQL view

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    service_request_count = fields.Integer(string='Service Requests', readonly=True)
    warranty_claim_count = fields.Integer(string='Warranty Claims', readonly=True)
    total_count = fields.Integer(string='Total Requests', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH product_stats AS (
                    -- Service Request products
                    SELECT 
                        product_id,
                        COUNT(id) AS service_request_count,
                        0 AS warranty_claim_count
                    FROM service_request
                    WHERE product_id IS NOT NULL
                    GROUP BY product_id

                    UNION ALL

                    -- Warranty Claim products
                    SELECT 
                        product_id,
                        0 AS service_request_count,
                        COUNT(id) AS warranty_claim_count
                    FROM warranty_claim
                    WHERE product_id IS NOT NULL
                    GROUP BY product_id
                )
                SELECT
                    ROW_NUMBER() OVER() AS id,
                    product_id,
                    SUM(service_request_count) AS service_request_count,
                    SUM(warranty_claim_count) AS warranty_claim_count,
                    SUM(service_request_count + warranty_claim_count) AS total_count
                FROM product_stats
                GROUP BY product_id
                ORDER BY total_count DESC
            )
        """ % self._table)


class AfterSalesCSReport(models.Model):
    _name = 'after.sales.cs.report'
    _description = 'After Sales Customer Service Report'
    _auto = False  # This will be a SQL view

    responsible_id = fields.Many2one('res.users', string='Customer Service', readonly=True)
    service_request_count = fields.Integer(string='Service Requests', readonly=True)
    warranty_claim_count = fields.Integer(string='Warranty Claims', readonly=True)
    total_count = fields.Integer(string='Total Requests', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH cs_stats AS (
                    -- Service Request products
                    SELECT 
                        responsible_id,
                        COUNT(id) AS service_request_count,
                        0 AS warranty_claim_count
                    FROM service_request
                    WHERE responsible_id IS NOT NULL
                    GROUP BY responsible_id

                    UNION ALL

                    -- Warranty Claim products
                    SELECT 
                        responsible_id,
                        0 AS service_request_count,
                        COUNT(id) AS warranty_claim_count
                    FROM warranty_claim
                    WHERE responsible_id IS NOT NULL
                    GROUP BY responsible_id
                )
                SELECT
                    ROW_NUMBER() OVER() AS id,
                    responsible_id,
                    SUM(service_request_count) AS service_request_count,
                    SUM(warranty_claim_count) AS warranty_claim_count,
                    SUM(service_request_count + warranty_claim_count) AS total_count
                FROM cs_stats
                GROUP BY responsible_id
                ORDER BY total_count DESC
            )
        """ % self._table)


