DROP FUNCTION if exists public.get_rfm_analysis_data(integer[], date, date);

CREATE OR REPLACE FUNCTION public.get_rfm_analysis_data(
IN company_ids integer[],
IN start_date date,
IN end_date date)
RETURNS TABLE(company_id integer, customer_id integer, total_orders integer, total_order_value numeric, days_from_last_purchase integer, recency integer, frequency integer, monetization integer, score character varying, score_id integer, segment_id integer) AS
$BODY$
    BEGIN
            Drop Table if exists rfm_transaction_table;
        CREATE TEMPORARY TABLE rfm_transaction_table(
            company_id integer,  customer_id integer,
            total_orders integer, total_order_value numeric, days_from_last_purchase integer
        );

        insert into rfm_transaction_table
        Select
            so.company_id,
            so.partner_id,
            count(so.id) as total_orders,
            sum(Round(so.amount_total /
            CASE COALESCE(so.currency_rate, 0::numeric)
                WHEN 0 THEN 1.0
                ELSE so.currency_rate
            END, 2)) as total_order_value,
            DATE_PART('day', now()::timestamp - max(so.date_order)::timestamp) as days_from_last_purchase
        From
            Sale_order so
        Where so.state not in ('draft','cancel','sent')
        and so.date_order::date >= start_date and so.date_order::date <= end_date
        and 1 = case when array_length(company_ids,1) >= 1 then
            case when so.company_id = ANY(company_ids) then 1 else 0 end
            else 1 end
        group by so.partner_id, so.company_id;

        Return Query
        with all_data as (
            Select
            row_number() over(partition by rtt.company_id order by rtt.company_id, rtt.days_from_last_purchase) as recency_id,
            row_number() over(partition by rtt.company_id order by rtt.company_id, rtt.total_orders desc) as frequency_id,
            row_number() over(partition by rtt.company_id order by rtt.company_id, rtt.total_order_value desc) as monetization_id,
            *
            from rfm_transaction_table rtt
        ),
        customer_count as (
            Select rtt.company_id, count(rtt.customer_id) as total_customers from rfm_transaction_table rtt
            group by rtt.company_id
        )


        Select D.*, (D.recency::char || D.frequency::char || D.monetization::char)::character varying as score,
            rsc.id as score_id,
            rsc.rfm_segment_id
        from
        (
            Select
                ad.company_id, ad.customer_id,
                ad.total_orders, ad.total_order_value, ad.days_from_last_purchase,
                case
                    when ((recency_id * 100.0) / total_customers) < 26 then 1
                    when ((recency_id * 100.0) / total_customers) >= 26 and ((recency_id * 100.0) / total_customers) < 51 then 2
                    when ((recency_id * 100.0) / total_customers) >= 51 and ((recency_id * 100.0) / total_customers) < 76 then 3
                    when ((recency_id * 100.0) / total_customers) >= 76 then 4
                end as recency,
                case
                    when ((frequency_id * 100.0) / total_customers) < 26 then 1
                    when ((frequency_id * 100.0) / total_customers) >= 26 and ((frequency_id * 100.0) / total_customers) < 51 then 2
                    when ((frequency_id * 100.0) / total_customers) >= 51 and ((frequency_id * 100.0) / total_customers) < 76 then 3
                    when ((frequency_id * 100.0) / total_customers) >= 76 then 4
                end as frequency,
                case
                    when ((monetization_id * 100.0) / total_customers) < 26 then 1
                    when ((monetization_id * 100.0) / total_customers) >= 26 and ((monetization_id * 100.0) / total_customers) < 51 then 2
                    when ((monetization_id * 100.0) / total_customers) >= 51 and ((monetization_id * 100.0) / total_customers) < 76 then 3
                    when ((monetization_id * 100.0) / total_customers) >= 76 then 4
                end as monetization
            From
                all_data ad
                    Inner Join customer_count cc on cc.company_id = ad.company_id
        )D
            Inner Join setu_rfm_score rsc on rsc.name = (D.recency::char || D.frequency::char || D.monetization::char)::character varying;


    END;
    $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;