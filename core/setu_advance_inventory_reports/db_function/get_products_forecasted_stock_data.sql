-- DROP FUNCTION public.get_products_forecasted_stock_data(integer[], integer[], integer[], integer[]);

CREATE OR REPLACE FUNCTION public.get_products_forecasted_stock_data(
    IN company_ids integer[],
    IN product_ids integer[],
    IN category_ids integer[],
    IN warehouse_ids integer[])
  RETURNS TABLE(company_id integer, company_name character varying, product_id integer, product_name character varying, product_category_id integer, category_name character varying, warehouse_id integer, warehouse_name character varying, qty_available numeric, outgoing numeric, incoming numeric, forecasted_stock numeric) AS
$BODY$
BEGIN
    Return Query
    Select
        T.company_id, cmp.name as company_name, T.product_id, coalesce(prod.default_code, tmpl.name) as product_name,
        T.categ_id as product_category_id, cat.complete_name as category_name, T.warehouse_id, ware.name as warehouse_name,
        --sum(T.qty_available)::numeric, sum(T.incoming)::numeric, sum(T.outgoing)::numeric, (sum(T.qty_available) + sum(T.incoming) - sum(T.outgoing))::numeric as forecasted_qty
	sum(T.qty_available)::numeric as qty_available, sum(T.outgoing)::numeric as outgoing, sum(T.incoming)::numeric as incoming, (sum(T.qty_available) + sum(T.incoming) - sum(T.outgoing))::numeric as forecasted_qty
    From
    (
        Select
            quant.company_id,
            quant.product_id,
            tmpl.categ_id,
            ware.id as warehouse_id,
            sum(quantity) as qty_available,
            sum(reserved_quantity) as outgoing,
            0 as incoming
        from
            stock_quant quant
                Inner Join stock_location loc on loc.id = quant.location_id
                Inner Join product_product prod on prod.id = quant.product_id
                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                Left Join stock_warehouse ware ON loc.parent_path::text ~~ concat('%/', ware.view_location_id, '/%')
        Where loc.usage = 'internal' and prod.active = True and tmpl.active = True and tmpl.type = 'product'
            --company dynamic condition
            and 1 = case when array_length(company_ids,1) >= 1 then
                case when quant.company_id = ANY(company_ids) then 1 else 0 end
                else 1 end
            --product dynamic condition
            and 1 = case when array_length(product_ids,1) >= 1 then
                case when quant.product_id = ANY(product_ids) then 1 else 0 end
                else 1 end
            --category dynamic condition
            and 1 = case when array_length(category_ids,1) >= 1 then
                case when tmpl.categ_id = ANY(category_ids) then 1 else 0 end
                else 1 end
            --warehouse dynamic condition
            and 1 = case when array_length(warehouse_ids,1) >= 1 then
                case when ware.id = ANY(warehouse_ids) then 1 else 0 end
                else 1 end
             group by quant.company_id,quant.product_id,tmpl.categ_id,ware.id
        Union All

        Select
            move.company_id,
            move.product_id,
            tmpl.categ_id,
            dest_ware.id as warehouse_id,
            0 as qty_available,
            0 as outgoing,
            sum(move.product_uom_qty)
        from
            stock_move move
                Inner Join stock_location source on source.id = move.location_id
                Inner Join stock_location dest_location on dest_location.id = move.location_dest_id
                Inner Join product_product prod on prod.id = move.product_id
                Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
                Left Join stock_warehouse source_ware ON source.parent_path::text ~~ concat('%/', source_ware.view_location_id, '/%')
                Left Join stock_warehouse dest_ware ON dest_location.parent_path::text ~~ concat('%/', dest_ware.view_location_id, '/%')
        Where
            source.usage = 'supplier' and dest_location.usage = 'internal' and move.state not in ('draft','done','cancel') and
            prod.active = True and tmpl.active = True and tmpl.type = 'product'
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
                case when dest_ware.id = ANY(warehouse_ids) then 1 else 0 end
                else 1 end
            group by move.company_id,move.product_id,tmpl.categ_id,dest_ware.id
    )T
        Inner Join res_company cmp on cmp.id = T.company_id
        Inner Join product_product prod on prod.id = T.product_id
        Inner Join product_template tmpl on tmpl.id = prod.product_tmpl_id
        Inner Join product_category cat on cat.id = tmpl.categ_id
        Inner Join stock_warehouse ware on ware.id = T.warehouse_id

        group by T.company_id,T.product_id,T.categ_id,T.warehouse_id,cmp.name,prod.default_code,tmpl.name,cat.complete_name,ware.name;

END; $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;
