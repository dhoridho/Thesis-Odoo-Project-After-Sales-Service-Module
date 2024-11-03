DROP FUNCTION if exists public.update_customer_rfm_segment(integer[], date, date);

CREATE OR REPLACE FUNCTION public.update_customer_rfm_segment(
    company_ids integer[],
    start_date date,
    end_date date)
RETURNS void AS
$BODY$
    BEGIN

        update sale_order set rfm_segment_id = null where rfm_segment_id is not null;

        update res_partner cust set rfm_score_id = D.score_id, rfm_segment_id = D.segment_id
        From (
        Select * from get_rfm_analysis_data(company_ids, start_date, end_date) T ) D
        Where D.customer_id = cust.id;

        update sale_order so set rfm_segment_id = orders.rfm_segment_id from
        (
            Select
                so.partner_id,
                so.id as order_id,
                partner.rfm_segment_id
            From
                sale_order so
                    Inner join res_partner partner on partner.id = so.partner_id
            Where so.state not in ('draft','cancel','sent')
            and so.date_order::date >= start_date and so.date_order::date <= end_date
            and 1 = case when array_length(company_ids,1) >= 1 then
                case when so.company_id = ANY(company_ids) then 1 else 0 end
                else 1 end
        )orders
        where orders.order_id = so.id;

   update setu_rfm_segment set from_date = start_date, to_date = end_date, calculated_on= (select now()::date);

    END;
    $BODY$
LANGUAGE plpgsql VOLATILE
COST 100;