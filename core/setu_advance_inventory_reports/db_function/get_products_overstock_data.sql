-- DROP FUNCTION public.get_products_overstock_data(integer[], integer[], integer[], integer[], date, date, integer);

CREATE OR REPLACE FUNCTION public.get_products_overstock_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[],
    IN start_date date,
    IN end_date date,
    IN advance_stock_days integer)
  RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, sales numeric, ads numeric, qty_available numeric, outgoing numeric, incoming numeric, forecasted_stock numeric, demanded_qty numeric, coverage_days numeric, overstock_qty numeric, overstock_value numeric, last_purchase_date date, last_purchase_qty numeric, last_purchase_price numeric, currency_name character varying, vendor_name character varying, wh_overstock_qty_per numeric, wh_overstock_value_per numeric, turnover_ratio numeric, stock_movement text) AS
$BODY$
BEGIN
    Drop Table if exists overstock_transaction_table;
    CREATE TEMPORARY TABLE overstock_transaction_table(
        company_id INT,
        company_name character varying,
        product_id INT,
        product_name character varying,
        product_category_id INT,
        category_name character varying,
        warehouse_id INT,
        warehouse_name character varying,
        sales numeric DEFAULT 0,
        ads numeric DEFAULT 0,
        qty_available Numeric DEFAULT 0,
        outgoing numeric DEFAULT 0,
        incoming Numeric DEFAULT 0,
        forecasted_stock Numeric DEFAULT 0,
        demanded_qty Numeric DEFAULT 0,
        coverage_days Numeric DEFAULT 0,
        overstock_qty Numeric DEFAULT 0,
        overstock_value Numeric DEFAULT 0,
        last_purchase_date Date,
        last_purchase_qty Numeric,
        last_purchase_price Numeric,
        currency_name character varying,
        vendor_name character varying
    );

    Insert into overstock_transaction_table
    Select
        final_data.company_id, cmp.name, final_data.product_id, prod.default_code,
        tmpl.categ_id, cat.complete_name, final_data.warehouse_id, ware.name,
        final_data.sales, final_data.ads, final_data.qty_available, final_data.outgoing, final_data.incoming,
        final_data.forecasted_stock, final_data.demanded_qty, final_data.coverage_days, final_data.overstock_qty,
        round((final_data.overstock_qty * stock_value)::numeric,0) ovestock_value, final_data.purchase_date,
        final_data.purchase_qty, final_data.purchase_price, final_data.currency, final_data.vendor
    From
    (
        Select
            stock_data.* , coalesce(round(sales_data.sales,0),0) as sales, coalesce(sales_data.ads,0) as ads,
            Round(coalesce(advance_stock_days * sales_data.ads,0),0) as demanded_qty,
            coalesce(Round((stock_data.forecasted_stock / case when sales_data.ads <= 0.0000 then 0.001 else sales_data.ads end)::numeric, 0),0) as coverage_days,
            coalesce(ir_property.value_float,0) as stock_value,
            coalesce(Round((stock_data.forecasted_stock - (advance_stock_days * coalesce(sales_data.ads,0)))::numeric,0),0) as overstock_qty,
            po_data.purchase_date, po_data.purchase_qty, po_data.purchase_price, po_data.currency, po_data.vendor
        From
        (
            Select T.* from get_products_forecasted_stock_data(company_ids, product_ids, category_ids, warehouse_ids) T
            where t.forecasted_stock > 0
        )stock_data

        Left Join
        (
            select *, Round(D1.sales / ((end_date - start_date) + 1),2) as ads
            from get_sales_transaction_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date) D1
        )sales_data
            on stock_data.product_id = sales_data.product_id and stock_data.warehouse_id = sales_data.warehouse_id
            Left Join ir_property on ir_property.name = 'standard_price' and ir_property.res_id = 'product.product,' || stock_data.product_id
            and ir_property.company_id = stock_data.company_id
        Left Join
        (
            Select
                po_line.product_id,
                ware.id as warehouse_id,
                po.date_order::date as purchase_date,
                po_line.product_uom_qty as purchase_qty,
                po_line.price_unit as purchase_price,
                cur.name as currency,
                partner.name as vendor
            From
            (
                Select tmpl.categ_id, pol.product_id, max(pol.id) po_line_id
                from purchase_order_line pol
                    Inner Join product_product prod on prod.id = pol.product_id
                    Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
	            Inner Join purchase_order po on po.id = pol.order_id
	            Inner join stock_picking_type picking_type on picking_type.id = po.picking_type_id
	            Inner Join stock_warehouse ware on ware.id = picking_type.warehouse_id

                where 1 = case when array_length(product_ids,1) >= 1 then
                        case when pol.product_id = ANY(product_ids) then 1 else 0 end
                      else 1 end
                and 1 = case when array_length(category_ids,1) >= 1 then
                        case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                    else 1 end
                group by pol.product_id, tmpl.categ_id, ware.id
            )p_l
                Inner Join purchase_order_line po_line on p_l.po_line_id = po_line.id
                Inner Join purchase_order po on po.id = po_line.order_id
                Inner join stock_picking_type picking_type on picking_type.id = po.picking_type_id
                Inner Join stock_warehouse ware on ware.id = picking_type.warehouse_id
                Inner Join res_partner partner on partner.id = po.partner_id
                Inner Join res_currency cur on cur.id = po.currency_id
            where 1 = case when array_length(warehouse_ids,1) >= 1 then
                    case when ware.id = ANY(warehouse_ids) then 1 else 0 end
                  else 1 end
            and 1 = case when array_length(company_ids,1) >= 1 then
                    case when po.company_id = ANY(company_ids) then 1 else 0 end
                else 1 end
        )po_data
            on po_data.product_id = stock_data.product_id and po_data.warehouse_id = stock_data.warehouse_id
    )final_data
        Inner Join res_company cmp on cmp.id = final_data.company_id
        Inner Join product_product prod on prod.id = final_data.product_id
        Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
        Inner Join product_category cat on cat.id = tmpl.categ_id
        Inner Join stock_warehouse ware on ware.id = final_data.warehouse_id;

    Return Query
    with all_data as (
        Select * from overstock_transaction_table
    ),
    warehouse_wise_overstock as(
        Select ott.warehouse_id, ott.company_id, sum(ott.overstock_qty) as total_overstock_qty, sum(ott.overstock_value) as total_overstock_value
        from overstock_transaction_table ott
        group by ott.warehouse_id, ott.company_id
    ),
    fsn_analysis as(
        Select *
        from get_inventory_fsn_analysis_report(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, 'all') f_data
    )

    Select
        all_data.*,
        case when wwover.total_overstock_qty <= 0.00 then 0 else
            Round(all_data.overstock_qty / wwover.total_overstock_qty * 100,2)
        end as warehouse_overstock_qty ,
        case when wwover.total_overstock_value <= 0.00 then 0 else
            Round(all_data.overstock_value / wwover.total_overstock_value * 100,2)
        end as warehouse_overstock_value,
        fsn.turnover_ratio,
        fsn.stock_movement
    from all_data
        Inner Join warehouse_wise_overstock wwover on wwover.warehouse_id = all_data.warehouse_id
        Left Join fsn_analysis fsn on fsn.product_id = all_data.product_id and fsn.warehouse_id = all_data.warehouse_id;

END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;
