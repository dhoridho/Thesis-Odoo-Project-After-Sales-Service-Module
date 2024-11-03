odoo.define('equip3_construction_operation.list_editable_renderer', function (require) {
    "use strict";


    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        _renderRow: function (record) {
            var self = this;
            var $tr = this._super.apply(this, arguments);
            if (self.__parentedParent.model === 'job.estimate'){
                let job_estimate_one2many = ['material.estimate', 'labour.estimate', 'subcon.estimate',
                        'equipment.estimate', 'internal.assets', 'overhead.estimate', 'project.scope.estimate', 'section.estimate', 'variable.estimate']
                if (job_estimate_one2many.includes(self.state.model) && self.__parentedParent.recordData['contract_category'] === 'var') {
                    if ($tr[0].lastChild.className === 'o_list_record_remove'){
                        if (record.data['is_vo_generated'] === true){
                            // console.log('record', record)
                            // console.log('check', $tr)
                            $tr[0].lastChild.style.display = 'none'
                        }
                    }
                }
            }
            
            if (self.__parentedParent.model === 'internal.transfer.budget'){
                let job_estimate_one2many = [
                    'internal.transfer.budget.material.line', 
                    'internal.transfer.budget.labour.line', 
                    'internal.transfer.budget.overhead.line', 
                    'internal.transfer.budget.internal.asset.line', 
                    'internal.transfer.budget.equipment.line', 
                    'internal.transfer.budget.subcon.line',
                    'internal.transfer.budget.project.scope',
                    'internal.transfer.budget.section',
                ]
                if (job_estimate_one2many.includes(self.state.model)) {
                    if ($tr[0].lastChild.className === 'o_list_record_remove'){
                        if (record.data['is_generated'] === true){
                            $tr[0].lastChild.style.display = 'none'
                        }
                    }
                }
            }

            return $tr;
        },

        // _renderRows: function () {
        //     var res= this._super.apply(this, arguments);
        //     var self = this;
        //     // if (this.addCreateLine) {
        //     //     let internal_transfer_model = ['internal.transfer.budget.material.line', 'internal.transfer.budget.labour.line',
        //     //         'internal.transfer.budget.overhead.line', 'internal.transfer.budget.internal.asset.line', 'internal.transfer.budget.equipment.line',
        //     //         'internal.transfer.budget.subcon.line']
        //     //     if (internal_transfer_model.includes(this.state.model) ) {
        //     //         if (this.state.context['default_is_change_allocation'] || this.__parentedParent.record.context['default_is_change_allocation']){
        //     //             res[res.length-1].css('display', 'None')
        //     //         }
        //     //     }
        //     // }
        //     return res
        // },
    })
})
