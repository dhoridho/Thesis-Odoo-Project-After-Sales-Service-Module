odoo.define('equip3_pos_masterdata.KitchenProcessingTimes', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class KitchenProcessingTimes extends PosComponent {
        constructor() {
            super(...arguments);
            this.default_time_active_time = '';
            this.total_product_default_time= '';
            this.props.order.new.forEach((l) => {
                    this.total_product_default_time += l.default_time ? l.default_time : 0;
                    if (l.default_time_active_time && this.default_time_active_time=='') {
                        this.default_time_active_time = l.default_time_active_time;
                    }
                    // l.default_time_active_time = new Date().getTime();
                    // l.is_default_timer_active = 1;
            });
            this.state = {
                startTime: this.props.order.request_time || new Date().getTime(),
            };
        }

        get warningWaitingTime() {
            var diff = new Date().getTime() - this.state.startTime;
            var msec = diff;
            var hh = `0${Math.floor(msec / 1000 / 60 / 60)}`;
            msec -= hh * 1000 * 60 * 60;
            var mm = `0${Math.floor(msec / 1000 / 60)}`;
            if ((Math.floor(msec / 1000 / 60) >= this.env.pos.config.period_minutes_warning)) {
                return true
            } else {
                return false
            }

        }
        get warningDefaultTime() {
            if (this.default_time_active_time) {
                var diff = new Date().getTime() - this.default_time_active_time;
                var msec = diff;
                var hh = `0${Math.floor(msec / 1000 / 60 / 60)}`;
                msec -= hh * 1000 * 60 * 60;
                var mm = `0${Math.floor(msec / 1000 / 60)}`;
                if ((Math.floor(msec / 1000 / 60) >= this.total_product_default_time)) {
                    return true
                } else {
                    return false
                }
            } else {
                return false
            }

        }
        get getDefaultProcessingTime() {
            if (this.default_time_active_time) {
                let self = this;
                var diff = new Date().getTime() - this.default_time_active_time;
                var msec = diff;
                var hh = `0${Math.floor(msec / 1000 / 60 / 60)}`;
                msec -= hh * 1000 * 60 * 60;
                var mm = `0${Math.floor(msec / 1000 / 60)}`;
                msec -= mm * 1000 * 60;
                var ss = `0${Math.floor(msec / 1000)}`;
                msec -= ss * 1000;
                setTimeout(function () {
                    self.render()
                }, 1000)
                return hh.slice(-2) + ":" + mm.slice(-2) + ":" + ss.slice(-2);
            } else {
                return ''
            }
        }
        get getProcessingTime() {
            let self = this;
            var diff = new Date().getTime() - this.state.startTime;
            var msec = diff;
            var hh = `0${Math.floor(msec / 1000 / 60 / 60)}`;
            msec -= hh * 1000 * 60 * 60;
            var mm = `0${Math.floor(msec / 1000 / 60)}`;
            msec -= mm * 1000 * 60;
            var ss = `0${Math.floor(msec / 1000)}`;
            msec -= ss * 1000;
            setTimeout(function () {
                self.render()
            }, 1000)
            return hh.slice(-2) + ":" + mm.slice(-2) + ":" + ss.slice(-2);
        }
    }

    KitchenProcessingTimes.template = 'KitchenProcessingTimes';

    Registries.Component.add(KitchenProcessingTimes);

    return KitchenProcessingTimes;
});


odoo.define('equip3_pos_masterdata.KitchenProcessingTimesBackward', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class KitchenProcessingTimesBackward extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = {
                startTime: this.props.order.request_time || new Date().getTime(),
            };
        }

        get redWaitingtime(){
            let self = this;
            var diff = new Date().getTime() - this.state.startTime;
            var period_minutes_warning = (this.env.pos.config.period_minutes_warning * 60) * 1000
            var diff_backward = period_minutes_warning - diff
            var msec = diff_backward;
            if(msec >= 0) {
                return false
            } else{
                if($('.order-item.order-item-detail.order-detail-fnb tr').length > 0){
                    if(!$('.order-item.order-item-detail.order-detail-fnb tr').hasClass('bg-danger')){
                        $('.order-item.order-item-detail.order-detail-fnb tr').addClass('bg-danger')
                    }
                }
                return true
            }
        }


        get getProcessingTime() {
            let self = this;
            var diff = new Date().getTime() - this.state.startTime;
            var period_minutes_warning = ((this.env.pos.config.period_minutes_warning+1) * 60) * 1000
            var diff_backward = period_minutes_warning - diff
            var msec = diff_backward;
            if(msec >= 0) {
                var hh = `0${Math.floor(msec / 1000 / 60 / 60)}`;
                msec -= hh * 1000 * 60 * 60;
                var mm = `0${Math.floor(msec / 1000 / 60)}`;
                msec -= mm * 1000 * 60;
                var ss = `0${Math.floor(msec / 1000)}`;
                msec -= ss * 1000;
                setTimeout(function () {
                    self.render()
                }, 1000)
                return hh.slice(-2) + ":" + mm.slice(-2);
            } else{
                msec = msec * -1
                var hh = `0${Math.floor(msec / 1000 / 60 / 60)}`;
                msec -= hh * 1000 * 60 * 60;
                var mm = `0${Math.floor(msec / 1000 / 60)}`;
                msec -= mm * 1000 * 60;
                var ss = `0${Math.floor(msec / 1000)}`;
                msec -= ss * 1000;
                setTimeout(function () {
                    self.render()
                }, 1000)
                var negatif = ''
                if (hh.slice(-2)!='00' || mm.slice(-2) != '00'){
                    negatif = '- '
                }
                return negatif+hh.slice(-2) + ":" + mm.slice(-2);
            }
            
        }
    }

    KitchenProcessingTimesBackward.template = 'KitchenProcessingTimesBackward';

    Registries.Component.add(KitchenProcessingTimesBackward);

    return KitchenProcessingTimesBackward;
});
