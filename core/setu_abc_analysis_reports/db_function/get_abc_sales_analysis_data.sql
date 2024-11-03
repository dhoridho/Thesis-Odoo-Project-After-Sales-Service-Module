DROP FUNCTION IF EXISTS public.get_abc_sales_analysis_data(integer[], integer[], integer[], integer[], date, date, text);

CREATE OR REPLACE FUNCTION public.get_abc_sales_analysis_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date,
    IN abc_analysis_type text,
    IN except_line integer[])
  RETURNS TABLE
  (
    company_id integer, company_name character varying, product_id integer, product_name character varying,
    product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying,
    sales_qty numeric, sales_amount numeric,total_orders numeric, sales_amount_per numeric, cum_sales_amount_per numeric, analysis_category text
) AS
$BODY$
        BEGIN
            Return Query

            with all_data as (
                Select * from get_sales_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, except_line)
            ),
            warehouse_wise_abc_analysis as(
                Select
                    a.warehouse_id,
                    a.warehouse_name,
                    sum(a.sales_qty) as total_sales,
                    sum(a.sales_amount) as total_sales_amount,
                    sum(a.total_orders) as total_orders
                from all_data a
                group by a.warehouse_id, a.warehouse_name
            )

            Select final_data.* from
            (
                Select
                    result.*,
                    case
                        when result.cum_sales_amount_per <= 80 then 'A'
                        when result.cum_sales_amount_per > 80 and result.cum_sales_amount_per <= 95 then 'B'
                        when result.cum_sales_amount_per > 95 then 'C'
                    end as analysis_category
                from
                (
                    Select
                        *,
                        round(sum(cum_data.sales_amount_per)
            over (partition by cum_data.warehouse_id order by cum_data.warehouse_id, cum_data.sales_amount_per desc, cum_data.total_orders desc rows between unbounded preceding and current row),2) as cum_sales_amount_per
                    from
                    (
                        Select
                            all_data.*,
                            case when wwabc.total_sales_amount <= 0.00 then 0 else
                                (all_data.sales_amount / wwabc.total_sales_amount * 100.0)::numeric
                            end as sales_amount_per
                        from all_data
                            Inner Join warehouse_wise_abc_analysis wwabc on all_data.warehouse_id = wwabc.warehouse_id
                        order by sales_amount_per desc, all_data.total_orders desc
                    )cum_data
                )result
            )final_data
            where
            1 = case when abc_analysis_type = 'all' then 1
            else
                case when abc_analysis_type = 'high_sales' then
                    case when final_data.analysis_category = 'A' then 1 else 0 end
                else
                    case when abc_analysis_type = 'medium_sales' then
                        case when final_data.analysis_category = 'B' then 1 else 0 end
                    else
                        case when abc_analysis_type = 'low_sales' then
                            case when final_data.analysis_category = 'C' then 1 else 0 end
                        else 0 end

                    end
                end
            end;

        END; $BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100
  ROWS 1000;
