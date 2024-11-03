odoo.define('equip3_pos_masterdata.ProductList', function (require) {
    'use strict';

    const ProductList = require('point_of_sale.ProductList');
    const Registries = require('point_of_sale.Registries');

    ProductList.template = 'RetailProductList';
    Registries.Component.add(ProductList);

    const RetailProductList = (ProductList) =>
        class extends ProductList {
            // mounted() {
            //     this.env.pos.on(
            //         'change:ProductView',
            //         (pos, synch) => {
            //             this.render()
            //         },
            //         this
            //     );
            // }

            get IsSHowPrevPagination(){
                if(1!=this.props.page_pagination){
                    return true
                }
                else{
                    return false
                }

            }

            get IsSHowNextPagination(){
                var length_products = this.props.products.length
                var max_line_perpage = this.props.max_line_perpage
                var length_record = Math.ceil(length_products / max_line_perpage);
                if(this.props.page_pagination!=length_record){
                    return true
                }
                else{
                    return false
                }
            }


            get getproductsPagination() {
                var res = this.props.products
                var min = 0
                if(this.props.page_pagination > 1){
                    min += (this.props.page_pagination-1)* this.props.max_line_perpage 
                }
                var max = min+this.props.max_line_perpage
                return res.slice(min, max)
            }

            clickPagination(Pagination){
                this.props.page_pagination = parseInt(Pagination)
                this.render()
            }

            get lengthPagination(){
                var length_products = this.props.products.length
                var max_line_perpage = this.props.max_line_perpage
                var length_record = Math.ceil(length_products / max_line_perpage);
                var count = 0
                var res = []
                var count = 0
                var first_pagination = this.props.group_pagination_button 
                if (first_pagination>1)
                {
                    first_pagination = ((this.props.group_pagination_button  - 1) * this.props.max_pagination_button) + 1
                }
                for(var ii = first_pagination ; ii <= length_record; ii++){
                    res.push(ii)
                    count+=1
                    if (count==this.props.max_pagination_button){
                        break
                    }
                }
                return res
            }

            clickNextPagination(){
                var length_products = this.props.products.length
                var max_line_perpage = this.props.max_line_perpage
                var length_record = Math.ceil(length_products / max_line_perpage);
                var pagination = this.lengthPagination
                if(pagination[pagination.length-1]==this.props.page_pagination){
                    this.props.group_pagination_button+=1
                    this.SetPaginationAuto()
                }
                else{
                    this.props.page_pagination+=1
                    this.render()
                }
                
                
                
            }
            clickPrevPagination(){
                var length_products = this.props.products.length
                var max_line_perpage = this.props.max_line_perpage
                var length_record = Math.ceil(length_products / max_line_perpage);
                var pagination = this.lengthPagination
                if(pagination[0]==this.props.page_pagination){
                    this.props.group_pagination_button-=1
                    this.SetPaginationAuto()
                    var last_pagination = this.lengthPagination[this.lengthPagination.length-1]
                    this.clickPagination(last_pagination)
                }
                else{
                    this.props.page_pagination-=1
                    this.render()
                }
            }

            SetPaginationAuto(){
                var length_products = this.props.products.length
                var max_line_perpage = this.props.max_line_perpage
                var length_record = Math.ceil(length_products / max_line_perpage);
                var pagination = this.lengthPagination
                var first_pagination = pagination[0]
                this.clickPagination(first_pagination)
            }

        }
    Registries.Component.extend(ProductList, RetailProductList);

    return ProductList;
});
