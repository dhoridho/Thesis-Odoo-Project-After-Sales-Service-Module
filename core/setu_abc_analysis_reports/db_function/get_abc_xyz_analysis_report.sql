DROP FUNCTION IF EXISTS public.get_abc_xyz_analysis_report(integer[], integer[], integer[], date, date, text, text);
CREATE OR REPLACE FUNCTION public.get_abc_xyz_analysis_report(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN start_date date,
    IN end_date date,
    IN abc_classification_type text,
    IN stock_value_type text,
    IN except_line integer[])
RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, sales_qty numeric, sales_amount numeric, sales_amount_per numeric, cum_sales_amount_per numeric, abc_classification text, current_stock numeric, stock_value numeric, xyz_classification text, combine_classification text) AS
$BODY$
    BEGIN
        Return Query
    Select
    abc.company_id, abc.company_name, abc.product_id, abc.product_name, abc.product_category_id, abc.category_name,
    abc.sales_qty, abc.sales_amount, abc.sales_amount_per, abc.cum_sales_amount_per, abc.analysis_category,
    coalesce(xyz.current_stock,0) as current_stock, coalesce(xyz.stock_value,0) as stock_value,
    coalesce(xyz.analysis_category,'Z') as xyz_classification,
    (abc.analysis_category ||  coalesce(xyz.analysis_category,'Z'))::text as combine_classification
    from
    (
    Select T.* From
    get_abc_sales_analysis_data_by_company(company_ids, product_ids, category_ids, start_date, end_date, abc_classification_type, except_line) T
    ) abc
    Inner Join
    (
    Select T1.*
    From get_inventory_xyz_analysis_data(company_ids, product_ids, category_ids, stock_value_type) T1
    ) xyz
    on abc.product_id = xyz.product_id and abc.company_id = xyz.company_id

    order by abc.sales_amount desc;

    END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;
