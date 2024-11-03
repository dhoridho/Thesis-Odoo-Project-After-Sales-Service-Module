-- DROP FUNCTION public.get_inventory_turnover_ratio_data(integer[], integer[], integer[], integer[], date, date);

CREATE OR REPLACE FUNCTION public.get_inventory_turnover_ratio_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date
)
RETURNS TABLE(
    company_id integer, company_name character varying,
    product_id integer, product_name character varying,
    product_category_id integer, category_name character varying,
    warehouse_id integer, warehouse_name character varying,
    opening_stock numeric, closing_stock numeric,
    average_stock numeric, sales numeric,
    turnover_ratio numeric
) AS
$BODY$
BEGIN
    Return Query
    Select
        t_data.*,
        case when t_data.average_stock = 0.0 then 1 else
            round(t_data.sales / t_data.average_stock, 2)
        end as turnover_ratio
    From
    (
        Select
            T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name,
            T.warehouse_id, T.warehouse_name, T.opening_stock, T.closing, coalesce(Round((T.opening_stock + T.closing) / 2.0, 2)) as average_stock,
            (T.sales - T.sales_return + T.production_out) as sales
        from get_products_stock_movements(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date) T
    )t_data;

END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;