from odoo import tools
from odoo import api, fields, models


class RFMYearlyAnalysisBySegment(models.Model):
    _name = "rfm.yearly.analysis.by.segment"
    _description = "RFM Yearly Analysis By Segment"
    _auto = False
    _order = 'calculation_year desc'

    calculation_year = fields.Text("Calculation Year", help="Display which year is selected for RFM calculation")
    segment_id = fields.Many2one("setu.rfm.segment", "RFM Segment")
    total_customers = fields.Integer("Total Customers")
    ratio = fields.Float("Customer Ratio")

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        _qry = """
            Select min(segment_id) as id,* from get_yearly_rfm_analysis_by_segment()
            group by calculation_year,segment_id,total_customers,ratio
        """

        return _qry

    def init(self):
        # self._table = rfm_yearly_analysis_by_segment
        sp_query = self.sp_get_yearly_rfm_analysis_by_segment()
        self.env.cr.execute(sp_query)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

    def sp_get_yearly_rfm_analysis_by_segment(self):
        query = """
        drop view if exists rfm_yearly_analysis_by_segment;
        DROP FUNCTION if exists public.get_yearly_rfm_analysis_by_segment();

CREATE OR REPLACE FUNCTION public.get_yearly_rfm_analysis_by_segment()
  RETURNS TABLE(calculation_year text, segment_id integer, total_customers bigint, ratio numeric) AS
$BODY$
    DECLARE
            beginning_year Integer := (Select EXTRACT(YEAR FROM Min(date_order)::TIMESTAMP) from sale_order)::Integer;
            ending_year Integer := (Select EXTRACT(YEAR FROM Max(date_order)::TIMESTAMP) from sale_order)::Integer;
        a Integer := beginning_year;

    BEGIN
        Drop Table if exists rfm_analysis_temp_table;
        CREATE TEMPORARY TABLE rfm_analysis_temp_table(
            calculation_year text,
            company_id integer, customer_id integer,
            total_orders integer, total_order_value numeric,
            days_from_last_purchase integer, recency integer,
            frequency integer, monetization integer,
            score character varying, score_id integer, segment_id integer
        );

        while a <= ending_year loop
            Insert into rfm_analysis_temp_table
            Select a::text,
                D.*
            from get_rfm_analysis_data('{}', (a ||'-01-01')::date, (a ||'-12-01')::date) D;
            a := a + 1;
        end loop;

        RETURN QUERY
        with all_data as (
            Select T.calculation_year, T.segment_id, count(T.customer_id) as total_customers from rfm_analysis_temp_table T
            group by T.calculation_year, T.segment_id
        ),
        total_customer as (
            Select d.calculation_year, sum(d.total_customers) as tc from all_data as d
            group by d.calculation_year
        )
        select ad.*,
        Round((ad.total_customers / (case when total_cust.tc >=1 then total_cust.tc else 1 end)) * 100, 2)
        from all_data ad inner join total_customer total_cust on total_cust.calculation_year = ad.calculation_year;

    END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;"""
        return query