odoo.define('equip3_pos_masterdata.TakeAwayScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const core = require('web.core');
    const QWeb = core.qweb;

    class TakeAwayScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.orders = this.env.pos.db.getOrderReceipts();
            // const orderTicketsBackup = JSON.parse(this.env.pos.config.order_receipt_tickets);
            // if (this.orders.length == 0) {
            //     this.orders = orderTicketsBackup
            // }
        }
        mounted() {
            this._tableLongpolling();
            this.tableLongpolling = setInterval(this._tableLongpolling.bind(this), 2000);
            this.adust_masonry();
        }
        adust_masonry(){
            if($('.adjust_tickets_content').length){
                $('.adjust_tickets_content').masonry('destroy');
                $('.adjust_ticketds_content').masonry({
                  itemSelector: '.kitchen-box',
                  columnWidth: '.kitchen-box'
                });
            }
        }
        willUnmount() {
            clearInterval(this.tableLongpolling);
            //no need remove events, we keep always listen events
        }
        _tableLongpolling() {
            this.orders = this.env.pos.db.getOrderReceipts()
            //Check done receipt/tickets and remove it after 2 minutes done;
            for(let receipt of this.doneOrderList){
                if(typeof receipt.update_time != 'undefined'){
                    let countUndone = receipt.new.filter((x) => ['Done','Ready Transfer'].includes(x.state) == false).length;
                    if(countUndone == 0){
                        if(new Date().getTime() > this._timeout(receipt) ) {
                            this.env.pos.db.removeOrderReceiptOutOfDatabase(receipt.uid)
                        }
                    }
                }
            }
            this.render();
            this.adust_masonry();
        }
        get orderList(){
            return this.orders.filter((x) => {
                if(x.take_away_order == true && (!x.takeaway_cleared)){
                    return true;
                }
                return false;
            });
        }
        get doneOrderList(){
            return this.orderList.filter((x)=> ['Done'].includes(x['state']));
        }
        get NewTakeAwayOrders(){
            return this.orderList.filter((x)=> !['Ready Transfer', 'Done', 'Paid'].includes(x['state']));
        }
        _timeout(receipt){
            return receipt.update_time + 2*60*1000; //2 minutes;
        }
        get DoneTakeAwayOrders(){
            let orders = this.doneOrderList;
            // orders = orders.filter((receipt) => {
            //     if(typeof receipt.update_time != 'undefined'){
            //         let countUndone = receipt.new.filter((x) => ['Done','Ready Transfer'].includes(x.state) == false).length;
            //         if(countUndone == 0){
            //             if(new Date().getTime() > this._timeout(receipt) == false) {
            //                 return true;
            //             }
            //         }
            //         if(countUndone != 0){
            //             return true;
            //         }
            //     }
            //     return false;
            // });
            return orders;
        }

        async clearScreen() {
            this.orders.forEach(r => {
                r.takeaway_cleared = true
            });
            this.env.pos.db.saveOrderReceipts(this.orders);
            posbus.trigger('save-receipt')
            this.env.pos.alert_message({
                title: 'Success',
                body: 'Your Screen is cleared',
            });
            $('.adjust_tickets_content').html('');
        }
    }

    TakeAwayScreen.template = 'TakeAwayScreen';

    Registries.Component.add(TakeAwayScreen);

    return TakeAwayScreen;
});
