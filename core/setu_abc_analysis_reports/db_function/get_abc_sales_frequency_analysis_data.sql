DROP FUNCTION IF EXISTS public.get_abc_sales_frequency_analysis_data(integer[], integer[], integer[], integer[], date, date, text, integer[]);

CREATE OR REPLACE FUNCTION public.get_abc_sales_frequency_analysis_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date,
    IN abc_analysis_type text,
    IN except_line integer[])
RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, sales_qty numeric, total_orders bigint, total_orders_per numeric, cum_total_orders_per numeric, analysis_category text) AS
$BODY$
    BEGIN
        Return Query

        with all_data as (
    Select * from get_sales_frequency_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, except_line)
        ),
        warehouse_wise_abc_analysis as(
            Select a.warehouse_id, a.warehouse_name, sum(a.total_orders) as total_orders
            from all_data a
            group by a.warehouse_id, a.warehouse_name
        )

        Select final_data.* from
        (
            Select
                result.*,
                case
                    when result.total_orders_per > 20 then 'A'
                    when result.total_orders_per >= 5 and result.total_orders_per <= 20 then 'B'
                    when result.total_orders_per < 5 then 'C'
                end as analysis_category
            from
            (
                Select
                    *,
                    sum(cum_data.total_orders_per)
        over (partition by cum_data.warehouse_id order by cum_data.warehouse_id, cum_data.total_orders_per desc rows between unbounded preceding and current row) as cum_total_orders_per
                from
                (
                    Select
                        all_data.*,
                        case when wwabc.total_orders <= 0.00 then 0 else
                            Round((all_data.total_orders / wwabc.total_orders * 100.0)::numeric,2)
                        end as total_orders_per
                    from all_data
                        Inner Join warehouse_wise_abc_analysis wwabc on all_data.warehouse_id = wwabc.warehouse_id
                    order by total_orders_per desc
                )cum_data
            )result
        )final_data
        where
        1 = case when abc_analysis_type = 'all' then 1
        else
            case when abc_analysis_type = 'highest_order' then
                case when final_data.analysis_category = 'A' then 1 else 0 end
            else
                case when abc_analysis_type = 'medium_order' then
                    case when final_data.analysis_category = 'B' then 1 else 0 end
                else
                    case when abc_analysis_type = 'lowest_order' then
                        case when final_data.analysis_category = 'C' then 1 else 0 end
                    else 0 end

                end
            end
        end;

    END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;