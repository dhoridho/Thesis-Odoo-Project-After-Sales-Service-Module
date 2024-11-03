odoo.define('equip3_pos_masterdata.MonitorAutoSyncDetail', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const {posbus} = require('point_of_sale.utils');
    const {useState} = owl;

    class MonitorAutoSyncDetail extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                datalist: [],
                data: {},
                count: {
                    product: 0,
                    product_stock: 0,
                    pricelist: 0,
                    promotion: 0,
                    coupon: 0,
                },
                filter: ['product', 'product_stock', 'pricelist', 'promotion', 'coupon'],
            });

            this.applyDataset();
        }

        onChangeApplyFilter(ev){
            let filter = ev.target.value;
            if(this.props.dataset && this.props.dataset.data){
                for(let i in this.props.dataset.data){
                    let data = this.props.dataset.data[i];
                    this.state.datalist.push(data);
                }
                this.state.datalist.sort((a, b) => a.sequence - b.sequence);
                if(filter != 'all'){
                    this.state.datalist = this.state.datalist.filter(o=>o.type == filter);
                } 
            }
        }

        applyDataset(){
            if(this.props.dataset && this.props.dataset.data){
                for(let i in this.props.dataset.data){
                    let data = this.props.dataset.data[i];
                    this.state.datalist.push(data);
                }
                this.state.datalist.sort((a, b) => a.sequence - b.sequence);
                this.state.datalist = this.state.datalist.filter(o=>o.type == 'product'); // default filter Product
            }

            if(this.props.dataset.data){
                this.state.data = this.props.dataset.data;
            }
            if(this.props.dataset.count.product){
                this.state.count.product += this.props.dataset.count.product;
            }
            if(this.props.dataset.count.product_stock){
                this.state.count.product_stock += this.props.dataset.count.product_stock;
            }
            if(this.props.dataset.count.pricelist){
                this.state.count.pricelist += this.props.dataset.count.pricelist;
            }
            if(this.props.dataset.count.promotion){
                this.state.count.promotion += this.props.dataset.count.promotion;
            }
            if(this.props.dataset.count.coupon){
                this.state.count.coupon += this.props.dataset.count.coupon;
            }
        }

        get_date(date){
            return date;
        }

        get_duration(duration){
            return (duration/1000).toFixed(2);
        }

        async close(ev) {
            this.trigger('close-popup');
        }

    }

    MonitorAutoSyncDetail.template = 'MonitorAutoSyncDetail';
    Registries.Component.add(MonitorAutoSyncDetail);
    return MonitorAutoSyncDetail;
});