odoo.define('equip3_construction_sales_operation.variation_order', function (require) {
    'use strict';

    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({

        // Change string of header cell
        // Currently this only change unit price and quantity of estimations field
        // on job.estimate, sale.order.const, job.estimate.existing.quotation.const
        _renderHeaderCell: function (record, node, colIndex, options) {
            var self = this;
            var $result = this._super.apply(this, arguments);
            if (['job.estimate', 'sale.order.const', 'job.estimate.existing.quotation.const'].includes(self.__parentedParent.model)) {
                let job_estimate_one2many = ['material.estimate', 'labour.estimate', 'subcon.estimate',
                    'equipment.estimate', 'internal.assets', 'overhead.estimate']
                let sale_order_one2many = ['sale.order.material.line', 'sale.order.labour.line', 'sale.order.subcon.line',
                    'sale.order.overhead.line','sale.order.equipment.line','sale.internal.asset.line',]
                let job_estimate_existing_quotation_one2many = ['job.estimate.existing.line.material', 'job.estimate.existing.line.labour',
                'job.estimate.existing.line.overhead','job.estimate.existing.line.asset','job.estimate.existing.line.equipment','job.estimate.existing.line.subcon',]

                if (self.__parentedParent.model === 'job.estimate') {
                    if (job_estimate_one2many.includes(self.state.model) && self.__parentedParent.recordData['contract_category'] === 'var') {
                        if (self.state.model === 'labour.estimate'){
                            if ($result[0].dataset['name'] === 'contractors') {
                                $result[0].innerText = 'VO Contractors';
                            } else if ($result[0].dataset['name'] === 'unit_price') {
                                $result[0].innerText = 'VO Unit Price';
                            }
                            else if ($result[0].dataset['name'] === 'time') {
                                $result[0].innerText = 'VO Time';
                            }
                        } else{
                            if ($result[0].dataset['name'] === 'quantity') {
                                $result[0].innerText = 'VO Quantity';
                            } else if ($result[0].dataset['name'] === 'unit_price') {
                                $result[0].innerText = 'VO Unit Price';
                            }
                        }
                    }
                }
                else if (self.__parentedParent.model === 'job.estimate.existing.quotation.const') {
                    if (job_estimate_existing_quotation_one2many.includes(self.state.model) && self.__parentedParent.recordData['contract_category'] === 'var') {
                        if (self.state.model === 'job.estimate.existing.line.labour'){
                            if ($result[0].dataset['name'] === 'contractors') {
                                $result[0].innerText = 'VO Contractors';
                            } else if ($result[0].dataset['name'] === 'unit_price') {
                                $result[0].innerText = 'VO Unit Price';
                            }
                            else if ($result[0].dataset['name'] === 'time') {
                                $result[0].innerText = 'VO Time';
                            }
                        } else{
                            if ($result[0].dataset['name'] === 'quantity') {
                                $result[0].innerText = 'VO Quantity';
                            } else if ($result[0].dataset['name'] === 'unit_price') {
                                $result[0].innerText = 'VO Unit Price';
                            }
                        }
                    }
                }
                else if (self.__parentedParent.model === 'sale.order.const') {
                    if (sale_order_one2many.includes(self.state.model) && self.__parentedParent.recordData['contract_category'] === 'var') {
                        if (self.state.model === 'sale.order.labour.line'){
                            if ($result[0].dataset['name'] === 'contractors') {
                                $result[0].innerText = 'VO Contractors';
                            } else if ($result[0].dataset['name'] === 'unit_price') {
                                $result[0].innerText = 'VO Unit Price';
                            }
                            else if ($result[0].dataset['name'] === 'time') {
                                $result[0].innerText = 'VO Time';
                            }
                        } else{
                            if ($result[0].dataset['name'] === 'quantity') {
                                $result[0].innerText = 'VO Quantity';
                            } else if ($result[0].dataset['name'] === 'unit_price') {
                                $result[0].innerText = 'VO Unit Price';
                            }
                        }
                    }
                }
            }
            return $result;
        }
    })

})