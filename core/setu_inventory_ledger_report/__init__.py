from . import controller, models, wizard
from odoo import api, SUPERUSER_ID

def pre_init(cr):
    get_products_movements_for_inventory_ledger(cr)
    get_products_opening_stock(cr)
    get_stock_data(cr)
    get_products_movements_for_inventory_ledger_cmpwise(cr)

def get_products_movements_for_inventory_ledger(cr):
    query = """
        DROP FUNCTION if EXISTS public.get_products_movements_for_inventory_ledger(integer[], integer[], integer[], integer[], date, date);
        CREATE OR REPLACE FUNCTION public.get_products_movements_for_inventory_ledger(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN start_date date,
            IN end_date date)
          RETURNS TABLE(row_id bigint, company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, inventory_date date, opening_stock numeric, sales numeric, purchase numeric, sales_return numeric, purchase_return numeric, adjustment_in numeric, adjustment_out numeric, production_in numeric, production_out numeric, transit_in numeric, transit_out numeric, internal_in numeric, internal_out numeric, closing numeric) AS
        $BODY$
                DECLARE
                    tr_start_date date;
                    tr_end_date date;
            
            BEGIN	
                Drop Table if exists inventory_ledger_transaction_table;
                CREATE TEMPORARY TABLE inventory_ledger_transaction_table(
                row_id bigint,
                    company_id integer,
                    company_name character varying,
                    product_id integer,
                    product_name character varying,
                    product_category_id integer,
                    category_name character varying, 
                    warehouse_id integer,
                    warehouse_name character varying, 
                    inventory_date timestamp,
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
        
            tr_start_date := '1900-01-01';
            tr_end_date := start_date - interval '1 day';
        
            Insert into inventory_ledger_transaction_table(row_id, company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, inventory_date, 
            opening_stock, sales, purchase, sales_return, purchase_return, adjustment_in, adjustment_out, production_in, production_out, transit_in, transit_out, internal_in, internal_out, closing)
            
            Select 
                row_number() over(partition by T1.product_id, T1.company_id, T1.warehouse_id order by T1.inventory_date::date, T1.product_id, T1.company_id, T1.warehouse_id) as row_id,
                T1.company_id, T1.company_name, T1.product_id, T1.product_name, T1.product_category_id, T1.category_name, T1.warehouse_id, T1.warehouse_name,
                T1.inventory_date::date, sum(T1.opening_stock) as opening_stock, sum(T1.sales) as sales,  sum(T1.purchase) as purchase,  sum(T1.sales_return) as sales_return, sum(T1.purchase_return) as purchase_return,
                sum(T1.adjustment_in) as adjustment_in, sum(T1.adjustment_out) as adjustment_out, sum(T1.production_in) as production_in, sum(T1.production_out) as production_out,
                sum(T1.transit_in) as transit_in, sum(T1.transit_out) as transit_out, sum(T1.internal_in) as internal_in, sum(T1.internal_out) as internal_out,
                sum(T1.opening_stock) + sum(T1.purchase) - sum(T1.sales) + sum(T1.sales_return) - sum(T1.purchase_return) + sum(T1.adjustment_in) - sum(T1.adjustment_out) + sum(T1.production_in) - sum(T1.production_out) +
                sum(T1.transit_in) - sum(T1.transit_out) + sum(T1.internal_in) - sum(T1.internal_out) as closing
            From  (
                Select * from (
                    Select  
                        move.company_id,
                        cmp.name as company_name,
                        move.product_id as product_id,
                        prod.default_code as product_name,
                        tmpl.categ_id as product_category_id,
                        cat.complete_name as category_name,
                        case 
                            when source.usage = 'internal' and dest.usage = 'customer' then whs.id
                            when source.usage = 'customer' and dest.usage = 'internal' then whd.id
                            when source.usage = 'supplier' and dest.usage = 'internal' then whd.id
                            when source.usage = 'internal' and dest.usage = 'supplier' then whs.id
                            when source.usage = 'internal' and dest.usage = 'inventory' then whs.id
                            when source.usage = 'inventory' and dest.usage = 'internal' then whd.id
                            when source.usage = 'internal' and dest.usage = 'production' then whs.id
                            when source.usage = 'production' and dest.usage = 'intenal' then whd.id
                            when source.usage = 'internal' and dest.usage = 'transit' then whs.id
                            when source.usage = 'transit' and dest.usage = 'internal' then whd.id
                        end as warehouse_id, 
                        case 
                            when source.usage = 'internal' and dest.usage = 'customer' then whs.name
                            when source.usage = 'customer' and dest.usage = 'internal' then whd.name
                            when source.usage = 'supplier' and dest.usage = 'internal' then whd.name
                            when source.usage = 'internal' and dest.usage = 'supplier' then whs.name
                            when source.usage = 'internal' and dest.usage = 'inventory' then whs.name
                            when source.usage = 'inventory' and dest.usage = 'internal' then whd.name
                            when source.usage = 'internal' and dest.usage = 'production' then whs.name
                            when source.usage = 'production' and dest.usage = 'intenal' then whd.name
                            when source.usage = 'internal' and dest.usage = 'transit' then whs.name
                            when source.usage = 'transit' and dest.usage = 'internal' then whd.name
                        end as warehouse_name,
                        move.date as inventory_date, 
                        0 as opening_stock,
                        case when source.usage = 'internal' and dest.usage = 'customer' then move.product_uom_qty else 0 end as sales, 
                        case when source.usage = 'customer' and dest.usage = 'internal' then move.product_uom_qty else 0 end as sales_return,
                        case when source.usage = 'supplier' and dest.usage = 'internal' then move.product_uom_qty else 0 end as purchase,
                        case when source.usage = 'internal' and dest.usage = 'supplier' then move.product_uom_qty else 0 end as purchase_return,
                        case when source.usage = 'internal' and dest.usage = 'inventory' then move.product_uom_qty else 0 end as adjustment_out,
                        case when source.usage = 'inventory' and dest.usage = 'internal' then move.product_uom_qty else 0 end as adjustment_in,
                        case when source.usage = 'internal' and dest.usage = 'production' then move.product_uom_qty else 0 end as production_out,
                        case when source.usage = 'production' and dest.usage = 'intenal' then move.product_uom_qty else 0 end as production_in,
                        case when source.usage = 'internal' and dest.usage = 'transit' then move.product_uom_qty else 0 end as transit_out,
                        case when source.usage = 'transit' and dest.usage = 'internal' then move.product_uom_qty else 0 end as transit_in,
                        0 as internal_out,
                        0 as internal_in
                        
                    from stock_move move
                        Inner Join stock_location source on source.id = move.location_id
                        Inner Join stock_location dest on dest.id = move.location_dest_id
                        LEFT JOIN stock_warehouse whs ON source.parent_path::text ~~ concat('%/', whs.view_location_id, '/%')
                        LEFT JOIN stock_warehouse whd ON dest.parent_path::text ~~ concat('%/', whd.view_location_id, '/%')
                        Inner Join res_company cmp on cmp.id = move.company_id
                        Inner Join product_product prod on prod.id = move.product_id 
                        Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id 
                        Inner Join product_category cat on cat.id = tmpl.categ_id
        
                    Where prod.active = true and tmpl.active = true and 
                    move.state ='done' and move.date between start_date and end_date
                    and not (source.usage = 'internal' and dest.usage='internal') 
                    --company dynamic condition
                    and 1 = case when array_length(company_ids,1) >= 1 then 
                        case when move.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                    --product dynamic condition
                    and 1 = case when array_length(product_ids,1) >= 1 then 
                        case when move.product_id = ANY(product_ids) then 1 else 0 end
                        else 1 end
                    --category dynamic condition
                    and 1 = case when array_length(category_ids,1) >= 1 then 
                        case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                        else 1 end
                )move
                --warehouse dynamic condition
                where 1 = case when array_length(warehouse_ids,1) >= 1 then 
                        case when move.warehouse_id = ANY(warehouse_ids) then 1 
                        else 0 end 
                    else 1 end
        
            Union All 
            
            select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, T.warehouse_id, T.warehouse_name, start_date as inventory_date, T.opening_stock,
            0,0,0,0,0,0,0,0,0,0,0,0
            from get_products_opening_stock(company_ids, product_ids, category_ids, warehouse_ids, tr_start_date, tr_end_date) T
        
            Union all 
            
            Select  
                move.company_id,
                cmp.name as company_name,
                move.product_id as product_id,
                prod.default_code as product_name,
                tmpl.categ_id as category_id,
                cat.complete_name as category_name,
                whs.id as warehouse_id,
                whs.name as warehouse_name,
                move.date, 	 
                0 as opening,		
                0 as sale, 
                0 as sale_return,
                0 as purchase,
                0 as purchase_return,
                0 as adjustment_out,
                0 as adjustment_in,
                0 as production_out,
                0 as production_in,
                0 as transit_out,
                0 as transit_in,
                move.product_uom_qty as internal_out,
                0 as internal_in
            from stock_move move
                Inner Join stock_location source on source.id = move.location_id
                Inner Join stock_location dest on dest.id = move.location_dest_id
                LEFT JOIN stock_warehouse whs ON source.parent_path::text ~~ concat('%/', whs.view_location_id, '/%')
                LEFT JOIN stock_warehouse whd ON dest.parent_path::text ~~ concat('%/', whd.view_location_id, '/%')
                Inner Join res_company cmp on cmp.id = move.company_id
                Inner Join product_product prod on prod.id = move.product_id 
                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id 
                Inner Join product_category cat on cat.id = tmpl.categ_id
            Where prod.active = true and tmpl.active = true and move.state ='done' and move.date between start_date and end_date and source.usage = 'internal' and dest.usage='internal'
            --company dynamic condition
            and 1 = case when array_length(company_ids,1) >= 1 then 
                case when move.company_id = ANY(company_ids) then 1 else 0 end
                else 1 end
            --product dynamic condition
            and 1 = case when array_length(product_ids,1) >= 1 then 
                case when move.product_id = ANY(product_ids) then 1 else 0 end
                else 1 end
            --category dynamic condition
            and 1 = case when array_length(category_ids,1) >= 1 then 
                case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                else 1 end
            --warehouse dynamic condition
            and 1 = case when array_length(warehouse_ids,1) >= 1 then 
                    case when whs.id = ANY(warehouse_ids) then 1 
                    else 0 end 
                else 1 end
        
            Union All
        
            Select  
                move.company_id,
                cmp.name as company_name,
                move.product_id as product_id,
                prod.default_code as product_name,
                tmpl.categ_id as category_id,
                cat.complete_name as category_name,
                whd.id as warehouse_id,
                whd.name as warehouse_name,
                move.date,
                0 as opening,
                0 as sale, 
                0 as sale_return,
                0 as purchase,
                0 as purchase_return,
                0 as adjustment_out,
                0 as adjustment_in,
                0 as production_out,
                0 as production_in,
                0 as transit_out,
                0 as transit_in,
                0 as internal_out,
                move.product_uom_qty as internal_in
                
            from stock_move move
                Inner Join stock_location source on source.id = move.location_id
                Inner Join stock_location dest on dest.id = move.location_dest_id
                LEFT JOIN stock_warehouse whs ON source.parent_path::text ~~ concat('%/', whs.view_location_id, '/%')
                LEFT JOIN stock_warehouse whd ON dest.parent_path::text ~~ concat('%/', whd.view_location_id, '/%')
                Inner Join res_company cmp on cmp.id = move.company_id
                Inner Join product_product prod on prod.id = move.product_id 
                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id 
                Inner Join product_category cat on cat.id = tmpl.categ_id
            Where prod.active = true and tmpl.active = true and move.state ='done' and move.date between start_date and end_date and source.usage = 'internal' and dest.usage='internal'
            --company dynamic condition
            and 1 = case when array_length(company_ids,1) >= 1 then 
                case when move.company_id = ANY(company_ids) then 1 else 0 end
                else 1 end
            --product dynamic condition
            and 1 = case when array_length(product_ids,1) >= 1 then 
                case when move.product_id = ANY(product_ids) then 1 else 0 end
                else 1 end
            --category dynamic condition
            and 1 = case when array_length(category_ids,1) >= 1 then 
                case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                else 1 end
            --warehouse dynamic condition
            and 1 = case when array_length(warehouse_ids,1) >= 1 then 
                    case when whd.id = ANY(warehouse_ids) then 1  
                    else 0 end 
                else 1 end
            )T1
            Group by T1.company_id, T1.company_name, T1.product_id, T1.product_name, T1.product_category_id, T1.category_name, T1.warehouse_id, T1.warehouse_name, T1.inventory_date::date;
            
        
            
            Return query
            WITH RECURSIVE summary_cte(row_id, company_id, company_name, product_id, product_name, product_category_id, category_name, warehouse_id, warehouse_name, inventory_date,
            opening_stock, sales, purchase, sales_return, purchase_return, adjustment_in, adjustment_out, production_in, production_out, transit_in, transit_out, internal_in, internal_out, closing) 
            AS (
                Select 
                    S1.row_id,
                    S1.company_id, S1.company_name, S1.product_id, S1.product_name, S1.product_category_id, S1.category_name, S1.warehouse_id, S1.warehouse_name,
                    S1.inventory_date::date, S1.opening_stock, S1.sales, S1.purchase, S1.sales_return, S1.purchase_return, S1.adjustment_in, S1.adjustment_out, S1.production_in, S1.production_out,
                    S1.transit_in, S1.transit_out, S1.internal_in, S1.internal_out, 
                    (S1.opening_stock + S1.purchase - S1.sales + S1.sales_return - S1.purchase_return + S1.adjustment_in - S1.adjustment_out + S1.production_in - S1.production_out +
                    S1.transit_in - S1.transit_out + S1.internal_in - S1.internal_out) as closing
                from inventory_ledger_transaction_table S1
                Where S1.row_id = 1
        
                    UNION ALL
                
                SELECT summ.row_id,
                    summ.company_id, summ.company_name, summ.product_id, summ.product_name, summ.product_category_id, summ.category_name, summ.warehouse_id, summ.warehouse_name,
                    summ.inventory_date::date, (summ_cte.opening_stock + summ_cte.purchase - summ_cte.sales + summ_cte.sales_return - summ_cte.purchase_return + summ_cte.adjustment_in - summ_cte.adjustment_out + summ_cte.production_in - summ_cte.production_out +
                    summ_cte.transit_in - summ_cte.transit_out + summ_cte.internal_in - summ_cte.internal_out), summ.sales, summ.purchase, summ.sales_return, summ.purchase_return, summ.adjustment_in, summ.adjustment_out, summ.production_in, summ.production_out,
                    summ.transit_in, summ.transit_out, summ.internal_in, summ.internal_out, 
                    ((summ_cte.opening_stock + summ_cte.purchase - summ_cte.sales + summ_cte.sales_return - summ_cte.purchase_return + summ_cte.adjustment_in - summ_cte.adjustment_out + summ_cte.production_in - summ_cte.production_out +
                    summ_cte.transit_in - summ_cte.transit_out + summ_cte.internal_in - summ.internal_out) + summ.purchase - summ.sales + summ.sales_return - summ.purchase_return + summ.adjustment_in - summ.adjustment_out + summ.production_in - summ.production_out +
                    summ.transit_in - summ.transit_out + summ.internal_in - summ.internal_out) as closing
                FROM inventory_ledger_transaction_table summ, summary_cte summ_cte
                WHERE summ.row_id - 1 = summ_cte.row_id and summ.product_id = summ_cte.product_id and summ.warehouse_id = summ_cte.warehouse_id 
            )
        
            SELECT * FROM summary_cte order by 2,4,8,10;
        
        END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def get_products_opening_stock(cr):
    query = """
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
    """
    cr.execute(query)

def get_stock_data(cr):
    query = """
        DROP FUNCTION if EXISTS public.get_stock_data(integer[], integer[], integer[], integer[], text, date, date);
        CREATE OR REPLACE FUNCTION public.get_stock_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN transaction_type text,
            IN start_date date,
            IN end_date date)
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, product_qty numeric) AS
        $BODY$
                DECLARE 
                    source_usage text;
                    dest_usage text;
                BEGIN
                    source_usage := case 
                                when transaction_type in ('sales','transit_out','production_out','internal_out', 'adjustment_out', 'internal_in','purchase_return') 
                                    then 'internal' 
                                when transaction_type = 'purchase' then 'supplier'
                                when transaction_type = 'transit_in' then 'transit'
                                when transaction_type = 'adjustment_in' then 'inventory'
                                when transaction_type = 'production_in' then 'production'
                                when transaction_type = 'sales_return' then 'customer'
                            end;
                    dest_usage := case 
                                when transaction_type in ('purchase','transit_in','adjustment_in','production_in', 'internal_in', 'internal_out', 'sales_return') 
                                    then 'internal' 
                                when transaction_type = 'sales' then 'customer'
                                when transaction_type = 'transit_out' then 'transit'
                                when transaction_type = 'adjustment_out' then 'inventory'
                                when transaction_type = 'production_out' then 'production'
                                when transaction_type = 'purchase_return' then 'supplier'
                            end;
                        
                    RETURN QUERY 
                    Select 
                        T.company_id,
                        T.company_name,
                        T.product_id,
                        T.product_name,
                        T.category_id,
                        T.category_name,
                        T.warehouse_id,
                        T.warehouse_name,
                        coalesce(sum(T.product_qty),0) as product_qty
                    From
                    (
                        Select 
                            move.company_id,
                            cmp.name as company_name,
                            move.product_id as product_id,
                            prod.default_code as product_name,
                            tmpl.categ_id as category_id,
                            cat.complete_name as category_name,
                            case when transaction_type in ('sales','transit_out','production_out','internal_out', 'adjustment_out', 'purchase_return') then 
                                source_warehouse.id else  dest_warehouse.id end as warehouse_id,
                            case when transaction_type in ('sales','transit_out','production_out','internal_out', 'adjustment_out', 'purchase_return') then 
                                source_warehouse.name else  dest_warehouse.name end as warehouse_name,
                            move.product_uom_qty as product_qty
                        From 
                            stock_move move
                                Inner Join stock_location source on source.id = move.location_id
                                Inner Join stock_location dest on dest.id = move.location_dest_id
                                Inner Join res_company cmp on cmp.id = move.company_id
                                Inner Join product_product prod on prod.id = move.product_id 
                                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id 
                                Inner Join product_category cat on cat.id = tmpl.categ_id
                                Left Join stock_warehouse source_warehouse ON source.parent_path::text ~~ concat('%/', source_warehouse.view_location_id, '/%')
                                Left Join stock_warehouse dest_warehouse ON dest.parent_path::text ~~ concat('%/', dest_warehouse.view_location_id, '/%')
                        where prod.active = true and tmpl.active = true
                        and source.usage = source_usage and dest.usage = dest_usage 
                        and move.date::date >= start_date and move.date::date <= end_date 
                        and move.state = 'done'
                        and tmpl.type = 'product'
                        
                        --company dynamic condition
                        and 1 = case when array_length(company_ids,1) >= 1 then 
                            case when move.company_id = ANY(company_ids) then 1 else 0 end
                            else 1 end
                        --product dynamic condition
                        and 1 = case when array_length(product_ids,1) >= 1 then 
                            case when move.product_id = ANY(product_ids) then 1 else 0 end
                            else 1 end
                        --category dynamic condition
                        and 1 = case when array_length(category_ids,1) >= 1 then 
                            case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                            else 1 end
                        --warehouse dynamic condition
                        and 1 = case when array_length(warehouse_ids,1) >= 1 then 
                                case when transaction_type in ('sales','transit_out','production_out','internal_out', 'adjustment_out','purchase_return'	) then 
                                    case when source_warehouse.id = ANY(warehouse_ids) then 1 else 0 end 
                                else  
                                    case when dest_warehouse.id = ANY(warehouse_ids) then 1 else 0 end
                                end
                            else 1 end
                    )T
                    group by T.company_id, T.product_id, T.category_id, T.warehouse_id, T.company_name, T.product_name, T.category_name, T.warehouse_name
                    ;
                END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def get_products_movements_for_inventory_ledger_cmpwise(cr):
    query = """
        DROP FUNCTION if EXISTS public.get_products_movements_for_inventory_ledger_cmpwise(integer[], integer[], integer[], date, date);
        CREATE OR REPLACE FUNCTION public.get_products_movements_for_inventory_ledger_cmpwise(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN start_date date,
            IN end_date date)
          RETURNS TABLE(row_id bigint, company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, inventory_date date, opening_stock numeric, sales numeric, purchase numeric, sales_return numeric, purchase_return numeric, adjustment_in numeric, adjustment_out numeric, production_in numeric, production_out numeric, closing numeric) AS
        $BODY$
                DECLARE
                    tr_start_date date;
                    tr_end_date date;
            
            BEGIN	
                Drop Table if exists inventory_ledger_transaction_table;
                CREATE TEMPORARY TABLE inventory_ledger_transaction_table(
                row_id bigint,
                    company_id integer,
                    company_name character varying,
                    product_id integer,
                    product_name character varying,
                    product_category_id integer,
                    category_name character varying, 
                    inventory_date timestamp,
                    opening_stock Numeric DEFAULT 0,
                    sales Numeric DEFAULT 0,
                    sales_return numeric DEFAULT 0,
                    purchase Numeric DEFAULT 0,
                    purchase_return numeric DEFAULT 0,
                    adjustment_in Numeric DEFAULT 0,
                    adjustment_out Numeric DEFAULT 0,
                    production_in Numeric DEFAULT 0,
                    production_out Numeric DEFAULT 0,
                    closing Numeric DEFAULT 0
                );
        
            tr_start_date := '1900-01-01';
            tr_end_date := start_date - interval '1 day';
        
            Insert into inventory_ledger_transaction_table(row_id, company_id, company_name, product_id, product_name, product_category_id, category_name, inventory_date, 
            opening_stock, sales, purchase, sales_return, purchase_return, adjustment_in, adjustment_out, production_in, production_out, closing)
            
            Select 
                row_number() over(partition by T1.product_id, T1.company_id order by T1.inventory_date::date, T1.product_id, T1.company_id) as row_id,
                T1.company_id, T1.company_name, T1.product_id, T1.product_name, T1.product_category_id, T1.category_name,
                T1.inventory_date::date, sum(T1.opening_stock) as opening_stock, sum(T1.sales) as sales,  sum(T1.purchase) as purchase,  sum(T1.sales_return) as sales_return, sum(T1.purchase_return) as purchase_return,
                sum(T1.adjustment_in) as adjustment_in, sum(T1.adjustment_out) as adjustment_out, sum(T1.production_in) as production_in, sum(T1.production_out) as production_out,
                sum(T1.opening_stock) + sum(T1.purchase) - sum(T1.sales) + sum(T1.sales_return) - sum(T1.purchase_return) + sum(T1.adjustment_in) - sum(T1.adjustment_out) + sum(T1.production_in) - sum(T1.production_out)
                as closing
            From  (
            
            Select  
                move.company_id,
                cmp.name as company_name,
                move.product_id as product_id,
                prod.default_code as product_name,
                tmpl.categ_id as product_category_id,
                cat.complete_name as category_name,
                move.date as inventory_date, 
                0 as opening_stock,
                case when source.usage = 'internal' and dest.usage = 'customer' then move.product_uom_qty else 0 end as sales, 
                case when source.usage = 'customer' and dest.usage = 'internal' then move.product_uom_qty else 0 end as sales_return,
                case when source.usage = 'supplier' and dest.usage = 'internal' then move.product_uom_qty else 0 end as purchase,
                case when source.usage = 'internal' and dest.usage = 'supplier' then move.product_uom_qty else 0 end as purchase_return,
                case when source.usage = 'internal' and dest.usage = 'inventory' then move.product_uom_qty else 0 end as adjustment_out,
                case when source.usage = 'inventory' and dest.usage = 'internal' then move.product_uom_qty else 0 end as adjustment_in,
                case when source.usage = 'internal' and dest.usage = 'production' then move.product_uom_qty else 0 end as production_out,
                case when source.usage = 'production' and dest.usage = 'intenal' then move.product_uom_qty else 0 end as production_in
            from stock_move move
                Inner Join stock_location source on source.id = move.location_id
                Inner Join stock_location dest on dest.id = move.location_dest_id
                Inner Join res_company cmp on cmp.id = move.company_id
                Inner Join product_product prod on prod.id = move.product_id 
                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id 
                Inner Join product_category cat on cat.id = tmpl.categ_id
        
            Where prod.active = true and tmpl.active = true and 
            move.state ='done' and move.date between start_date and end_date
            and not (source.usage = 'internal' and dest.usage='internal') and not (source.usage = 'transit' or dest.usage='transit') 
            --company dynamic condition
            and 1 = case when array_length(company_ids,1) >= 1 then 
                case when move.company_id = ANY(company_ids) then 1 else 0 end
                else 1 end
            --product dynamic condition
            and 1 = case when array_length(product_ids,1) >= 1 then 
                case when move.product_id = ANY(product_ids) then 1 else 0 end
                else 1 end
            --category dynamic condition
            and 1 = case when array_length(category_ids,1) >= 1 then 
                case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                else 1 end
        
            Union All 
            
            select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, start_date as inventory_date, sum(T.opening_stock) as opening_stock,
            0,0,0,0,0,0,0,0
            from get_products_opening_stock(company_ids, product_ids, category_ids, '{}', tr_start_date, tr_end_date) T
            Group by T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name
            )T1
            Group by T1.company_id, T1.company_name, T1.product_id, T1.product_name, T1.product_category_id, T1.category_name, T1.inventory_date::date;
            
        
            
            Return query
            WITH RECURSIVE summary_cte(row_id, company_id, company_name, product_id, product_name, product_category_id, category_name, inventory_date,
            opening_stock, sales, purchase, sales_return, purchase_return, adjustment_in, adjustment_out, production_in, production_out, closing) 
            AS (
                Select 
                    S1.row_id,
                    S1.company_id, S1.company_name, S1.product_id, S1.product_name, S1.product_category_id, S1.category_name, 
                    S1.inventory_date::date, S1.opening_stock, S1.sales, S1.purchase, S1.sales_return, S1.purchase_return, S1.adjustment_in, S1.adjustment_out, S1.production_in, S1.production_out,
                    (S1.opening_stock + S1.purchase - S1.sales + S1.sales_return - S1.purchase_return + S1.adjustment_in - 
                    S1.adjustment_out + S1.production_in - S1.production_out) as closing
                from inventory_ledger_transaction_table S1
                Where S1.row_id = 1
        
                    UNION ALL
                
                SELECT summ.row_id,
                    summ.company_id, summ.company_name, summ.product_id, summ.product_name, summ.product_category_id, summ.category_name,
                    summ.inventory_date::date, (summ_cte.opening_stock + summ_cte.purchase - summ_cte.sales + summ_cte.sales_return - summ_cte.purchase_return + summ_cte.adjustment_in - summ_cte.adjustment_out + summ_cte.production_in - summ_cte.production_out
                    ), summ.sales, summ.purchase, summ.sales_return, summ.purchase_return, summ.adjustment_in, summ.adjustment_out, summ.production_in, summ.production_out,
                    ((summ_cte.opening_stock + summ_cte.purchase - summ_cte.sales + summ_cte.sales_return - summ_cte.purchase_return + summ_cte.adjustment_in - summ_cte.adjustment_out + summ_cte.production_in - summ_cte.production_out) 
                    + summ.purchase - summ.sales + summ.sales_return - summ.purchase_return + summ.adjustment_in - summ.adjustment_out + summ.production_in - summ.production_out) as closing
                FROM inventory_ledger_transaction_table summ, summary_cte summ_cte
                WHERE summ.row_id - 1 = summ_cte.row_id and summ.product_id = summ_cte.product_id and summ.company_id = summ_cte.company_id
            )
        
            SELECT * FROM summary_cte order by 2,4,8;
        
        END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)