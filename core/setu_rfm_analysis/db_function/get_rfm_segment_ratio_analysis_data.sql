DROP FUNCTION if exists public.get_rfm_segment_ratio_analysis_data();

CREATE OR REPLACE FUNCTION public.get_rfm_segment_ratio_analysis_data()
  RETURNS TABLE(segment_id integer, segment_name character varying, total_customer bigint, ratio numeric) AS
$BODY$
BEGIN
    Return Query
    with all_data as (
        Select
            segment.id as segment_id,
            segment.name as segment_name,
            sum(case when coalesce(partner.id,0) > 0 then 1 else 0 end) as customers
        from
            res_partner partner
                right Join setu_rfm_segment segment on segment.id = partner.rfm_segment_id
        group by segment.id, segment.name
    ),
    total_customer as (
        Select sum(customers) as tc from all_data
    )

    Select
        ad.*,
        Round((ad.customers / (case when total_customer.tc >=1 then total_customer.tc else 1 end)) * 100, 2)
    From
        all_data ad, total_customer;

END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;