-- DROP FUNCTION public.get_inventory_fsn_analysis_report(integer[], integer[], integer[], integer[], date, date, text);

CREATE OR REPLACE FUNCTION public.get_inventory_fsn_analysis_report(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date,
    IN stock_movement_type text
)
RETURNS TABLE(
    company_id integer, company_name character varying,
    product_id integer, product_name character varying,
    product_category_id integer, category_name character varying,
    warehouse_id integer, warehouse_name character varying,
    opening_stock numeric, closing_stock numeric,
    average_stock numeric, sales numeric,
    turnover_ratio numeric, stock_movement text
) AS
$BODY$
BEGIN
    Return Query
    Select * From
    (
        Select
            t_data.*,
            case
                when t_data.turnover_ratio > 3 then 'Fast Moving'
                when t_data.turnover_ratio >= 1 and t_data.turnover_ratio <= 3 then 'Slow Moving'
                when t_data.turnover_ratio < 1 then 'Non Moving'
            end as stock_movement
        From
        (
            Select
                *
            from get_inventory_turnover_ratio_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date) T
        )t_data
    )report_data
    where
    1 = case when stock_movement_type = 'all' then 1
    else
        case when stock_movement_type = 'fast' then
            case when report_data.stock_movement = 'Fast Moving' then 1 else 0 end
        else
            case when stock_movement_type = 'slow' then
                case when report_data.stock_movement = 'Slow Moving' then 1 else 0 end
            else
                case when stock_movement_type = 'non' then
                    case when report_data.stock_movement = 'Non Moving' then 1 else 0 end
                else 0 end

            end
        end
    end;
END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;