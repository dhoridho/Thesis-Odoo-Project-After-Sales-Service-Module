-- DROP FUNCTION public.get_products_stock_movements(integer[], integer[], integer[], integer[], date, date);

CREATE OR REPLACE FUNCTION public.get_products_stock_movements(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date)
  RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, opening_stock numeric, sales numeric, sales_return numeric, purchase numeric, purchase_return numeric, internal_in numeric, internal_out numeric, adjustment_in numeric, adjustment_out numeric, production_in numeric, production_out numeric, transit_in numeric, transit_out numeric, closing numeric) AS
$BODY$
    DECLARE
        tr_start_date date;
        tr_end_date date;

BEGIN
    Drop Table if exists transaction_table;
    CREATE TEMPORARY TABLE transaction_table(
        company_id INT,
        company_name character varying,
        product_id INT,
        product_name character varying,
        product_category_id INT,
        category_name character varying,
        warehouse_id INT,
        warehouse_name character varying,
        opening_stock Numeric DEFAULT 0,
        sales Numeric DEFAULT 0,
        sales_return numeric DEFAULT 0,
        purchase Numeric DEFAULT 0,
        purchase_return numeric DEFAULT 0,
        internal_in Numeric DEFAULT 0,
        internal_out Numeric DEFAULT 0,
        adjustment_in Numeric DEFAULT 0,
        adjustment_out Numeric DEFAULT 0,
        production_in Numeric DEFAULT 0,
        production_out Numeric DEFAULT 0,
        transit_in Numeric DEFAULT 0,
        transit_out Numeric DEFAULT 0,
        closing Numeric DEFAULT 0
    );

    IF start_Date is not null then
        tr_start_date := '1900-01-01';
        tr_end_date := start_date - interval '1 day';
        Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, opening_stock)
        select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, T.opening_stock
        from get_products_opening_stock(company_ids, product_ids, category_ids, warehouse_ids, tr_start_date, tr_end_date) T;
    END IF;

    -- Sales
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, sales)
    select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sales', start_date, end_date)T;

    -- Sales Return
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, sales_return)
    select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'sales_return', start_date, end_date)T;

    -- Purchase
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, purchase)
    select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'purchase', start_date, end_date)T;

    -- Purchase Return
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, purchase_return)
    select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'purchase_return', start_date, end_date)T;

    -- Internal IN
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, internal_in)
    select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'internal_in', start_date, end_date)T;


    -- Internal Out
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, internal_out)
    select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'internal_out', start_date, end_date)T;

    -- Adjustment IN
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, adjustment_in)
    select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'adjustment_in', start_date, end_date)T;


    -- Adjustment Out
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, adjustment_out)
    select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'adjustment_out', start_date, end_date)T;


    -- Production IN
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, production_in)
    select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'production_in', start_date, end_date)T;


    -- Production Out
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, production_out)
    select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'production_out', start_date, end_date)T;


    -- Transit IN
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, transit_in)
    select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'transit_in', start_date, end_date)T;

    -- Transit Out
    Insert into transaction_table(company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, transit_out)
    select  T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, product_qty
    from get_stock_data(company_ids, product_ids, category_ids, warehouse_ids, 'transit_out', start_date, end_date)T;


    RETURN QUERY
    Select Tr_data.*,
        Tr_data.opening_stock - Tr_data.sales + Tr_data.sales_return + Tr_data.purchase - Tr_data.purchase_return
        + Tr_data.internal_in - Tr_data.internal_out + Tr_data.adjustment_in - Tr_data.adjustment_out
        + Tr_data.production_in - Tr_data.production_out + Tr_data.transit_in - Tr_data.transit_out as closing
    From
    (
        Select
            T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name,
            sum(T.opening_stock) as opening_stock,
            sum(T.sales) as sales,
            sum(T.sales_return) as sales_return,
            sum(T.purchase) as purchase,
            sum(T.purchase_return) as purchase_return,
            sum(T.internal_in) as internal_in,
            sum(T.internal_out) as internal_out,
            sum(T.adjustment_in) as adjustment_in,
            sum(T.adjustment_out) as adjustment_out,
            sum(T.production_in) as production_in,
            sum(T.production_out) as production_out,
            sum(T.transit_in) as transit_in,
            sum(T.transit_out) as transit_out
        From
            transaction_table T
        group by
            T.company_id, T.company_name, T.product_id, T.product_name,
            T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name
    )Tr_data;

END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;
