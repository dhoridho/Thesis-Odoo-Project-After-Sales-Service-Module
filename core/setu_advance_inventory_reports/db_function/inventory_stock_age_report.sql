-- DROP FUNCTION public.inventory_stock_age_report(integer[], integer[], integer[]);
CREATE OR REPLACE FUNCTION public.inventory_stock_age_report(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[])
  RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, current_stock numeric, current_stock_value numeric, oldest_date date, days_old integer, oldest_stock_qty numeric, oldest_stock_value numeric, stock_qty_ratio numeric, stock_value_ratio numeric) AS
$BODY$
        BEGIN
        Drop Table if exists stock_age_table;
        CREATE TEMPORARY TABLE stock_age_table(
            row_id INT,
            company_id INT,
            company_name character varying,
            in_date date,
            product_id INT,
            product_name character varying,
            product_category_id INT,
            category_name character varying,
            current_stock numeric DEFAULT 0,
            current_stock_value numeric DEFAULT 0
        );
        Insert into stock_age_table
        Select
            row_number() over(partition by layer.company_id, layer.product_id order by layer.company_id, layer.product_id, move.date) row_id,
            layer.company_id,
            cmp.name as company_name,
            move.date,
            layer.product_id,
            coalesce(prod.default_code, tmpl.name) as product_code,
            --prod.default_code as product_code,
-- 			tmpl.name,
            tmpl.categ_id as category_id,
            cat.complete_name as category_name,
            sum(layer.remaining_qty) stock_qty,
            sum(layer.remaining_value) stock_value
        from
            stock_valuation_layer layer
                Inner Join stock_move move on move.id = layer.stock_move_id
                Inner Join product_product prod on prod.id = layer.product_id
                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                Inner Join product_category cat on cat.id = tmpl.categ_id
                Inner Join res_company cmp on cmp.id = layer.company_id
        Where remaining_qty > 0 and prod.active = True and tmpl.active = True and
        1 = case when array_length(product_ids,1) >= 1 then
            case when layer.product_id = ANY(product_ids) then 1 else 0 end
            else 1 end
        and 1 = case when array_length(category_ids,1) >= 1 then
            case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
            else 1 end
        and 1 = case when array_length(company_ids,1) >= 1 then
            case when layer.company_id = ANY(company_ids) then 1 else 0 end
            else 1 end
        group by layer.company_id, cmp.name, move.date, layer.product_id, prod.default_code, tmpl.name, tmpl.categ_id, cat.complete_name;

        Return Query
        with all_data as (
            Select st.company_id, st.company_name, st.product_id, st.product_name, st.product_category_id, st.category_name,
                sum(st.current_stock) as total_stock, sum(st.current_stock_value) as total_stock_value
            from stock_age_table st
            group by st.company_id, st.company_name, st.product_id, st.product_name, st.product_category_id, st.category_name
        ),
        company_wise_stock_age_table as(
            Select sat.company_id, sum(sat.current_stock) as total_stock_qty, sum(sat.current_stock_value) as total_stock_value
            from stock_age_table sat
            group by sat.company_id
        ),
        oldest_stock_data as (
            Select st.company_id, st.product_id, st.in_date, st.current_stock, st.current_stock_value,
                (now()::date - st.in_date) days_old
            from stock_age_table st
            where row_id = 1
        )

        Select
            all_data.*, oldest.in_date, oldest.days_old, oldest.current_stock, oldest.current_stock_value,
            case when cmp_age.total_stock_qty <= 0.00 then 0 else
                Round(all_data.total_stock / cmp_age.total_stock_qty * 100,3)
            end as stock_qty_ratio,
            case when cmp_age.total_stock_value <= 0.00 then 0 else
                Round(all_data.total_stock_value / cmp_age.total_stock_value * 100,4)
            end as stock_value_ratio
        From
            all_data
                Inner Join oldest_stock_data oldest on oldest.company_id = all_data.company_id and all_data.product_id = oldest.product_id
                Inner Join company_wise_stock_age_table cmp_age on cmp_age.company_id = all_data.company_id;
    END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;