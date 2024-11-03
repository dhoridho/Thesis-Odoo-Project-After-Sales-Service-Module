-- DROP FUNCTION public.get_inventory_fsn_xyz_analysis_report(integer[], integer[], integer[], integer[], date, date, text, text);

CREATE OR REPLACE FUNCTION public.get_inventory_fsn_xyz_analysis_report(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date,
    IN stock_movement_type text,
    IN stock_value_type text)
RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, average_stock numeric, sales numeric, turnover_ratio numeric, fsn_classification text, current_stock numeric, stock_value numeric, xyz_classification text, combine_classification text) AS
$BODY$
    BEGIN
        Return Query
        Select
            xyz.company_id, xyz.company_name, xyz.product_id, xyz.product_name, xyz.product_category_id, xyz.category_name,
            fsn.average_stock, fsn.sales, fsn.turnover_ratio, fsn.stock_movement as fsn_classification,
            xyz.current_stock, xyz.stock_value, xyz.analysis_category as xyz_classification,
            ((case
                when fsn.stock_movement = 'Fast Moving' then 'F'
                when fsn.stock_movement = 'Slow Moving' then 'S'
                when fsn.stock_movement = 'Non Moving' then 'N'
            end) ||  xyz.analysis_category)::text as combine_classification

        from
        (
            Select T1.*
            From get_inventory_xyz_analysis_data(company_ids, product_ids, category_ids, stock_value_type) T1
        ) xyz
            Inner Join
        (
            Select T.*
            From
            get_inventory_fsn_analysis_report(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, stock_movement_type) T
        ) fsn
            on xyz.product_id = fsn.product_id and xyz.company_id = fsn.company_id
        order by xyz.stock_value desc;
    END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;