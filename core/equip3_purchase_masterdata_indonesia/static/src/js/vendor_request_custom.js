$(document).ready(function (e) {
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

    let selectionOption = ""
    function get_title_option(vendorTitle){
        selectionOption = ""
        getDataTitle(function(result){
            console.log(result)
            if(result){
              var data = result.data
              data.forEach(function(currentValue, index, arr) {
                selectionOption = selectionOption + "<option value='"+currentValue['id']+"'>"+currentValue['name']+"</option>";
              })
              $('#select_'+vendorTitle).html(
                  selectionOption
              )
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
    let selectionOptionCivil = ""
    function get_civil_option(vendorCivil){
        selectionOptionCivil = ""
        getDataCivil(function(result){
            if(result){
              var data = result.data
              data.forEach(function(currentValue, index, arr) {
                selectionOptionCivil = selectionOptionCivil + "<option value='"+currentValue['id']+"'>"+currentValue['name']+"</option>";
              })
              $('#select_'+vendorCivil).html(
                  selectionOptionCivil
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
     function getDataCivil(callback) {
      let url = '/vendor/civil_infos';
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
    $("#testbtn").click(function(e) {
        var rowCount = $(document).find("#contact_row row").length + 1;
		console.log("WAKWAW!");
		console.log(rowCount);
        rowIdx = rowIdx + 1;
        var typeContact = "vendor_c_type_contact_" + String(rowIdx);
        var vendorName = "vendor_c_name_" + String(rowIdx);
        var vendorEmail = "vendor_c_email_" + String(rowIdx);
        var vendorPhone = "vendor_c_phone_" + String(rowIdx);
        var vendorMobile = "vendor_c_mobile_" + String(rowIdx);
        var vendorJobPosition = "vendor_c_job_position_" + String(rowIdx);
        var vendorNotes = "vendor_c_notes_" + String(rowIdx);
        var vendorTitle = "vendor_c_title_" + String(rowIdx);
        var vendorIDnumber = "vendor_c_id_" + String(rowIdx);
        var vendorGender = "vendor_c_gender_" + String(rowIdx);
        var vendorPlace = "vendor_c_place_" + String(rowIdx);
        var vendorBirthdate = "vendor_c_birth_" + String(rowIdx);
        var vendorCivil = "vendor_c_civil_" + String(rowIdx);
        var vendorEmployee = "vendor_c_employee_" + String(rowIdx);
        get_title_option(vendorTitle)
        get_gender_option(vendorGender)
        get_civil_option(vendorCivil)
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
                    '<input type="text" class="form-control" name="'+
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
				        '<label for="vendor_id_number"><b>ID Number :</b></label>'+
				        '<input type="text" class="form-control" name="'+
				            vendorIDnumber+
                        '" maxlength="16" required="required"/>'+
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
                    '<input type="date" class="form-control" name="'+
                        vendorBirthdate+
                        '" required="required"/>'+
                    '</div>'+
			    '</div>'+
                '<div class="col-lg-4 col-sm-12">'+
			  '     <div class="form-group">'+
                        '<label for="vendor_civil"><b>Civil Employee Status :</b></label>'+
                        '<select class="form-control" name="'+
                            vendorCivil+
                            '" id="select_'+
                            vendorCivil+
                            '" required="required">'+
                            selectionOptionCivil+
                        '</select>'+
				    '</div>'+
			    '</div>'+
                '<div class="col-lg-4 col-sm-12">'+
			              '<div class="form-group">'+
                        '<label for="vendor_employee_number"><b>Employee Number :</b></label>'+
                        '<div class="" style="display: flex;align-items: center;">'+
                        '<input type="text" class="form-control" name="'+
                            vendorEmployee+
                            '" required="required"/>'+
                            '<button style="margin-left: 14px;margin-right: 7px;font-size: 22px;padding: 0;color: red;" class="btn remove" type="button"><i class="fa fa-trash"/></button>'+
				                '</div>'+
                      '</div>'+
			          '</div>'+
			    '</div>'
        $("#contact_row").append(text);
    });
    $("#testbtnBill").click(function(e) {
        var rowCount = $(document).find("#contact_row row").length + 1;
		console.log("WAKWAW!");
		console.log(rowCount);
        rowIdx = rowIdx + 1;
        var typeContact = "vendor_c_type_contact_" + String(rowIdx);
        var vendorName = "vendor_c_name_" + String(rowIdx);
        var vendorEmail = "vendor_c_email_" + String(rowIdx);
        var vendorPhone = "vendor_c_phone_" + String(rowIdx);
        var vendorMobile = "vendor_c_mobile_" + String(rowIdx);
        var vendorJobPosition = "vendor_c_job_position_" + String(rowIdx);
        var vendorNotes = "vendor_c_notes_" + String(rowIdx);
        var vendorTitle = "vendor_c_title_" + String(rowIdx);
        var vendorIDnumber = "vendor_c_id_" + String(rowIdx);
        var vendorGender = "vendor_c_gender_" + String(rowIdx);
        var vendorPlace = "vendor_c_place_" + String(rowIdx);
        var vendorBirthdate = "vendor_c_birth_" + String(rowIdx);
        var vendorCivil = "vendor_c_civil_" + String(rowIdx);
        var vendorEmployee = "vendor_c_employee_" + String(rowIdx);
        get_title_option(vendorTitle)
        get_gender_option(vendorGender)
        get_civil_option(vendorCivil)
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
                    '<input type="text" class="form-control" name="'+
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
			    '</div>'
        $("#contact_row").append(text);
    });

    $('#contact_row').on('click', ".remove",function() {
        $(this).closest('.c_row').remove();
    });

    function getDataBank(callback) {
      let url = '/vendor/res_bank_infos';
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
    let selectionOptionBank = ""
    function get_res_bank_option(vendorBankBank){
        selectionOptionBank = ""
        getDataBank(function(result){
            console.log(result)
            if(result){
              var data = result.data
              data.forEach(function(currentValue, index, arr) {
                selectionOptionBank = selectionOptionBank + "<option value='"+currentValue['id']+"'>"+currentValue['name']+"</option>";
              })
              $('#select_'+vendorBankBank).html(
                  selectionOptionBank
              )
            }
          });
    }
    var rowBankIdx = 0;
    $("#addBankBtn").click(function(e) {
        var rowCount = $(document).find("#tbody_banks tr").length + 1;
		console.log("WAKWAW!");
		console.log(rowCount);
        rowBankIdx = rowBankIdx + 1;
        var vendorBankBank = "vendor_bank_bank_" + String(rowBankIdx);
        var vendorBankAccountNumber = "vendor_bank_account_number_" + String(rowBankIdx);
        get_res_bank_option(vendorBankBank)
        var text =
			'<tr class="body_bank_row '+
			String(rowBankIdx)+
			'">'+ 
      '<td><select class="form-control" name="'+
      vendorBankBank+
      '" id="select_'+
      vendorBankBank+
      '" required="required">'+
      selectionOptionBank+
  '</td></select>'+
  '<td><input type="text" class="form-control" name="'+
  vendorBankAccountNumber+
  '" required="required"/></td>'+
  '<td><button style="margin-left: 14px;margin-right: 7px;font-size: 22px;padding: 0;color: red;" class="btn removeBank" type="button"><i class="fa fa-trash"/></button></td>'+
			    '</tr>'
        $("#tbody_banks").append(text);
    });

    $('#tbody_banks').on('click', ".removeBank",function() {
        $(this).closest('.body_bank_row').remove();
    });

    $("#l10n_id_pkp").click(function () {
        if ($(this).is(":checked")) {
            $("#pkp_true_npwp").show();
            $(".pkp_true_npwp_class").show();
            $(".pkp_false_npwp_class").hide();
          } else {
            $("#pkp_true_npwp").hide();
            $(".pkp_true_npwp_class").hide();
            $(".pkp_false_npwp_class").show();
        }
    });
    $('.vendor_vat').mask('00.000.000.0-000.000');
});