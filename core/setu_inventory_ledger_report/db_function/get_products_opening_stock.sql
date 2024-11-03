DROP FUNCTION if EXISTS public.get_products_opening_stock(integer[], integer[], integer[], integer[], date, date);
CREATE OR REPLACE FUNCTION public.get_products_opening_stock(
IN company_ids integer[],
IN product_ids integer[],
IN category_ids integer[],
IN warehouse_ids integer[],
IN tr_start_date date,
IN tr_end_date date)
RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, opening_stock numeric) AS
$BODY$
    BEGIN
        RETURN QUERY
        Select
            cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name, sum(product_qty) as op_stock
        From
        (
            select
                T.company_id as cmp_id, T.company_name as cmp_name,
                T.product_id as p_id, T.product_name as prod_name,
                T.product_category_id as categ_id, T.category_name as cat_name,
                T.warehouse_id as wh_id, T.warehouse_name as ware_name,
                (product_qty * -1) as product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sales' ,tr_start_date, tr_end_date) T

            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                (product_qty * -1) as product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'purchase_return' ,tr_start_date, tr_end_date) T


            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                (product_qty * -1) as product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'production_out' ,tr_start_date, tr_end_date)T

            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                (product_qty * -1) as product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'internal_out' ,tr_start_date, tr_end_date) T

            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                (product_qty * -1) as product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'adjustment_out' ,tr_start_date, tr_end_date) T

            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                (product_qty * -1) as product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'transit_out' ,tr_start_date, tr_end_date) T

            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'purchase' ,tr_start_date, tr_end_date) T

            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sale_return' ,tr_start_date, tr_end_date) T

            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'transit_in' ,tr_start_date, tr_end_date) T


            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'adjustment_in' ,tr_start_date, tr_end_date) T

            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'production_in' ,tr_start_date, tr_end_date) T

            Union All

            select
                T.company_id as cmp_id, T.company_name,
                T.product_id as p_id, T.product_name,
                T.product_category_id as categ_id, T.category_name,
                T.warehouse_id as wh_id, T.warehouse_name,
                product_qty
            from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'internal_in' ,tr_start_date, tr_end_date) T
        )T
        group by cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name;
    END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;