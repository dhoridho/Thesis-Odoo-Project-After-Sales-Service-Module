-- DROP FUNCTION public.get_inventory_xyz_analysis_data(integer[], integer[], integer[], text);
CREATE OR REPLACE FUNCTION public.get_inventory_xyz_analysis_data(
IN company_ids integer[],
IN product_ids integer[],
IN category_ids integer[],
IN inventory_analysis_type text)
RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, current_stock numeric, stock_value numeric, stock_value_per numeric, cum_stock_value_per numeric, analysis_category text) AS
$BODY$
            BEGIN
                Return Query

                with all_data as (
                    Select
                        layer.company_id,
                        cmp.name as company_name,
                        layer.product_id,
                        coalesce(prod.default_code, tmpl.name) as product_name,
                        tmpl.categ_id as product_category_id,
                        cat.name as category_name,
                        sum(quantity) as current_stock,
                        sum(value) as stock_value
                    from
                        stock_valuation_layer layer
                            Inner Join res_company cmp on cmp.id = layer.company_id
                            Inner Join product_product prod on prod.id = layer.product_id
                            Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                            Inner Join product_category cat on cat.id = tmpl.categ_id
                    Where prod.active = True and tmpl.active = True and tmpl.type = 'product'
                        --company dynamic condition
                        and 1 = case when array_length(company_ids,1) >= 1 then
                            case when layer.company_id = ANY(company_ids) then 1 else 0 end
                            else 1 end
                        --product dynamic condition
                        and 1 = case when array_length(product_ids,1) >= 1 then
                            case when layer.product_id = ANY(product_ids) then 1 else 0 end
                            else 1 end
                        --category dynamic condition
                        and 1 = case when array_length(category_ids,1) >= 1 then
                            case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                            else 1 end
                   group by layer.company_id, cmp.name, layer.product_id, coalesce(prod.default_code, tmpl.name), tmpl.categ_id, cat.name
                ),
                warehouse_wise_xyz_analysis as(
                    Select a.company_id, a.company_name, sum(a.current_stock) as total_current_stock, sum(a.stock_value) as total_stock_value
                    from all_data a
                    group by a.company_id, a.company_name
                )
                Select final_data.* from
                (
                    Select
                        result.*,
                        case
                            when result.cum_stock_value_per < 70 then 'X'
                            when result.cum_stock_value_per >= 70 and result.cum_stock_value_per <= 90 then 'Y'
                            when result.cum_stock_value_per > 90 then 'Z'
                        end as analysis_category
                    from
                    (
                        Select
                            *,
                            sum(cum_data.warehouse_stock_value_per)
                over (partition by cum_data.company_id order by cum_data.company_id, cum_data.warehouse_stock_value_per desc rows between unbounded preceding and current row) as cum_stock_value_per
                        from
                        (
                            Select
                                all_data.*,
                                case when wwxyz.total_stock_value <= 0.00 then 0 else
                                    Round((all_data.stock_value / wwxyz.total_stock_value * 100.0)::numeric,2)
                                end as warehouse_stock_value_per
                            from all_data
                                Inner Join warehouse_wise_xyz_analysis wwxyz on all_data.company_id = wwxyz.company_id
                            order by warehouse_stock_value_per desc
                        )cum_data
                    )result
                )final_data
                where
                1 = case when inventory_analysis_type = 'all' then 1
                else
                    case when inventory_analysis_type = 'high_stock' then
                        case when final_data.analysis_category = 'X' then 1 else 0 end
                    else
                        case when inventory_analysis_type = 'medium_stock' then
                            case when final_data.analysis_category = 'Y' then 1 else 0 end
                        else
                            case when inventory_analysis_type = 'low_stock' then
                                case when final_data.analysis_category = 'Z' then 1 else 0 end
                            else 0 end

                        end
                    end
                end;

            END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;