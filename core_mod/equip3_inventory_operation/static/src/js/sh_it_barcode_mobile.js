$(document).ready(function () {

    let selectedDeviceId;

    function decodeOnce(codeReader, selectedDeviceId, inputField, resultField) {
        codeReader
            .decodeFromInputVideoDevice(selectedDeviceId, "video")
            .then((result) => {
                $(inputField).val(result.text);
                $(inputField).change();

                //RESET READER
                codeReader.reset();

                //HIDE VIDEO
                $("#js_id_sh_it_barcode_mobile_vid_div").hide();

                //HIDE STOP BUTTON
                $("#js_id_sh_it_barcode_mobile_reset_btn").hide();

                //RESULT
                $(resultField).text(result.text);
            })
            .catch((err) => {
                console.error(err);
            });
    }

    function decodeContinuously(codeReader, selectedDeviceId, inputField, resultField) {
        codeReader.decodeFromInputVideoDeviceContinuously(selectedDeviceId, "video", (result, err) => {
            if (result) {
                // console.log("Scanned Barcode:", result.text);

                $(inputField).val(result.text);
                $(inputField).change();

                //RESULT
                $(resultField).text(result.text);
            }

            if (err) {
                if (err instanceof ZXing.NotFoundException) {
                    $(inputField).val("");
                    $(inputField).change();
                }
            }
        });
    }

    //HIDE STOP BUTTON (SAFETY IN XML WE ALSO DO AND HERE ALSO.)
    $("#js_id_sh_it_barcode_mobile_reset_btn").hide();

    const codeReader = new ZXing.BrowserMultiFormatReader();

    codeReader
        .getVideoInputDevices()
        .then(function (result) {
            const sourceSelect = document.getElementById("js_id_sh_it_barcode_mobile_cam_select");

            $('input[name="sh_it_barcode_mobile"]').val("");
            $('input[name="sh_it_barcode_mobile"]').change();
            $('input[name="source_location_barcode"]').val("");
            $('input[name="source_location_barcode"]').change();
            $('input[name="destination_location_barcode"]').val("");
            $('input[name="destination_location_barcode"]').change();

            _.each(result, function (item) {
                const sourceOption = document.createElement("option");
                sourceOption.text = item.label;
                sourceOption.value = item.deviceId;
                sourceSelect.appendChild(sourceOption);
            });

            $(document).on('change', '#js_id_sh_it_barcode_mobile_cam_select', function(ev) {
                var cameraSelect = $(ev.currentTarget);
                selectedDeviceId = cameraSelect.val();
                $("#js_id_sh_it_barcode_mobile_reset_btn").click();
                $("#js_id_sh_it_barcode_mobile_start_btn").click();
            });

            $(document).on("click", "#js_id_sh_it_barcode_mobile_start_btn", function (event) {
                $('input[name="sh_it_barcode_mobile"]').val("");
                $('input[name="sh_it_barcode_mobile"]').change();

                $("#js_id_sh_it_barcode_mobile_vid_div").show();
                $("#js_id_sh_it_barcode_mobile_reset_btn").show();

                if ($('span[name="sh_it_bm_is_cont_scan"]').text() == "True") {
                    decodeContinuously(codeReader, selectedDeviceId, 'input[name="sh_it_barcode_mobile"]', "#js_id_sh_it_barcode_mobile_result");
                } else {
                    decodeOnce(codeReader, selectedDeviceId, 'input[name="sh_it_barcode_mobile"]', "#js_id_sh_it_barcode_mobile_result");
                }
            });

            $(document).on("click", "#js_id_sh_it_barcode_mobile_source_location_start_btn", function (event) {
                $('input[name="source_location_barcode"]').val("");
                $('input[name="source_location_barcode"]').change();

                $("#js_id_sh_it_barcode_mobile_vid_div").show();
                $("#js_id_sh_it_barcode_mobile_reset_btn").show();

                if ($('span[name="sh_it_bm_is_cont_scan"]').text() == "True") {
                    decodeContinuously(codeReader, selectedDeviceId, 'input[name="source_location_barcode"]', "#js_id_source_location_result");
                } else {
                    decodeOnce(codeReader, selectedDeviceId, 'input[name="source_location_barcode"]', "#js_id_source_location_result");
                }
            });

            $(document).on("click", "#js_id_sh_it_barcode_mobile_destination_location_start_btn", function (event) {
                $('input[name="destination_location_barcode"]').val("");
                $('input[name="destination_location_barcode"]').change();

                $("#js_id_sh_it_barcode_mobile_vid_div").show();
                $("#js_id_sh_it_barcode_mobile_reset_btn").show();

                if ($('span[name="sh_it_bm_is_cont_scan"]').text() == "True") {
                    decodeContinuously(codeReader, selectedDeviceId, 'input[name="destination_location_barcode"]', "#js_id_destination_location_result");
                } else {
                    decodeOnce(codeReader, selectedDeviceId, 'input[name="destination_location_barcode"]', "#js_id_destination_location_result");
                }
            });

            $(document).on("click", "#js_id_sh_it_barcode_mobile_reset_btn", function () {
                $("#js_id_sh_it_barcode_mobile_result").textContent = "";
                $("#js_id_source_location_result").textContent = "";
                $("#js_id_destination_location_result").textContent = "";

                $('input[name="sh_it_barcode_mobile"]').val("");
                $('input[name="sh_it_barcode_mobile"]').change();
                $('input[name="source_location_barcode"]').val("");
                $('input[name="source_location_barcode"]').change();
                $('input[name="destination_location_barcode"]').val("");
                $('input[name="destination_location_barcode"]').change();

                codeReader.reset();

                $("#js_id_sh_it_barcode_mobile_vid_div").hide();
                $("#js_id_sh_it_barcode_mobile_reset_btn").hide();
            });
        })
        .catch(function (reason) {
            console.log("Error ==>" + reason);
        });
});
