$(document).ready(function (e) {

    if (window.location.href.includes('/vendor_sign_up')&&$('.alert').length==1) {
        var modal_element = '\
        <div class="modal fade" id="modal_vendor_sign_up"  tabindex="-1" role="dialog">\
          <div class="modal-dialog" role="document">\
            <div class="modal-content">\
              <div class="modal-header '+$('.alert').attr('class')+'">\
                <h5 class="modal-title">'+$('.alert strong').text()+'</h5>\
                <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
                  <span aria-hidden="true">&times;</span>\
                </button>\
              </div>\
              <div class="modal-body">\
                <p>'+$('.alert span').text()+'</p>\
              </div>\
              <div class="modal-footer">\
                <button type="button" class="btn btn-primary" data-dismiss="modal" style="background:#A20025 !important;">Close</button>\
              </div>\
            </div>\
          </div>\
        </div>'
        $( "body" ).append( modal_element );
        $('#modal_vendor_sign_up').modal()
    }
    $("#create_vendor_pricelist").click(function(e){
        if ($('#quantity').val() < 1 || $('#quantity').val() == ''){
            alert("Minimal Qty should be greater then zero");
            return false;
        }
        else if(($('#validity_start').val() != '' && $('#validity_end').val() != '') && ($('#validity_end').val() < $('#validity_start').val()))
        {
            alert("End Date should be greater then Start Date");
            return false; 
        }
        else if($('#validity_start').val() == '' && $('#validity_end').val() != '')
        {
            alert("Please select Start Date");
            return false; 
        }
        else if($('#validity_start').val() != '' && $('#validity_end').val() == '')
        {
            alert("Please select End Date");
            return false; 
        }
    })

    $('.update-vendor-invoice').click(function(event) {
        var purchase_id = $(event.target).closest('tr').data('id');
        $('#updatevendorinvoice').find('#purchase_id').val(purchase_id);
        $('#updatevendorinvoice ul li:not(.d-none)').remove();
        $.ajax({
            url: "/purchase/attachment",
            data: {
                'purchase_id': purchase_id,
            },
            type: "post",
            cache: false,
            success: function (result) {
                var result = JSON.parse(result);
                if (result.urls !== undefined &&
                    result.urls.length) {
                    $('#updatevendorinvoice .modal-body ul').removeClass('d-none');
                    _.each(result.urls, function(item) {
                        var $new_li = $('#updatevendorinvoice .modal-body ul li.d-none').clone(true);
                        $new_li.removeClass('d-none');
                        $new_li.find('a').attr('href', item.url);
                        $new_li.find('a span.name').text(item.name);
                        $('#updatevendorinvoice .modal-body ul').append($new_li);
                    });
                }
                $('#updatevendorinvoice').modal("show");
            },
        });
    });

    $('.update-vendor-invoice-form').click(function(event) {
        var purchase_id = $('#purchase_order_id').val();
        $('#updatevendorinvoice').find('#purchase_id').val(purchase_id);
        $('#updatevendorinvoice ul li:not(.d-none)').remove();
        $.ajax({
            url: "/purchase/attachment",
            data: {
                'purchase_id': purchase_id,
            },
            type: "post",
            cache: false,
            success: function (result) {
                var result = JSON.parse(result);
                if (result.urls !== undefined &&
                    result.urls.length) {
                    $('#updatevendorinvoice .modal-body ul').removeClass('d-none');
                    _.each(result.urls, function(item) {
                        var $new_li = $('#updatevendorinvoice .modal-body ul li.d-none').clone(true);
                        $new_li.removeClass('d-none');
                        $new_li.find('a').attr('href', item.url);
                        $new_li.find('a span.name').text(item.name);
                        $('#updatevendorinvoice .modal-body ul').append($new_li);
                    });
                }
                $('#updatevendorinvoice').modal("show");
            },
        });
    });

    $(document).on('change', '#vendor_invoice_files',  function(event) {
        readFile($(event.target).parents('.modal').find('#vendor_invoice_files')[0]);
    });

    function readFile(input) {
        var filesName = [];
        var filesTotal = input.files.length;
        var files_data = [];
        for (var i = 0; i < filesTotal; ++i) {
            filesName.push(input.files.item(i).name)
            var reader = new FileReader();
            function readFileData(i) {
                reader.addEventListener("load", function(e) {
                    files_data.push({
                        'name': filesName[i],
                        'data': e.target.result.split('base64,')[1],
                    });
                    $('textarea[name="vendor_files"]').val(JSON.stringify(files_data));
                });
            }
        reader.readAsDataURL(input.files[i]);
        readFileData(i)
      }
    }

    $('.save_vendor_invoice').click(function(event) {
        var purchase_id = $(event.target).parents('.modal').find('#purchase_id').val();
        var files_data = $(event.target).parents('.modal').find('textarea[name="vendor_files"]').val();
        $.ajax({
            url: "/purchase/vendor/document/upload",
            data: {
                'purchase_id': purchase_id,
                'file_data': files_data,
            },
            type: "post",
            cache: false,
            success: function (result) {
                $('#vendor_invoice_files').val('');
                $('#updatevendorinvoice').modal("hide");
            },
        });
    });

    // if (window.location.href.includes('/open_tender')) {
    //     $('body').addClass('open_tender_view');
    // }

    // if (window.location.href.includes('/my/rfq')) {
    //     $('body').addClass('vendor_rfq_view');
    // }

    // if (window.location.href.includes('/my/purchase')) {
    //     $('body').addClass('vendor_purchase_view');
    // }

    // if (window.location.href.includes('/my/tender')) {
    //     $('body').addClass('vendor_tender_view');
    // }

    // if (window.location.href.includes('/my/vendor_pricelist')) {
    //     $('body').addClass('vendor_pricelist_view');
    // }

    // if (window.location.href.includes('/vendor_pricelist')) {
    //     $('body').addClass('vendor_pricelist_form_view');
    // }

    // if (window.location.href.includes('/blanket/order')) {
    //     $('body').addClass('blanket_order_view');
    // }

    // if (window.location.href.includes('/my/invoices')) {
    //     $('body').addClass('invoice_view');
    // }

    if (odoo.session_info !== undefined &&
        odoo.session_info.user_id !== undefined &&
        odoo.session_info.user_id === false) {
        sessionStorage.removeItem('is_wizard_show');
    }

    $(document).on('click', '.customer_portal_button', function(event) {
        event.stopPropagation();
        $.ajax({
            url: "/change/user/type",
            type: "POST",
            data: {
                'is_customer': true,
            },
            dataType: "json",
            success: function (result) {
                setTimeout(function () {
                    window.location.href = '/shop'
                }, 1000);
            },
        });
    });

    $(document).on('click', '.vendor_portal_button', function(event) {
        event.stopPropagation();
        $.ajax({
            url: "/change/user/type",
            type: "POST",
            data: {
                'is_vendor': true,
            },
            dataType: "json",
            success: function (result) {
                setTimeout(function () {
                    window.location.href = '/tender/dashboard'
                }, 1000);
            },
        });
    });

    if (odoo.session_info !== undefined &&
        odoo.session_info.is_both !== undefined &&
        odoo.session_info.is_both &&
        (sessionStorage.getItem('is_wizard_show') === null ||
        sessionStorage.getItem('is_wizard_show') === undefined)) {
        $.ajax({
            url: "/check/user",
            type: "GET",
            dataType: "json",
            success: function (result) {
                $('#wrap').append($(result.html));
                $('#user_vendor_customer').modal({backdrop: 'static', keyboard: false}, 'show');
                $('#user_vendor_customer').find('div.vendor_user').on('click', function(event) {
                    $(this).addClass('vendor_user_border');
                    $(this).find('.vendor-ok-img').removeClass('d-none');
                    $(this).next().removeClass('customer_user_border');
                    $(this).next().find('.customer-ok-img').addClass('d-none');
                    $(this).closest('.modal-body').find('.lets-get-started').removeClass('d-none');
                    $(this).closest('.modal-body').find('.lds-ring').removeClass('d-none');
                    $(this).closest('.modal-body').find('div.lets-get-started').removeClass('mt-5');
                    $.ajax({
                        url: "/change/user/type",
                        type: "POST",
                        data: {
                            'is_vendor': true,
                        },
                        dataType: "json",
                        success: function (result) {
                            setTimeout(function () {
                                sessionStorage.setItem('is_wizard_show', true);
                                window.location.href = '/tender/dashboard'
                            }, 3000);
                        },
                    });
                });
                $('#user_vendor_customer').find('div.customer_user').on('click', function(event) {
                    $(this).addClass('customer_user_border');
                    $(this).find('.customer-ok-img').removeClass('d-none');
                    $(this).prev().removeClass('vendor_user_border');
                    $(this).prev().find('.vendor-ok-img').addClass('d-none');
                    $(this).closest('.modal-body').find('.lets-get-started').removeClass('d-none');
                    $(this).closest('.modal-body').find('.lds-ring').removeClass('d-none');
                    $(this).closest('.modal-body').find('div.lets-get-started').removeClass('mt-5');
                    $.ajax({
                        url: "/change/user/type",
                        type: "POST",
                        data: {
                            'is_customer': true,
                        },
                        dataType: "json",
                        success: function (result) {
                            setTimeout(function () {
                                sessionStorage.setItem('is_wizard_show', true);
                                window.location.href = '/shop'
                            }, 3000);
                        },
                    });
                });
            },
        });
    } else if (odoo.session_info !== undefined &&
        odoo.session_info.is_vendor !== undefined &&
        odoo.session_info.is_customer !== undefined &&
        odoo.session_info.is_vendor &&
        !odoo.session_info.is_customer) {
        $.ajax({
            url: "/change/user/type",
            type: "POST",
            data: {
                'is_vendor': true,
            },
            dataType: "json",
        });
    } else if (odoo.session_info !== undefined &&
        odoo.session_info.is_vendor !== undefined &&
        odoo.session_info.is_customer !== undefined &&
        !odoo.session_info.is_vendor &&
        odoo.session_info.is_customer) {
        $.ajax({
            url: "/change/user/type",
            type: "POST",
            data: {
                'is_customer': true,
            },
            dataType: "json",
        });
    }

    if ($('.po_unitprice').length) {
        _.each($('.po_unitprice'), function(item) {
            var value = $(item).val();
            var new_value = value
                // Keep only digits and decimal points:
                .replace(/[^\d.]/g, "")
                // Remove duplicated decimal point, if one exists:
                .replace(/^(\d*\.)(.*)\.(.*)$/, '$1$2$3')
                // Keep only two digits past the decimal point:
                .replace(/\.(\d{2})\d+/, '.$1')
                // Add thousands separators:
                .replace(/\B(?=(\d{3})+(?!\d))/g, ",");
            $(item).val(new_value);
        });
    }

    $(document).on('focusout', '.po_unitprice', function(event) {
        if (event.which >= 37 && event.which <= 40) return;
            $(this).val(function(index, value) {
              return value
                // Keep only digits and decimal points:
                .replace(/[^\d.]/g, "")
                // Remove duplicated decimal point, if one exists:
                .replace(/^(\d*\.)(.*)\.(.*)$/, '$1$2$3')
                // Keep only two digits past the decimal point:
                .replace(/\.(\d{2})\d+/, '.$1')
                // Add thousands separators:
                .replace(/\B(?=(\d{3})+(?!\d))/g, ",")
            });
    });

    $("#btn_retreat").click(function (e) {
        e.stopPropagation();
        e.preventDefault();
        $.ajax({
            url: "/rfq/retreat",
            data: {order_id: $("#order_id").val() },
            type: "post",
            cache: false,
            success: function (result) {
                window.location.href = result;
            },
        });
    });
    $("#btn_retreat_rfq_open_tender").click(function (e) {
        e.stopPropagation();
        e.preventDefault();
        $.ajax({
            url: "/rfq/retreat?is_rfq_tender=True",
            data: {order_id: $("#order_id").val() },
            type: "post",
            cache: false,
            success: function (result) {
                window.location.href = result;
            },
        });
    });
    $("#btn_retreat_rfq_tender").click(function (e) {
        e.stopPropagation();
        e.preventDefault();
        $.ajax({
            url: "/rfq/retreat?is_rfq_open_tender=True",
            data: {order_id: $("#order_id").val() },
            type: "post",
            cache: false,
            success: function (result) {
                window.location.href = result;
            },
        });
    });

    let selectionOption = ""
    function get_title_option(vendorTitle){
        selectionOption = ""
        getDataTitle(function(result){
            if(result){
              var data = result.data
              // console.log(result.data);
              data.forEach(function(currentValue, index, arr) {
                // console.log(currentValue);
                selectionOption = selectionOption + "<option value='"+currentValue['id']+"'>"+currentValue['name']+"</option>";
              })
              console.log("=============================")
              console.log(selectionOption)
              console.log("=============================")
              $('#select_'+vendorTitle).html(
                  selectionOption
              )
            }
          });
    }
    function getDataTitle(callback) {
        let url = '/vendor/title_infos';
        $.ajax({
          method: "GET",
          url: url,
          dataType: "json",
          success(data){
            if(typeof callback == 'function'){
              callback(data)
            }
          }
        });
      }
      let selectionOptionGender = ""
    function get_gender_option(vendorGender){
        selectionOptionGender = ""
        getDataGender(function(resGender){
        console.log(resGender)
            if(resGender){
              var dataGender = resGender.data
              dataGender.forEach(function(currentValue, index, arr) {
                selectionOptionGender = selectionOptionGender + "<option value='"+currentValue['id']+"'>"+currentValue['name']+"</option>";
              })
              $('#select_'+vendorGender).html(
                  selectionOptionGender
              )
            }
          });
    }
    function getDataGender(callback) {
        let url = '/vendor/gender_infos';
        $.ajax({
          method: "GET",
          url: url,
          dataType: "json",
          success(data){
            if(typeof callback == 'function'){
              callback(data)
            }
          }
        });
      }
    // OVERRIDE
    var rowIdx = 0;
    $("#addBtn").off('click').on("click", function () {
        var rowCount = $(document).find("#contact_row row").length + 1;
		console.log("WAKWAW!");
		console.log(rowCount);
        rowIdx = rowIdx + 1;
        var vendorName = "vendor_c_name_" + String(rowIdx);
        var vendorEmail = "vendor_c_email_" + String(rowIdx);
        var vendorPhone = "vendor_c_phone_" + String(rowIdx);
        var vendorMobile = "vendor_c_mobile_" + String(rowIdx);
        var vendorJobPosition = "vendor_c_job_position_" + String(rowIdx);
        var vendorNotes = "vendor_c_notes_" + String(rowIdx);
        var vendorTitle = "vendor_c_title_" + String(rowIdx);
        var vendorGender = "vendor_c_gender_" + String(rowIdx);
        var vendorPlace = "vendor_c_place_" + String(rowIdx);
        var vendorBirthdate = "vendor_c_birth_" + String(rowIdx);
        get_title_option(vendorTitle)
        get_gender_option(vendorGender)
        var productOptioons = '<option value="">Select Product</option>';
        var productOptioons = $(document).find("#js_id_product_list").html();
        var text =
			'<div class="row c_row '+
			String(rowIdx)+
			'">'+ '<div class="col-lg-4 col-sm-12">'+
            '<div class="form-group">'+
              '<label for="vendor_contact_type"><b>Type :</b></label>'+
              '<select class="form-control" name="'+
              typeContact+
                  '" id="select_'+
                  typeContact+
                  '" required="required">'+
                  '<option value="contact">Contact</option>'+
              '</select>'+
              '</div>'+
      '</div>'+
      '<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_name"><b>Name :</b></label>'+
				'<input type="text" class="form-control" ' +
				' name="'+
				vendorName+
				'" required="required"/>'+
				'</div>'+
			    '</div>'+
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_email"><b>Email :</b></label>'+
				'<input type="email" class="form-control" name="'+
				vendorEmail+
				'" required="required"/>'+
				'</div>'+
			    '</div>'+
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_phone"><b>Phone :</b></label>'+
				'<input type="text" class="form-control" name="'+
				vendorPhone+
                '" required="required"/>'+
				'</div>'+
			    '</div>'+
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_mobile"><b>Mobile :</b></label>'+
				'<input type="text" class="form-control" name="'+
				vendorMobile+
				'" required="required"/>'+
				'</div>'+
			    '</div>'+
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_title"><b>Title :</b></label>'+
                '<select class="form-control" name="'+
				vendorTitle+
				'" id="select_'+
                vendorTitle+
				'" required="required">'+
                selectionOption+
				'</select>'+
				'</div>'+
			    '</div>'+ 
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_job_position"><b>Job Position :</b></label>'+
				'<input type="text" class="form-control" placeholder="e.g. Sales Director" name="'+
				vendorJobPosition+
				'" required="required"/>'+
				'</div>'+
			    '</div>'+
                '<div class="col-lg-4 col-sm-12">'+
			        '<div class="form-group">'+
				        '<label for="vendor_gender"><b>Gender :</b></label>'+
				        '<select class="form-control" name="'+
                            vendorGender+
                            '" id="select_'+
                            vendorGender+
                            '" required="required">'+
                            selectionOptionGender+
                        '</select>'+
                    '</div>'+
                '</div>'+
                '<div class="col-lg-4 col-sm-12">'+
			        '<div class="form-group">'+
				        '<label for="vendor_place"><b>Place of Birth :</b></label>'+
				        '<input type="text" class="form-control" name="'+
				            vendorPlace+
                            '" required="required"/>'+
				    '</div>'+
			    '</div>'+
                '<div class="col-lg-4 col-sm-12">'+
			        '<div class="form-group">'+
                    '<label for="vendor_birth_date"><b>Date of Birth :</b></label>'+
                    '<div class="" style="display: flex;align-items: center;">'+
                    '<input type="date" class="form-control" name="'+
                        vendorBirthdate+
                        '" required="required"/>'+
                        '<button style="margin-left: 14px;margin-right: 7px;font-size: 22px;padding: 0;color: red;" class="btn remove" type="button"><i class="fa fa-trash"/></button>'+
                    '</div>'+
                    '</div>'+
			    '</div>'
        $("#contact_row").append(text);
    });
    $("#addBtnBill").off('click').on("click", function () {
        var rowCount = $(document).find("#contact_row row").length + 1;
		console.log("WAKWAW!");
		console.log(rowCount);
        rowIdx = rowIdx + 1;
        var vendorName = "vendor_c_name_" + String(rowIdx);
        var vendorEmail = "vendor_c_email_" + String(rowIdx);
        var vendorPhone = "vendor_c_phone_" + String(rowIdx);
        var vendorMobile = "vendor_c_mobile_" + String(rowIdx);
        var vendorJobPosition = "vendor_c_job_position_" + String(rowIdx);
        var vendorNotes = "vendor_c_notes_" + String(rowIdx);
        var vendorTitle = "vendor_c_title_" + String(rowIdx);
        var vendorGender = "vendor_c_gender_" + String(rowIdx);
        var vendorPlace = "vendor_c_place_" + String(rowIdx);
        var vendorBirthdate = "vendor_c_birth_" + String(rowIdx);
        get_title_option(vendorTitle)
        get_gender_option(vendorGender)
        var productOptioons = '<option value="">Select Product</option>';
        var productOptioons = $(document).find("#js_id_product_list").html();
        var text =
			'<div class="row c_row '+
			String(rowIdx)+
			'">'+ '<div class="col-lg-4 col-sm-12">'+
            '<div class="form-group">'+
              '<label for="vendor_contact_type"><b>Type :</b></label>'+
              '<select class="form-control" name="'+
              typeContact+
                  '" id="select_'+
                  typeContact+
                  '" required="required">'+
                  '<option value="invoice">Vendor Bill Address</option>'+
              '</select>'+
              '</div>'+
      '</div>'+
      '<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_name"><b>Name :</b></label>'+
				'<input type="text" class="form-control" ' +
				' name="'+
				vendorName+
				'" required="required"/>'+
				'</div>'+
			    '</div>'+
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_email"><b>Email :</b></label>'+
				'<input type="email" class="form-control" name="'+
				vendorEmail+
				'" required="required"/>'+
				'</div>'+
			    '</div>'+
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_phone"><b>Phone :</b></label>'+
				'<input type="text" class="form-control" name="'+
				vendorPhone+
                '" required="required"/>'+
				'</div>'+
			    '</div>'+
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_mobile"><b>Mobile :</b></label>'+
                '<div class="" style="display: flex;align-items: center;">'+
				'<input type="text" class="form-control" name="'+
				vendorMobile+
				'" required="required"/>'+
                '<button style="margin-left: 14px;margin-right: 7px;font-size: 22px;padding: 0;color: red;" class="btn remove" type="button"><i class="fa fa-trash"/></button>'+
                '</div>'+
            '</div>'+
            '</div>'+
        $("#contact_row").append(text);
    });

    // $("#btn_add_bid_form_open_tender").click(function (e) {
    //     alert("KEPANGGIL 2")

    //     $.ajax({
    //         url: "/open_tender/rfq/create",
    //         data: { tender_id: $(this).attr("data-value") },
    //         type: "post",
    //         cache: false,
    //         success: function (result) {
    //             var datas = JSON.parse(result);
    //             if (datas.url) {
    //                 window.location.href = datas.url;
    //             }
    //         },
    //     });
    // });
    $("#create_vendor").click(function(e){
        let is_valid = false
        getDataEmail(function(result){
            if(result){
                var data = result.data
                // console.log(result.data);
                if(data.length >0){
                    alert('Email Has Been Registered')
                    return false
                }else{
                    is_valid= true
                }
            }else{
                is_valid= true
            }
          });
        return is_valid
    })
    function getDataEmail(callback) {
        let url = '/check_email_vendor';
        let email = $('#vendor_email').val()
        if(email){
            url = url+"?vendor_email="+email
        }
        console.log("======================")
        console.log(email)
        console.log(url)
        console.log("======================")
        $.ajax({
        method: "GET",
        url: url,
        dataType: "json",
        async:false,
        success(data){
            if(typeof callback == 'function'){
                callback(data)
            }
            }
        });
      }

    
    var elem = $('.thousandSeparator');
    for (var i = 0 ; i < elem.length; i++) {
        elem[i].addEventListener('keydown' ,function(event){
            var key = event.which;
            if((key<48 || key>57) && key != 8) event.preventDefault();
        }) ; 
        elem[i].addEventListener('keyup' ,function(event){
            var value = this.value.replace(/,/g,"");
            this.dataset.currentValue=parseInt(value);
            var caret = value.length-1;
            while((caret-3)>-1)
            {
                caret -= 3;
                value = value.split('');
                value.splice(caret+1,0,",");
                value = value.join('');
            }
            this.value = value;
        }) ; 
     }

});
