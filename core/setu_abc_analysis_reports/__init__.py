from . import controller
from . import wizard
from odoo import api, SUPERUSER_ID

def pre_init(cr):
    # env = api.Environment(cr, SUPERUSER_ID, {})
    get_sales_data(cr)
    get_abc_sales_analysis_data(cr)
    get_sales_frequency_data(cr)
    get_abc_sales_analysis_by_company(cr)
    create_get_xyz_analysis_data_sp(cr)
    get_abc_xyz_analysis_report(cr)
    get_abc_sales_frequency_analysis_data(cr)


def get_sales_data(cr):
    query = """
        -- DROP FUNCTION public.get_sales_data(integer[], integer[], integer[], integer[], date, date, integer[]);

        CREATE OR REPLACE FUNCTION public.get_sales_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN start_date date,
            IN end_date date,
            IN except_line integer[])
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, sales_qty numeric, sales_amount numeric) AS
        $BODY$
                BEGIN
                    Return Query
                    Select 	
                        cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name, sum(T.sales_qty) as total_sales, sum(T.sales_amount) as total_sales_amount
                    From
                    (	

                SELECT 
                    foo.cmp_id,
                    foo.cmp_name,
                    foo.p_id,
                    foo.prod_name,
                    foo.categ_id,
                    foo.cat_name,
                    foo.wh_id,
                    foo.ware_name,
                    foo.sales_amount,
                    foo.sales_qty
                FROM 
                ( 
                    SELECT 
                        so.company_id as cmp_id,
                        cmp.name as cmp_name,
                        sol.product_id as p_id,
                        pro.default_code as prod_name,
                        pt.categ_id,
                        cat.complete_name as cat_name,
                        so.warehouse_id as wh_id,
                        ware.name as ware_name,
                        Round(sol.price_subtotal /
                        CASE COALESCE(so.currency_rate, 0::numeric)
                            WHEN 0 THEN 1.0
                            ELSE so.currency_rate
                        END, 2) AS sales_amount,
                        Round(sol.product_uom_qty / u.factor * u2.factor,2) AS sales_qty
                    FROM sale_order_line sol
                        JOIN sale_order so ON sol.order_id = so.id
                        Inner Join product_product pro ON sol.product_id = pro.id
                        Inner Join product_template pt ON pro.product_tmpl_id = pt.id
                        Inner Join uom_uom u ON u.id = sol.product_uom
                        Inner Join uom_uom u2 ON u2.id = pt.uom_id
                        Inner Join res_company cmp on cmp.id = so.company_id
                        Inner Join stock_warehouse ware on ware.id = so.warehouse_id 
                        Inner Join product_category cat on cat.id = pt.categ_id
                    WHERE NOT sol.id = ANY(except_line) and so.state::text = ANY (ARRAY['sale'::character varying::text, 'done'::character varying::text])  
                    and so.date_order::date >= start_date and so.date_order::date <= end_date
                    --company dynamic condition
                    and 1 = case when array_length(company_ids,1) >= 1 then 
                        case when so.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                    --product dynamic condition
                    and 1 = case when array_length(product_ids,1) >= 1 then 
                        case when sol.product_id = ANY(product_ids) then 1 else 0 end
                        else 1 end
                    --category dynamic condition
                    and 1 = case when array_length(category_ids,1) >= 1 then 
                        case when pt.categ_id = ANY(category_ids) then 1 else 0 end
                        else 1 end
                    --warehouse dynamic condition
                    and 1 = case when array_length(warehouse_ids,1) >= 1 then 
                        case when so.warehouse_id = ANY(warehouse_ids) then 1 else 0 end
                        else 1 end
                ) foo
                    )T
                    group by cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name;

                END; 

                $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def get_abc_sales_analysis_data(cr):
    query = """
        -- DROP FUNCTION public.get_abc_sales_analysis_data(integer[], integer[], integer[], integer[], date, date, text, integer[]);
        
        CREATE OR REPLACE FUNCTION public.get_abc_sales_analysis_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN start_date date,
            IN end_date date,
            IN abc_analysis_type text,
            IN except_line integer[]),
          RETURNS TABLE
          (
            company_id integer, company_name character varying, product_id integer, product_name character varying, 
            product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying,
            sales_qty numeric, sales_amount numeric, sales_amount_per numeric, cum_sales_amount_per numeric, analysis_category text
        ) AS
        $BODY$
                BEGIN
                    Return Query
                    
                    with all_data as (
                        Select * from get_sales_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, except_line)
                    ),
                    warehouse_wise_abc_analysis as(
                        Select a.warehouse_id, a.warehouse_name, sum(a.sales_qty) as total_sales, sum(a.sales_amount) as total_sales_amount
                        from all_data a
                        group by a.warehouse_id, a.warehouse_name
                    )
        
                    Select final_data.* from 
                    (
                        Select 
                            result.*,
                            case 
                                when result.cum_sales_amount_per < 80 then 'A' 
                                when result.cum_sales_amount_per >= 80 and result.cum_sales_amount_per <= 95 then 'B'
                                when result.cum_sales_amount_per > 95 then 'C'
                            end as analysis_category 
                        from
                        (
                            Select 
                                *, 
                                sum(cum_data.sales_amount_per) 
                    over (partition by cum_data.warehouse_id order by cum_data.warehouse_id, cum_data.sales_amount_per desc rows between unbounded preceding and current row) as cum_sales_amount_per
                            from 
                            (
                                Select 
                                    all_data.*, 
                                    case when wwabc.total_sales_amount <= 0.00 then 0 else 
                                        Round((all_data.sales_amount / wwabc.total_sales_amount * 100.0)::numeric,2) 
                                    end as sales_amount_per
                                from all_data
                                    Inner Join warehouse_wise_abc_analysis wwabc on all_data.warehouse_id = wwabc.warehouse_id 
                                order by sales_amount_per desc
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
    """
    cr.execute(query)

def get_sales_frequency_data(cr):
    query = """
        -- DROP FUNCTION public.get_sales_frequency_data(integer[], integer[], integer[], integer[], date, date, integer[]);

        CREATE OR REPLACE FUNCTION public.get_sales_frequency_data(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN warehouse_ids integer[],
            IN start_date date,
            IN end_date date,
            IN except_line integer[])
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, sales_qty numeric, total_orders bigint) AS
        $BODY$
                BEGIN
                    Return Query
                    Select 	
                        cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name, sum(T.sales_qty) as total_sales, count(T.order_id) as total_orders
                    From
                    (	
                       
                SELECT  
                    foo.cmp_id,
                    foo.cmp_name,
                    foo.p_id,
                    foo.prod_name,
                    foo.categ_id,
                    foo.cat_name,
                    foo.wh_id,
                    foo.ware_name,			
                    foo.sales_qty,
                    foo.order_id
                FROM 
                ( 
                    SELECT 
                        so.company_id as cmp_id,
                        cmp.name as cmp_name,
                        sol.product_id as p_id,
                        pro.default_code as prod_name,
                        pt.categ_id,
                        cat.complete_name as cat_name,
                        so.warehouse_id as wh_id,
                        ware.name as ware_name,
                        sol.order_id,
                        sum(Round(sol.product_uom_qty / u.factor * u2.factor,2)) AS sales_qty
                    FROM sale_order_line sol
                        JOIN sale_order so ON sol.order_id = so.id
                        Inner Join product_product pro ON sol.product_id = pro.id
                        Inner Join product_template pt ON pro.product_tmpl_id = pt.id
                        Inner Join uom_uom u ON u.id = sol.product_uom
                        Inner Join uom_uom u2 ON u2.id = pt.uom_id
                        Inner Join res_company cmp on cmp.id = so.company_id
                        Inner Join stock_warehouse ware on ware.id = so.warehouse_id 
                        Inner Join product_category cat on cat.id = pt.categ_id
                    WHERE NOT sol.id = ANY(except_line) and so.state::text = ANY (ARRAY['sale'::character varying::text, 'done'::character varying::text])  
                    and so.date_order::date >= start_date and so.date_order::date <= end_date
                    --company dynamic condition
                    and 1 = case when array_length(company_ids,1) >= 1 then 
                        case when so.company_id = ANY(company_ids) then 1 else 0 end
                        else 1 end
                    --product dynamic condition
                    and 1 = case when array_length(product_ids,1) >= 1 then 
                        case when sol.product_id = ANY(product_ids) then 1 else 0 end
                        else 1 end
                    --category dynamic condition
                    and 1 = case when array_length(category_ids,1) >= 1 then 
                        case when pt.categ_id = ANY(category_ids) then 1 else 0 end
                        else 1 end
                    --warehouse dynamic condition
                    and 1 = case when array_length(warehouse_ids,1) >= 1 then 
                        case when so.warehouse_id = ANY(warehouse_ids) then 1 else 0 end
                        else 1 end
                    group by so.company_id, cmp.name, sol.product_id, pro.default_code, pt.categ_id, cat.complete_name, so.warehouse_id, ware.name, sol.order_id
                ) foo
                    )T
                    group by cmp_id, cmp_name, p_id, prod_name, categ_id, cat_name, wh_id, ware_name;
                
                END; 
                
                $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
    """
    cr.execute(query)

def get_abc_sales_analysis_by_company(cr):
    query = """
        -- DROP FUNCTION public.get_abc_sales_analysis_data_by_company(integer[], integer[], integer[], date, date, text, integer[]);
        CREATE OR REPLACE FUNCTION public.get_abc_sales_analysis_data_by_company(
            IN company_ids integer[],
            IN product_ids integer[],
            IN category_ids integer[],
            IN start_date date,
            IN end_date date,
            IN abc_analysis_type text,
            IN except_line integer[])
          RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, sales_qty numeric, sales_amount numeric, sales_amount_per numeric, cum_sales_amount_per numeric, analysis_category text) AS
        $BODY$
                BEGIN
                    Return Query
                    
                    with all_data as (
                        Select T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name, 
                        sum(T.sales_qty) as sales_qty, sum(T.sales_amount) as sales_amount
                from get_sales_data(company_ids, product_ids, category_ids, '{}', start_date, end_date, except_line) T
                group by T.company_id, T.company_name, T.product_id, T.product_name, T.product_category_id, T.category_name
                    ),
                    company_wise_abc_analysis as(
                        Select a.company_id, a.company_name, sum(a.sales_qty) as total_sales, sum(a.sales_amount) as total_sales_amount
                        from all_data a
                        group by a.company_id, a.company_name
                    )
        
                    Select final_data.* from 
                    (
                        Select 
                            result.*,
                            case 
                                when result.cum_sales_amount_per < 80 then 'A' 
                                when result.cum_sales_amount_per >= 80 and result.cum_sales_amount_per <= 95 then 'B'
                                when result.cum_sales_amount_per > 95 then 'C'
                            end as analysis_category 
                        from
                        (
                            Select 
                                *, 
                                sum(cum_data.sales_amount_per) 
                    over (partition by cum_data.company_id order by cum_data.company_id, cum_data.sales_amount_per desc rows between unbounded preceding and current row) as cum_sales_amount_per
                            from 
                            (
                                Select 
                                    all_data.*, 
                                    case when wwabc.total_sales_amount <= 0.00 then 0 else 
                                        Round((all_data.sales_amount / wwabc.total_sales_amount * 100.0)::numeric,2) 
                                    end as sales_amount_per
                                from all_data
                                    Inner Join company_wise_abc_analysis wwabc on all_data.company_id = wwabc.company_id
                                order by sales_amount_per desc
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
    """
    cr.execute(query)

def create_get_xyz_analysis_data_sp(cr):
    query = """
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
    """
    cr.execute(query)

def get_abc_xyz_analysis_report(cr):
    query = """
        -- DROP FUNCTION public.get_abc_xyz_analysis_report(integer[], integer[], integer[], date, date, text, text, integer[]);
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

    """
    cr.execute(query)

def get_abc_sales_frequency_analysis_data(cr):
    query = """
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
                                when result.cum_total_orders_per < 80 then 'A' 
                                when result.cum_total_orders_per >= 80 and result.cum_total_orders_per <= 95 then 'B'
                                when result.cum_total_orders_per > 95 then 'C'
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
    """
    cr.execute(query)
